"""Trabajo diario de recordatorios: pagos, citas, inactividad y purga de fotos.

Solo **decide y encola**; el envío lo hace `emisor_avisos.py`. Separarlo importa: si el
correo falla, los recordatorios de mañana siguen calculándose igual, y un aviso encolado no
se pierde porque el servidor SMTP estuviera caído a las 6 de la mañana.

Cruza inquilinos, que es exactamente el caso que la excepción de `sin_alcance` contempla.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.compartido.fechas import ahora_utc, en_zona
from app.config import ajustes
from app.datos.modelos import (
    Alumna,
    Chequeo,
    Ciclo,
    Cita,
    Coach,
    CobroProgramado,
    Foto,
    Pago,
    SolicitudDeRegistro,
    Usuario,
)
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio import avisos as av
from app.dominio import registro as reg
from app.servicios import avisos as cola

#: Cómo se le nombra a lo que le falta, para que el correo se lo diga con palabras suyas.
PENDIENTE_DE = {
    reg.Paso.CORREO: "confirmar tu correo con el código que te mandamos",
    reg.Paso.CUESTIONARIO: "contestar el cuestionario de tu coach",
    reg.Paso.CITA: "reservar tu primera consulta",
    reg.Paso.COMPROBANTE: "subir tu comprobante de inscripción",
    reg.Paso.ESPERA: "nada: ya está todo de tu lado",
    reg.Paso.LISTA: "nada",
}


@dataclass(frozen=True, slots=True)
class Resultado:
    pagos_proximos: int
    pagos_vencidos: int
    citas: int
    inactividad: int
    purgas: int
    registros: int = 0

    @property
    def total(self) -> int:
        return (
            self.pagos_proximos
            + self.pagos_vencidos
            + self.citas
            + self.inactividad
            + self.purgas
            + self.registros
        )


def _encolar(
    s: Session,
    pendiente: av.Pendiente,
    *,
    coach_id: int,
    usuario_id: int | None,
    correo: str,
    contexto: dict[str, object],
) -> bool:
    """Encola el aviso si no se había encolado antes.

    La llave la construye el dominio e identifica el disparo. Su unicidad es lo que impide
    que dos corridas del trabajo manden el mismo recordatorio dos veces.
    """
    return (
        cola.encolar(
            s,
            pendiente.aviso,
            coach_id=coach_id,
            llave=pendiente.llave,
            para=correo,
            contexto=contexto,
            destinatario_id=usuario_id,
            canales=pendiente.canales,
        )
        > 0
    )


def correr() -> Resultado:
    hoy = ahora_utc().date()
    ahora = ahora_utc()
    retencion = ajustes().retencion_fotos_meses

    pagos_proximos = pagos_vencidos = citas = inactividad = purgas = registros = 0

    with sesion_sin_alcance("recordatorios diarios; cruzan inquilinos") as s:
        coaches = {c.id: c for c in s.scalars(select(Coach))}
        alumnas = {a.id: a for a in s.scalars(select(Alumna)).all() if a.estado == "activa"}
        usuarios = {u.id: u for u in s.scalars(select(Usuario))}

        def datos_de(alumna: Alumna) -> tuple[str, str, str] | None:
            """(correo, nombre de pila, nombre de la coach), o None si falta algo."""
            usuario = usuarios.get(alumna.usuario_id) if alumna.usuario_id else None
            coach = coaches.get(alumna.coach_id)
            if usuario is None or coach is None or not usuario.email:
                return None
            return usuario.email, alumna.nombre.split(" ")[0], coach.nombre

        # ---- Pagos: próximos y vencidos ----------------------------------
        pagados = {p.ciclo_id for p in s.scalars(select(Pago)) if p.estado == "validado"}
        for ciclo in s.scalars(select(Ciclo)):
            alumna = alumnas.get(ciclo.alumna_id)
            if alumna is None:
                continue
            info = datos_de(alumna)
            if info is None:
                continue
            correo, nombre, coach_nombre = info
            pagado = ciclo.id in pagados

            contexto = {
                "nombre": nombre,
                "coach": coach_nombre,
                "vence": f"{ciclo.termina_en:%d/%m/%Y}",
                "ciclo": ciclo.numero,
            }

            proximo = av.toca_recordar_pago(ciclo.termina_en, hoy, pagado, str(ciclo.ulid))
            if proximo and _encolar(
                s,
                proximo,
                coach_id=ciclo.coach_id,
                usuario_id=alumna.usuario_id,
                correo=correo,
                contexto=contexto,
            ):
                pagos_proximos += 1

            vencido = av.toca_avisar_vencido(ciclo.termina_en, hoy, pagado, str(ciclo.ulid))
            if vencido and _encolar(
                s,
                vencido,
                coach_id=ciclo.coach_id,
                usuario_id=alumna.usuario_id,
                correo=correo,
                contexto=contexto,
            ):
                pagos_vencidos += 1

        # ---- Citas de mañana ---------------------------------------------
        ventana = s.scalars(
            select(Cita).where(
                Cita.inicia_en >= ahora,
                Cita.inicia_en <= ahora + av.ANTICIPACION_CITA,
                Cita.estado != "cancelada",
            )
        )
        for cita in ventana:
            if cita.alumna_id is None:
                # Un bloque de trabajo de la coach no le manda recordatorio a nadie.
                continue
            alumna = alumnas.get(cita.alumna_id)
            if alumna is None:
                continue
            info = datos_de(alumna)
            if info is None:
                continue
            correo, nombre, coach_nombre = info

            pendiente = av.toca_recordar_cita(
                cita.inicia_en, ahora, cita.recordatorio_enviado_en is not None, str(cita.ulid)
            )
            if pendiente and _encolar(
                s,
                pendiente,
                coach_id=cita.coach_id,
                usuario_id=alumna.usuario_id,
                correo=correo,
                contexto={
                    "nombre": nombre,
                    "coach": coach_nombre,
                    # En la hora de ella: el UTC crudo le corría la consulta seis horas.
                    "fecha": f"{en_zona(cita.inicia_en, alumna.zona_horaria):%d/%m/%Y}",
                    "hora_inicio": f"{en_zona(cita.inicia_en, alumna.zona_horaria):%H:%M}",
                    "hora_fin": f"{en_zona(cita.termina_en, alumna.zona_horaria):%H:%M}",
                    "modalidad": cita.modalidad,
                    "detalle": cita.notas or "",
                },
            ):
                cita.recordatorio_enviado_en = ahora
                citas += 1

        # ---- Inactividad --------------------------------------------------
        for alumna in alumnas.values():
            usuario = usuarios.get(alumna.usuario_id) if alumna.usuario_id else None
            info = datos_de(alumna)
            if usuario is None or info is None:
                continue
            correo, nombre, coach_nombre = info
            ultimo = usuario.ultimo_acceso_en.date() if usuario.ultimo_acceso_en else None

            pendiente = av.toca_avisar_inactividad(ultimo, hoy, False, str(alumna.ulid))
            if pendiente and _encolar(
                s,
                pendiente,
                coach_id=alumna.coach_id,
                usuario_id=alumna.usuario_id,
                correo=correo,
                contexto={"nombre": nombre, "coach": coach_nombre},
            ):
                inactividad += 1

        # ---- Purga de fotos: aviso 15 días antes ---------------------------
        # Una foto llega a su alumna a través del chequeo, así que el JOIN va por ahí.
        limite = ahora - timedelta(days=retencion * 30 - av.ANTICIPACION_PURGA.days)
        proximas_a_purgar = s.execute(
            select(Foto, Chequeo.alumna_id)
            .join(Chequeo, Chequeo.id == Foto.chequeo_id)
            .where(Foto.purgada_en.is_(None), Foto.tomada_en <= limite)
        ).all()

        for foto, alumna_id in proximas_a_purgar:
            if foto.tomada_en is None:
                continue
            alumna = alumnas.get(alumna_id)
            if alumna is None:
                continue
            info = datos_de(alumna)
            if info is None:
                continue
            correo, nombre, coach_nombre = info

            pendiente = av.toca_avisar_purga(foto.tomada_en.date(), hoy, retencion, str(foto.ulid))
            if pendiente and _encolar(
                s,
                pendiente,
                coach_id=foto.coach_id,
                usuario_id=alumna.usuario_id,
                correo=correo,
                contexto={
                    "nombre": nombre,
                    "coach": coach_nombre,
                    "mes": f"{foto.tomada_en:%B}",
                    "fecha": f"{foto.tomada_en.date() + timedelta(days=retencion * 30):%d/%m/%Y}",
                },
            ):
                purgas += 1

        # ---- Registros a medias -------------------------------------------
        # Van aparte del bucle de alumnas: una solicitante no está en `alumnas`, que solo
        # trae a las activas.
        for solicitud in s.scalars(select(SolicitudDeRegistro)):
            if not reg.toca_recordar(
                reg.Estado(solicitud.estado),
                solicitud.creado_en,
                ahora,
                solicitud.recordatorio_enviado_en is not None,
            ):
                continue

            candidata = s.get(Alumna, solicitud.alumna_id)
            coach = coaches.get(solicitud.coach_id)
            usuario = (
                usuarios.get(candidata.usuario_id)
                if candidata is not None and candidata.usuario_id
                else None
            )
            if candidata is None or coach is None or usuario is None:
                continue

            # Se consulta lo suyo en lugar de suponerlo: el correo le nombra lo que le
            # falta, y decirle que reserve una consulta que ya reservó la manda de vuelta
            # a una pantalla donde no hay nada que hacer.
            tiene_cita = (
                s.scalars(
                    select(Cita).where(Cita.alumna_id == candidata.id, Cita.estado != "cancelada")
                ).first()
                is not None
            )
            comprobante = (
                s.scalars(
                    select(CobroProgramado).where(
                        CobroProgramado.alumna_id == candidata.id,
                        CobroProgramado.estado.in_(("en_revision", "pagado")),
                    )
                ).first()
                is not None
            )
            paso = reg.paso_actual(
                estado=reg.Estado(solicitud.estado),
                cuestionario_completo=candidata.cuestionario_completo,
                tiene_cita=tiene_cita,
                comprobante_subido=comprobante,
            )
            if cola.encolar(
                s,
                av.Aviso.REGISTRO_SIN_TERMINAR,
                coach_id=solicitud.coach_id,
                llave=f"solicitud:{solicitud.ulid}:sin-terminar",
                para=usuario.email,
                contexto={
                    "nombre": candidata.nombre.split(" ")[0],
                    "coach": coach.marca or coach.nombre,
                    "pendiente": PENDIENTE_DE[paso],
                    "dias": reg.AVISO_BORRADO.days,
                },
                destinatario_id=usuario.id,
            ):
                solicitud.recordatorio_enviado_en = ahora
                registros += 1

    return Resultado(pagos_proximos, pagos_vencidos, citas, inactividad, purgas, registros)


def main() -> None:  # pragma: no cover - punto de entrada del timer de systemd
    r = correr()
    print(
        f"encolados={r.total} pagos_proximos={r.pagos_proximos} vencidos={r.pagos_vencidos} "
        f"citas={r.citas} inactividad={r.inactividad} purgas={r.purgas}"
    )


if __name__ == "__main__":  # pragma: no cover
    main()
