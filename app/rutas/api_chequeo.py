"""Captura del chequeo mensual, desde el frente de alumna.

El borrador se guarda en el servidor y no en el navegador: la alumna hace esto de pie, en
ayunas, y perder la captura por cerrar la pestaña significa esperar al mes siguiente.

Las guardas de envío las evalúa el dominio; la pantalla las repite por cortesía, pero las
que mandan son estas.
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
from app.datos.modelos import Alumna, Chequeo, Ciclo, Medida, Pesaje
from app.datos.repos import consultas as q
from app.dominio.agenda import TipoCita, ventana_de_chequeo
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
from app.rutas.sesion import Actor, RutaQueConfirma, datos, solo_alumna_aceptada
from app.rutas.traduccion import respuesta_para
from app.servicios import avisos as cola
from app.servicios import bitacora

ruteador = APIRouter(prefix="/api/mi", tags=["chequeo"], route_class=RutaQueConfirma)

#: Tope de pesajes por ciclo. El promedio quita el ruido de un día de retención.
MAX_PESAJES = 3


def _mi_alumna(s: Session, actor: Actor) -> Alumna:
    alumna = q.alumna_de_usuario(s, actor.usuario_id)
    if alumna is None:
        raise ErrorDeDominio(Codigo.SIN_PERMISO)
    return alumna


def _hoy_de(alumna: Alumna) -> date:
    """El día calendario de la alumna: en Tijuana no se pierde el chequeo porque en Mérida
    ya sea otro día."""
    return dia_calendario(ahora_utc(), alumna.zona_horaria)


def _numero_de(s: Session, alumna_id: int, chequeo: Chequeo) -> int:
    """Lo que la alumna ve como «Chequeo #5». Solo cuentan los enviados: contar el borrador
    le inventaba un chequeo que no existe."""
    historial = q.chequeos_enviados(s, alumna_id)
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


def _exigir_ventana_de_consulta(s: Session, alumna: Alumna, ciclo: Ciclo) -> None:
    """El chequeo se captura alrededor de la consulta agendada: es lo que ata la medición a
    la revisión. Unas medidas de hace tres semanas ya no describen el ciclo."""
    consultas = [
        c
        for c in q.citas_de_alumna(s, alumna.id)
        if c.inicia_en.date() >= ciclo.inicia_en and c.tipo == TipoCita.CONSULTA.value
    ]
    if not consultas:
        raise HTTPException(
            409,
            "Tu coach todavía no agenda tu consulta de este ciclo. En cuanto lo haga, aquí "
            "aparece tu chequeo.",
        )

    hoy = _hoy_de(alumna)
    ventanas = [ventana_de_chequeo(c.inicia_en) for c in consultas]
    if any(v.abierta(hoy) for v in ventanas):
        return

    proxima = next((v for v in ventanas if hoy < v.desde), None)
    if proxima is not None:
        raise HTTPException(
            409,
            f"Tu chequeo se abre el {proxima.desde:%d/%m/%Y}, tres días antes de tu consulta "
            f"del {proxima.consulta:%d/%m/%Y}.",
        )

    ultima = ventanas[-1]
    raise HTTPException(
        409,
        f"El plazo para el chequeo de tu consulta del {ultima.consulta:%d/%m/%Y} cerró el "
        f"{ultima.hasta:%d/%m/%Y}. Pídele a tu coach otra fecha.",
    )


@ruteador.post("/chequeo", response_model=BorradorChequeo)
def abrir_chequeo(
    actor: Annotated[Actor, Depends(solo_alumna_aceptada)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Abre el chequeo del ciclo o devuelve el abierto. Idempotente: entrar dos veces no
    crea dos. Uno en `rechazado_calidad` se retoma para no romper la numeración."""
    alumna = _mi_alumna(s, actor)
    ciclo = q.ciclo_vigente(s, alumna.id)
    if ciclo is None:
        raise HTTPException(409, "No tienes un ciclo abierto. Habla con tu coach.")

    chequeo = q.borrador_de(s, alumna.id, ciclo.id)
    if chequeo is None:
        _exigir_ventana_de_consulta(s, alumna, ciclo)
        # Un chequeo por ciclo. Sin esta comprobación, volver a esta pantalla después de
        # enviar creaba un borrador vacío que se convertía en «el último» de la alumna: la
        # coach veía «borrador» en su cartera, el chequeo enviado desaparecía de la bandeja
        # de pendientes y no había forma de llegar a validarlo.
        for ya in q.chequeos_de(s, alumna.id):
            if ya.ciclo_id != ciclo.id:
                continue
            if ya.estado == EstadoChequeo.PENDIENTE_EVALUACION.value:
                raise HTTPException(
                    409, "Ya enviaste el chequeo de este ciclo. Tu coach lo está revisando."
                )
            if ya.estado == EstadoChequeo.VALIDADO.value:
                raise HTTPException(
                    409,
                    "El chequeo de este ciclo ya está validado. El siguiente toca el mes que entra.",
                )

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
    actor: Annotated[Actor, Depends(solo_alumna_aceptada)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Guarda el avance; todo es opcional. Los rangos se validan igual: descubrir un peso
    de 700 kg al final sería peor que rechazarlo al momento."""
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
    """Un peso por día, hasta tres por ciclo. Volver a pesarse el mismo día corrige el
    valor en vez de acumular otro."""
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
    actor: Annotated[Actor, Depends(solo_alumna_aceptada)],
    s: Annotated[Session, Depends(datos)],
) -> BorradorChequeo:
    """Cierra el chequeo y lo manda a evaluación. Devuelve todas las causas de rechazo
    juntas: la alumna arregla todo de una pasada."""
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

    # Y a la coach, que es quien tiene que hacer algo con él.
    suyo = q.usuario_de_coach(s)
    if suyo is not None:
        cola.encolar(
            s,
            Aviso.CHEQUEO_LISTO,
            coach_id=actor.coach_id,
            llave=f"chequeo:{chequeo.ulid}:listo",
            para=suyo.email,
            contexto={"alumna": alumna.nombre},
            destinatario_id=suyo.id,
        )

    return _publico(s, alumna, chequeo)


def _instantanea(s: Session, alumna: Alumna, chequeo: Chequeo) -> Instantanea:
    """Arma lo que el dominio necesita saber, sin que el dominio toque la base."""
    pesajes = q.pesajes_del_ciclo(s, alumna.id, chequeo.ciclo_id)
    del_chequeo = next((p for p in pesajes if p.chequeo_id == chequeo.id), None)
    medidas = q.medidas_del_chequeo(s, chequeo.id)
    fotos = [f for f in q.fotos_de(s, chequeo.id) if f.storage_key is not None]

    protocolo = q.consentimiento_vigente(s, alumna.id, "protocolo_foto")

    # Por fecha de subida y no de EXIF: un teléfono con la hora mal puesta bloquearía un
    # chequeo correcto, y la de subida no se puede falsear desde el cliente.
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
    """Traduce el rechazo completo. Se responde a mano porque el manejador global traduce
    un solo error, y aquí el valor está en que vayan todos juntos."""
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
