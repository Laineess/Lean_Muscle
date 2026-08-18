"""Las guardas del acceso: contraseña inicial, freno a la fuerza bruta y qué se filtra.

Son reglas que se comprueban solas, sin base: lo que se prueba aquí es la decisión, no la
consulta. El conteo contra MySQL vive en las pruebas de integración.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from fastapi import HTTPException

from app.compartido.errores import Codigo, ErrorDeDominio
from app.compartido.fechas import ahora_utc
from app.rutas.sesion import Actor, actor_establecido
from app.servicios import limites
from app.servicios.cuentas import validar_contrasena
from app.servicios.seguridad import (
    VIGENCIA_CLAVE_TEMPORAL,
    clave_temporal_vigente,
    contrasena_inicial,
    hash_contrasena,
    verificar_contrasena,
)


class TestContrasenaInicial:
    def test_sale_de_la_configuracion(self) -> None:
        """No va escrita en el código: se rota sin desplegar si se filtra."""
        assert contrasena_inicial()

    def test_se_guarda_cifrada_como_cualquier_otra(self) -> None:
        """Que la conozca la coach no la exime: en la base nunca hay contraseñas en claro."""
        clave = contrasena_inicial()
        guardado = hash_contrasena(clave)
        assert clave not in guardado
        assert verificar_contrasena(guardado, clave)

    def test_dos_cuentas_no_comparten_el_hash(self) -> None:
        """Argon2 sala cada una. Sin eso, un vistazo a la tabla diría quién no la cambió."""
        clave = contrasena_inicial()
        assert hash_contrasena(clave) != hash_contrasena(clave)


class TestReglasDeContrasena:
    """Ocho caracteres, un número y un carácter especial. Es la regla que pidió la clienta."""

    @pytest.mark.parametrize(
        "clara",
        ["buena123!", "Ab3$xq!p", "mi.clave.9", "ocho1234#"],
    )
    def test_acepta_las_que_cumplen(self, clara: str) -> None:
        validar_contrasena(clara)

    @pytest.mark.parametrize(
        ("clara", "por_que"),
        [
            ("corta1!", "menos de ocho"),
            ("sinnumero!", "sin número"),
            ("sinespecial9", "sin carácter especial"),
            ("muylargaperosinnada", "larga pero sin número ni especial"),
        ],
    )
    def test_rechaza_las_que_no(self, clara: str, por_que: str) -> None:
        with pytest.raises(ErrorDeDominio) as caso:
            validar_contrasena(clara)
        assert caso.value.codigo is Codigo.CONTRASENA_DEBIL, por_que

    def test_la_inicial_no_sirve_como_definitiva(self) -> None:
        """La conoce la coach: nadie debería poder dejarla puesta."""
        with pytest.raises(ErrorDeDominio):
            validar_contrasena(contrasena_inicial())


class TestClaveInicialCaduca:
    """La contraseña de alta y la de restablecimiento son públicas: la coach las dicta.

    Por eso llevan plazo. Sin él, quien conociera el correo de una alumna que todavía no ha
    entrado podría tomarle la cuenta el día que quisiera, y `ClaveTemporal.vence_en` existía
    sin que nadie lo mirara.
    """

    def test_dentro_del_plazo_vale(self) -> None:
        assert clave_temporal_vigente(ahora_utc() + timedelta(hours=1))

    def test_pasado_el_plazo_no(self) -> None:
        assert not clave_temporal_vigente(ahora_utc() - timedelta(minutes=1))

    def test_el_plazo_es_de_un_dia(self) -> None:
        """Suficiente para que la alumna la use, corto para que no quede abierta."""
        assert VIGENCIA_CLAVE_TEMPORAL == timedelta(hours=24)


class TestGuardaDeSesion:
    """Mientras no la cambie, la sesión existe pero no abre nada.

    Es lo que convierte una contraseña que conoce cualquiera en una contraseña de un solo
    uso. Sin esta guarda, la inicial sería una puerta abierta permanente.
    """

    def test_quien_no_la_cambio_no_pasa(self) -> None:
        nueva = Actor(usuario_id=1, coach_id=1, rol="alumna", debe_cambiar_contrasena=True)
        with pytest.raises(HTTPException) as caso:
            actor_establecido(nueva)
        assert caso.value.status_code == 403
        assert caso.value.detail["codigo"] == Codigo.CONTRASENA_INICIAL_SIN_CAMBIAR.value

    def test_quien_ya_la_cambio_pasa(self) -> None:
        establecida = Actor(usuario_id=1, coach_id=1, rol="alumna")
        assert actor_establecido(establecida) is establecida

    def test_la_guarda_tambien_aplica_a_la_coach(self) -> None:
        """No es una regla para alumnas: la cuenta de la coach abre el panel entero."""
        recien_creada = Actor(usuario_id=2, coach_id=1, rol="coach", debe_cambiar_contrasena=True)
        with pytest.raises(HTTPException):
            actor_establecido(recien_creada)


class TestLimitesDeAcceso:
    def test_el_limite_por_correo_es_mas_estricto_que_el_de_ip(self) -> None:
        """Una casa o un gimnasio comparten salida a internet: cortar la IP al quinto fallo
        dejaría fuera a quien no hizo nada."""
        assert limites.LIMITE_POR_CORREO < limites.LIMITE_POR_IP

    def test_la_ventana_es_corta(self) -> None:
        """Larga castiga al que se equivoca; corta no frena. Quince minutos es el punto en el
        que un ataque no alcanza la décima prueba y una persona espera poco."""
        assert 5 <= limites.VENTANA.total_seconds() / 60 <= 60

    def test_los_intentos_no_se_guardan_para_siempre(self) -> None:
        """Pasado el bloqueo son ruido, y guardan correos de gente que ni existe."""
        assert limites.RETENCION.days <= 90
