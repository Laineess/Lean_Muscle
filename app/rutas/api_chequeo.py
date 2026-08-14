"""Captura del chequeo mensual, desde el frente de alumna.

Es el flujo que sostiene todo lo demás: sin chequeo no hay peso, sin peso no hay
calculadora, y sin calculadora no hay plan. Por eso el borrador se guarda paso a paso en el
servidor y no en el navegador: la alumna hace esto de pie, en ayunas, recién despierta, y
perder la captura por cerrar la pestaña sin querer significa esperar al mes siguiente.

**Las guardas de envío las evalúa el dominio, no esta capa.** Aquí solo se arma la
instantánea y se traduce el resultado. La pantalla repite las mismas validaciones por
cortesía, pero las que mandan son estas: un cliente comprometido no debe poder saltarse
ninguna.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc, dia_calendario
from app.datos.modelos import Alumna, Chequeo, Medida, Pesaje
from app.datos.repos import consultas as q
from app.dominio.avisos import Aviso
from app.dominio.chequeo import (
    Angulo,
    EstadoChequeo,
    Instantanea,
    Transicion,
    guardas_de_envio,
    transicionar,
)
from app.dominio.medidas import TipoMedida, validar_medida, validar_peso
from app.rutas.esquemas import (
    BorradorChequeo,
    FotoDeBorrador,
    GuardadoDeChequeo,
    PesajePublico,
)
from app.rutas.sesion import Actor, datos, solo_alumna
from app.rutas.traduccion import respuesta_para
from app.servicios import avisos as cola
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api/mi", tags=["chequeo"])

#: Tope de pesajes por ciclo. El promedio quita el ruido de un día de retención.
MAX_PESAJES = 3


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


def _hoy_de(alumna: Alumna) -> date:
    """El día calendario **de la alumna**.

    Una alumna en Tijuana que se pesa a las 7 no debe perder su chequeo porque en Mérida ya
    es otro día.
    """
    return dia_calendario(ahora_utc(), alumna.zona_horaria)


def _numero_de(s: Session, alumna_id: int, chequeo: Chequeo) -> int:
    """Cuántos chequeos van, contando este. Es lo que la alumna ve como «Chequeo #5»."""
    historial = q.chequeos_de(s, alumna_id)
    for i, c in enumerate(historial, start=1):
        if c.id == chequeo.id:
            return i
    return len(historial) + 1


def _peso_anterior(s: Session, alumna_id: int, chequeo_id: int) -> Decimal | None:
    """El peso del chequeo anterior, que es contra el que se mide la varianza."""
    previos = [c for c in q.chequeos_de(s, alumna_id) if c.id != chequeo_id]
    if not previos:
        return None
    pesos = q.peso_de_chequeo(s, [c.id for c in previos])
    for c in reversed(previos):
        peso = pesos.get(c.id)
        if peso is not None:
            return Decimal(str(peso))
    return None


def _medidas_anteriores(s: Session, alumna_id: int, chequeo_id: int) -> dict[str, Decimal]:
    previos = [c for c in q.chequeos_de(s, alumna_id) if c.id != chequeo_id]
    if not previos:
        return {}
    medidas = q.medidas_de(s, [c.id for c in previos])
    for c in reversed(previos):
        del_chequeo = medidas.get(c.id) or {}
        if del_chequeo:
            return {k: Decimal(str(v)) for k, v in del_chequeo.items()}
    return {}


def _publico(s: Session, alumna: Alumna, chequeo: Chequeo) -> BorradorChequeo:
    pesajes = q.pesajes_del_ciclo(s, alumna.id, chequeo.ciclo_id)
    medidas = q.medidas_del_chequeo(s, chequeo.id)
    fotos = q.fotos_de(s, chequeo.id)
    del_chequeo = next((p for p in pesajes if p.chequeo_id == chequeo.id), None)

    return BorradorChequeo(
        ulid=chequeo.ulid,
        numero=_numero_de(s, alumna.id, chequeo),
        fecha=chequeo.fecha,
        estado=chequeo.estado,
        ayuno_confirmado=chequeo.ayuno_confirmado,
        varianza_confirmada=chequeo.varianza_confirmada,
        nota_alumna=chequeo.nota_alumna,
        peso_kg=del_chequeo.peso_kg if del_chequeo else None,
        medidas={m.tipo: m.valor for m in medidas},
        fotos=[
            FotoDeBorrador(
                angulo=f.angulo,
                estado_auto=f.estado_auto,
                nitidez=f.nitidez,
                luminancia=f.luminancia,
                tomada_en=f.subida_en,
            )
            for f in fotos
            if f.storage_key is not None
        ],
        pesajes=[PesajePublico(fecha=p.fecha, peso_kg=p.peso_kg) for p in pesajes],
        max_pesajes=MAX_PESAJES,
        peso_anterior_kg=_peso_anterior(s, alumna.id, chequeo.id),
        medidas_anteriores=_medidas_anteriores(s, alumna.id, chequeo.id),
        bascula_ref=alumna.bascula_ref,
        lugar_ref=alumna.lugar_ref,
        hora_ref=alumna.hora_ref,
        bascula_usada=chequeo.bascula_usada,
        lugar_usado=chequeo.lugar_usado,
        hora_usada=chequeo.hora_usada,
    )


def _chequeo_editable(s: Session, alumna: Alumna, ulid: str) -> Chequeo:
    chequeo = q.chequeo_por_ulid(s, ulid)
    if chequeo is None or chequeo.alumna_id != alumna.id:
        raise HTTPException(404, "No existe ese chequeo")
    if chequeo.estado not in {"borrador", "rechazado_calidad"}:
        raise HTTPException(409, "Este chequeo ya se envió y no se puede cambiar")
    return chequeo


# ---------------------------------------------------------------------------
# Abrir, guardar, enviar
# ---------------------------------------------------------------------------


@ruteador.post("/chequeo", response_model=BorradorChequeo)
def abrir_chequeo(
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Abre el chequeo del ciclo, o devuelve el que ya estaba abierto.

    Es idempotente a propósito: la pantalla lo llama al entrar, y entrar dos veces no debe
    crear dos chequeos. Un chequeo devuelto en `rechazado_calidad` es uno que la coach mandó
    repetir; se vuelve a la misma captura en lugar de empezar otra, que rompería la
    numeración de la que cuelgan las gráficas.
    """
    alumna = _mi_alumna(s, actor)
    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(409, "No tienes un ciclo abierto. Habla con tu coach.")

    chequeo = q.borrador_de(s, alumna.id, ciclo.id)
    if chequeo is None:
        chequeo = Chequeo(
            coach_id=actor.coach_id,
            alumna_id=alumna.id,
            ciclo_id=ciclo.id,
            fecha=_hoy_de(alumna),
            estado=EstadoChequeo.BORRADOR.value,
        )
        s.add(chequeo)
        s.flush()

    return _publico(s, alumna, chequeo)


@ruteador.put("/chequeo/{ulid}", response_model=BorradorChequeo)
def guardar_chequeo(
    ulid: str,
    cuerpo: GuardadoDeChequeo,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Guarda el avance. Todo es opcional: es un borrador, no un envío.

    Los rangos se validan aquí aunque el borrador no se envíe: guardar un peso de 700 kg y
    descubrirlo al final sería peor que rechazarlo al momento.
    """
    alumna = _mi_alumna(s, actor)
    chequeo = _chequeo_editable(s, alumna, ulid)

    if cuerpo.ayuno_confirmado is not None:
        chequeo.ayuno_confirmado = cuerpo.ayuno_confirmado
    if cuerpo.varianza_confirmada is not None:
        chequeo.varianza_confirmada = cuerpo.varianza_confirmada
    if cuerpo.nota_alumna is not None:
        chequeo.nota_alumna = cuerpo.nota_alumna.strip()[:2000] or None
    if cuerpo.bascula_usada is not None:
        chequeo.bascula_usada = cuerpo.bascula_usada[:120] or None
    if cuerpo.lugar_usado is not None:
        chequeo.lugar_usado = cuerpo.lugar_usado[:120] or None
    if cuerpo.hora_usada is not None:
        chequeo.hora_usada = cuerpo.hora_usada[:5] or None

    if cuerpo.peso_kg is not None:
        _guardar_pesaje(s, actor, alumna, chequeo, validar_peso(cuerpo.peso_kg))

    if cuerpo.medidas is not None:
        _guardar_medidas(s, actor, chequeo, cuerpo.medidas)

    return _publico(s, alumna, chequeo)


def _guardar_pesaje(
    s: Session, actor: Actor, alumna: Alumna, chequeo: Chequeo, peso: Decimal
) -> None:
    """Un peso por día, hasta tres días por ciclo.

    La unicidad la impone la base con UNIQUE (alumna_id, fecha); aquí se corrige el del día
    en lugar de intentar insertar otro, porque volver a pesarse el mismo día es corregir, no
    acumular.
    """
    hoy = _hoy_de(alumna)
    del_ciclo = q.pesajes_del_ciclo(s, alumna.id, chequeo.ciclo_id)

    existente = next((p for p in del_ciclo if p.fecha == hoy), None)
    if existente is not None:
        existente.peso_kg = peso
        existente.chequeo_id = chequeo.id
        return

    if len(del_ciclo) >= MAX_PESAJES:
        raise ErrorDeDominio(Codigo.PESAJES_DEL_CICLO_AGOTADOS, maximo=MAX_PESAJES)

    s.add(
        Pesaje(
            coach_id=actor.coach_id,
            alumna_id=alumna.id,
            chequeo_id=chequeo.id,
            fecha=hoy,
            peso_kg=peso,
            bascula_ref=chequeo.bascula_usada or alumna.bascula_ref,
        )
    )


def _guardar_medidas(
    s: Session, actor: Actor, chequeo: Chequeo, entrantes: dict[str, Decimal]
) -> None:
    existentes = {m.tipo: m for m in q.medidas_del_chequeo(s, chequeo.id)}

    for clave, valor in entrantes.items():
        try:
            tipo = TipoMedida(clave)
        except ValueError as causa:
            raise HTTPException(422, f"Medida desconocida: {clave}") from causa

        limpio = validar_medida(tipo, valor)
        fila = existentes.get(tipo.value)
        if fila is None:
            s.add(
                Medida(
                    coach_id=actor.coach_id,
                    chequeo_id=chequeo.id,
                    tipo=tipo.value,
                    valor=limpio,
                )
            )
        else:
            fila.valor = limpio


@ruteador.post("/chequeo/{ulid}/enviar", response_model=BorradorChequeo)
def enviar_chequeo(
    ulid: str,
    actor: Annotated[Actor, Depends(solo_alumna)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Cierra el chequeo y lo manda a evaluación.

    Devuelve **todas** las causas de rechazo juntas, no la primera: la alumna arregla todo de
    una pasada en vez de descubrir un problema nuevo en cada intento.
    """
    alumna = _mi_alumna(s, actor)
    chequeo = _chequeo_editable(s, alumna, ulid)

    resultado = guardas_de_envio(_instantanea(s, alumna, chequeo))
    if not resultado.puede_enviar:
        return _rechazo(resultado.errores, resultado.campos_faltantes)  # type: ignore[return-value]

    chequeo.estado = transicionar(EstadoChequeo(chequeo.estado), Transicion.ENVIAR).value
    chequeo.enviado_en = ahora_utc()
    chequeo.alerta_outlier = resultado.alerta_outlier

    bitacora.registrar(
        s,
        coach_id=actor.coach_id,
        actor_id=actor.usuario_id,
        actor_tipo="alumna",
        accion=bitacora.Accion.CHEQUEO_ENVIADO,
        entidad="chequeo",
        entidad_id=chequeo.id,
        detalle={"alerta_outlier": resultado.alerta_outlier},
    )

    from app.datos.modelos import Coach, Usuario

    coach = s.get(Coach, actor.coach_id)
    usuario = s.get(Usuario, alumna.usuario_id)
    cola.encolar(
        s,
        Aviso.CHEQUEO_RECIBIDO,
        coach_id=actor.coach_id,
        llave=f"chequeo:{chequeo.ulid}:recibido",
        para=usuario.email if usuario else "",
        contexto={
            "nombre": alumna.nombre.split(" ")[0],
            "coach": coach.nombre if coach else "tu coach",
        },
        destinatario_id=alumna.usuario_id,
    )

    return _publico(s, alumna, chequeo)


def _instantanea(s: Session, alumna: Alumna, chequeo: Chequeo) -> Instantanea:
    """Arma lo que el dominio necesita saber, sin que el dominio toque la base."""
    pesajes = q.pesajes_del_ciclo(s, alumna.id, chequeo.ciclo_id)
    del_chequeo = next((p for p in pesajes if p.chequeo_id == chequeo.id), None)
    medidas = q.medidas_del_chequeo(s, chequeo.id)
    fotos = [f for f in q.fotos_de(s, chequeo.id) if f.storage_key is not None]

    protocolo = q.consentimiento_vigente(s, alumna.id, "protocolo_foto")

    # La sincronía peso-fotos se mide con la fecha de **subida**, no con la del EXIF: un
    # teléfono con la hora mal puesta bloquearía un chequeo correcto, y la fecha de subida no
    # se puede falsear desde el cliente.
    fechas_de_fotos = frozenset(
        dia_calendario(f.subida_en, alumna.zona_horaria) for f in fotos if f.subida_en
    )

    return Instantanea(
        estado=EstadoChequeo(chequeo.estado),
        fecha=chequeo.fecha,
        ayuno_confirmado=chequeo.ayuno_confirmado,
        medidas_capturadas=frozenset(TipoMedida(m.tipo) for m in medidas),
        angulos_capturados=frozenset(Angulo(f.angulo) for f in fotos),
        fecha_pesaje=del_chequeo.fecha if del_chequeo else None,
        fechas_de_fotos=fechas_de_fotos,
        peso_kg=del_chequeo.peso_kg if del_chequeo else None,
        peso_anterior_kg=_peso_anterior(s, alumna.id, chequeo.id),
        varianza_confirmada_por_alumna=chequeo.varianza_confirmada,
        cuestionario_completo=alumna.cuestionario_completo,
        protocolo_foto_aceptado=protocolo is not None,
    )


def _rechazo(
    errores: tuple[ErrorDeDominio, ...], campos_faltantes: dict[str, list[str]]
) -> JSONResponse:
    """Traduce el rechazo completo, no solo la primera causa.

    Se responde a mano en lugar de lanzar `ErrorDeDominio` porque el manejador global traduce
    **un** error, y aquí el valor está justo en que van todos: la pantalla marca a la vez la
    medida que falta y la foto que falta, y la alumna resuelve las dos de una pasada.
    """
    estado, mensaje = respuesta_para(errores[0].codigo)
    return JSONResponse(
        status_code=estado,
        content={
            "codigo": errores[0].codigo.value,
            "mensaje": mensaje,
            "detalle": {
                "errores": [
                    {
                        "codigo": e.codigo.value,
                        "mensaje": respuesta_para(e.codigo)[1],
                        "datos": e.detalle,
                    }
                    for e in errores
                ],
                "camposFaltantes": campos_faltantes,
            },
        },
    )
