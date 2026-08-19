"""Semilla de desarrollo. Crea dos coaches a propósito: sin un segundo inquilino, una fuga
entre coaches es invisible durante el desarrollo.

    python -m app.semilla              # siembra si la base está vacía
    python -m app.semilla --reiniciar  # borra y vuelve a sembrar
"""

from __future__ import annotations

import argparse
import hashlib
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.datos.modelos import (
    Alimento,
    Alumna,
    Chequeo,
    Ciclo,
    Cita,
    Coach,
    CobroCoach,
    CobroProgramado,
    Consentimiento,
    Ejercicio,
    Foto,
    HistorialClinico,
    HorarioDeAtencion,
    Medida,
    Mensaje,
    Pago,
    ParametrosCiclo,
    Pesaje,
    Plan,
    PreguntaCuestionario,
    PresentacionCoach,
    Servicio,
    SuscripcionCoach,
    Tarifa,
    Usuario,
)
from app.datos.sin_alcance import sesion_sin_alcance
from app.dominio.medidas import TipoMedida
from app.servicios.seguridad import hash_contrasena

CLAVE_DEMO = "Demo1234!"
HOY = date(2026, 8, 13)


def _marcador_de_foto(llave: str, angulo: str, cuando: str) -> None:
    """Imagen de relleno para que la pantalla de validacion no salga con las imagenes rotas.
    Un marcador evidente, no una silueta que pueda confundirse con la foto de alguien."""
    from io import BytesIO

    from PIL import Image, ImageDraw

    from app.servicios.almacenamiento import almacen

    for ancho, alto, sufijo in ((1200, 1600, ""), (320, 427, "-mini")):
        lienzo = Image.new("RGB", (ancho, alto), (238, 238, 236))
        pincel = ImageDraw.Draw(lienzo)
        margen = ancho // 12
        pincel.rectangle(
            [margen, margen, ancho - margen, alto - margen], outline=(200, 200, 196), width=3
        )
        pincel.text((margen + 12, margen + 12), f"ejemplo · {angulo}", fill=(120, 120, 118))
        pincel.text((margen + 12, margen + 30), cuando, fill=(150, 150, 148))

        salida = BytesIO()
        lienzo.save(salida, format="WEBP", quality=70, method=4)
        almacen().guardar(llave.replace(".webp", f"{sufijo}.webp"), salida.getvalue())


def _momento(dia: date, hora: int = 12) -> datetime:
    return datetime(dia.year, dia.month, dia.day, hora, tzinfo=UTC)


def _hash_texto(texto: str) -> str:
    """Hash del texto legal aceptado. Es lo que hace verificable el consentimiento."""
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Datos
# ---------------------------------------------------------------------------

CONSENTIMIENTOS = [
    ("terminos", "1.0", "Términos y Condiciones de uso de MyFittPlan."),
    ("privacidad", "2.0", "Aviso de Privacidad de MyFittPlan."),
    ("datos_salud", "2.0", "Consentimiento expreso para el tratamiento de datos de salud."),
    ("protocolo_foto", "2.0", "Aceptación del protocolo fotográfico sin rostro."),
]

#: Chequeos de la alumna principal. Medidas en el orden de `TipoMedida`.
CHEQUEOS_ANDREA: list[dict[str, Any]] = [
    {
        "numero": 1,
        "fecha": date(2026, 5, 3),
        "estado": "validado",
        "peso": "68.4",
        "grasa": "0.312",
        "medidas": {
            "cintura": "78.5",
            "abdomen": "84.0",
            "cadera": "98.0",
            "busto": "92.0",
            "pecho": "88.0",
            "brazo": "28.5",
            "muslo": "56.0",
            "pantorrilla": "35.5",
        },
        "feedback": "Excelente punto de partida. La postura en la toma de perfil está "
        "perfecta: brazos relajados y abdomen neutro. Arrancamos con déficit moderado.",
    },
    {
        "numero": 2,
        "fecha": date(2026, 6, 1),
        "estado": "validado",
        "peso": "67.1",
        "grasa": "0.298",
        "medidas": {
            "cintura": "76.8",
            "abdomen": "82.4",
            "cadera": "97.2",
            "busto": "91.0",
            "pecho": "87.5",
            "brazo": "28.6",
            "muslo": "55.8",
            "pantorrilla": "35.5",
        },
        "feedback": "Buen mes. Bajó cintura sin perder brazo, que es justo lo que buscábamos. "
        "Subimos proteína 10 g y agregamos un día de pierna.",
    },
    {
        "numero": 3,
        "fecha": date(2026, 7, 1),
        "estado": "validado",
        "peso": "66.3",
        "grasa": "0.286",
        "medidas": {
            "cintura": "75.4",
            "abdomen": "81.0",
            "cadera": "96.5",
            "busto": "90.5",
            "pecho": "87.0",
            "brazo": "28.8",
            "muslo": "55.4",
            "pantorrilla": "35.4",
        },
        "feedback": "Sigue el descenso constante. Ojo con la iluminación de la foto de espalda: "
        "se ve más oscura que el mes pasado. Misma ventana, misma hora.",
    },
    {
        "numero": 4,
        "fecha": date(2026, 8, 1),
        "estado": "pendiente_evaluacion",
        "peso": "65.2",
        "grasa": "0.271",
        "medidas": {
            "cintura": "74.1",
            "abdomen": "79.6",
            "cadera": "95.8",
            "busto": "90.0",
            "pecho": "86.6",
            "brazo": "29.0",
            "muslo": "55.0",
            "pantorrilla": "35.4",
        },
        "feedback": None,
    },
]

#: Cartera de la coach principal. La primera es Andrea, con historial completo.
CARTERA: list[dict[str, Any]] = [
    {
        "nombre": "Andrea Sáenz",
        "correo": "andrea.saenz@ejemplo.mx",
        "nac": date(1994, 3, 22),
        "estatura": 165,
        "objetivo": "recomposicion",
        "nivel": "intermedio",
        "ciclo": 4,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Paola Rentería",
        "correo": "paola.renteria@ejemplo.mx",
        "nac": date(1990, 11, 4),
        "estatura": 158,
        "objetivo": "perdida_grasa",
        "nivel": "avanzado",
        "ciclo": 6,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Renata Ibáñez",
        "correo": "renata.ibanez@ejemplo.mx",
        "nac": date(1998, 6, 17),
        "estatura": 171,
        "objetivo": "ganancia_masa",
        "nivel": "principiante",
        "ciclo": 2,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Ximena Ordaz",
        "correo": "ximena.ordaz@ejemplo.mx",
        "nac": date(1987, 1, 30),
        "estatura": 163,
        "objetivo": "recomposicion",
        "nivel": "avanzado",
        "ciclo": 9,
        "pago": "pendiente",
        "estado": "activa",
    },
    {
        "nombre": "Daniela Fuentes",
        "correo": "daniela.fuentes@ejemplo.mx",
        "nac": date(1995, 9, 12),
        "estatura": 168,
        "objetivo": "perdida_grasa",
        "nivel": "intermedio",
        "ciclo": 3,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Sofía Bustamante",
        "correo": "sofia.bustamante@ejemplo.mx",
        "nac": date(2001, 4, 8),
        "estatura": 160,
        "objetivo": "ganancia_masa",
        "nivel": "principiante",
        "ciclo": 1,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Lucía Márquez",
        "correo": "lucia.marquez@ejemplo.mx",
        "nac": date(1992, 12, 1),
        "estatura": 166,
        "objetivo": "recomposicion",
        "nivel": "intermedio",
        "ciclo": 5,
        "pago": "pendiente",
        "estado": "pausa",
    },
]

#: Segundo inquilino. Su única razón de ser es que una fuga se vea.
CARTERA_SEGUNDA = [
    {
        "nombre": "Valeria Nieto",
        "correo": "valeria.nieto@ejemplo.mx",
        "nac": date(1993, 2, 14),
        "estatura": 170,
        "objetivo": "perdida_grasa",
        "nivel": "intermedio",
        "ciclo": 2,
        "pago": "validado",
        "estado": "activa",
    },
    {
        "nombre": "Camila Duarte",
        "correo": "camila.duarte@ejemplo.mx",
        "nac": date(1996, 8, 25),
        "estatura": 162,
        "objetivo": "recomposicion",
        "nivel": "principiante",
        "ciclo": 1,
        "pago": "validado",
        "estado": "activa",
    },
]

PLAN_NUTRICION: dict[str, Any] = {
    "notas": "Come la mayor parte de los carbohidratos alrededor del entrenamiento. "
    "Dos litros de agua mínimo.",
    "tiempos": [
        {
            "nombre": "Desayuno",
            "hora": "07:30",
            "kcal": 480,
            "alimentos": [
                {
                    "nombre": "Claras de huevo",
                    "porcion": "200 g",
                    "kcal": 104,
                    "p": 22,
                    "c": 2,
                    "g": 0,
                },
                {"nombre": "Avena", "porcion": "60 g", "kcal": 228, "p": 8, "c": 40, "g": 4},
                {"nombre": "Arándanos", "porcion": "80 g", "kcal": 46, "p": 1, "c": 11, "g": 0},
                {"nombre": "Almendras", "porcion": "15 g", "kcal": 102, "p": 4, "c": 3, "g": 9},
            ],
        },
        {
            "nombre": "Comida",
            "hora": "14:00",
            "kcal": 620,
            "alimentos": [
                {
                    "nombre": "Pechuga de pollo",
                    "porcion": "180 g",
                    "kcal": 297,
                    "p": 56,
                    "c": 0,
                    "g": 7,
                },
                {
                    "nombre": "Arroz integral cocido",
                    "porcion": "180 g",
                    "kcal": 200,
                    "p": 4,
                    "c": 42,
                    "g": 2,
                },
                {
                    "nombre": "Ensalada verde",
                    "porcion": "150 g",
                    "kcal": 38,
                    "p": 2,
                    "c": 6,
                    "g": 0,
                },
                {
                    "nombre": "Aceite de oliva",
                    "porcion": "10 ml",
                    "kcal": 88,
                    "p": 0,
                    "c": 0,
                    "g": 10,
                },
            ],
        },
        {
            "nombre": "Colación",
            "hora": "17:30",
            "kcal": 260,
            "alimentos": [
                {
                    "nombre": "Yogur griego sin lactosa",
                    "porcion": "170 g",
                    "kcal": 145,
                    "p": 17,
                    "c": 8,
                    "g": 4,
                },
                {"nombre": "Plátano", "porcion": "1 pieza", "kcal": 105, "p": 1, "c": 27, "g": 0},
            ],
        },
        {
            "nombre": "Cena",
            "hora": "20:30",
            "kcal": 490,
            "alimentos": [
                {"nombre": "Salmón", "porcion": "150 g", "kcal": 312, "p": 34, "c": 0, "g": 19},
                {
                    "nombre": "Camote horneado",
                    "porcion": "150 g",
                    "kcal": 129,
                    "p": 2,
                    "c": 30,
                    "g": 0,
                },
                {"nombre": "Espárragos", "porcion": "120 g", "kcal": 24, "p": 3, "c": 4, "g": 0},
            ],
        },
    ],
}

PLAN_ENTRENAMIENTO: dict[str, Any] = {
    "plantilla": "Fuerza superior/inferior — 4 días",
    "notas": "Descansa 90 s entre series compuestas y 60 s en accesorios. "
    "Deja siempre 2 repeticiones en reserva.",
    "dias": [
        {
            "nombre": "Día 1 · Tren inferior",
            "ejercicios": [
                {
                    "nombre": "Sentadilla trasera",
                    "series": 4,
                    "reps": "6-8",
                    "carga": "45 kg",
                    "nota": "Profundidad hasta paralelo. Rodilla izquierda: nada de valgo.",
                },
                {
                    "nombre": "Peso muerto rumano",
                    "series": 3,
                    "reps": "8-10",
                    "carga": "40 kg",
                    "nota": "Barra pegada a la pierna.",
                },
                {
                    "nombre": "Prensa de pierna",
                    "series": 3,
                    "reps": "10-12",
                    "carga": "90 kg",
                    "nota": "",
                },
                {
                    "nombre": "Elevación de talones sentada",
                    "series": 4,
                    "reps": "12-15",
                    "carga": "25 kg",
                    "nota": "",
                },
            ],
        },
        {
            "nombre": "Día 2 · Tren superior (empuje)",
            "ejercicios": [
                {
                    "nombre": "Press de banca con mancuernas",
                    "series": 4,
                    "reps": "8-10",
                    "carga": "14 kg",
                    "nota": "",
                },
                {
                    "nombre": "Press militar sentada",
                    "series": 3,
                    "reps": "8-10",
                    "carga": "10 kg",
                    "nota": "Sin arquear la espalda baja.",
                },
                {
                    "nombre": "Fondos en máquina asistida",
                    "series": 3,
                    "reps": "10-12",
                    "carga": "-20 kg",
                    "nota": "",
                },
                {
                    "nombre": "Extensión de tríceps en polea",
                    "series": 3,
                    "reps": "12-15",
                    "carga": "15 kg",
                    "nota": "",
                },
            ],
        },
        {
            "nombre": "Día 3 · Tren inferior (cadena posterior)",
            "ejercicios": [
                {
                    "nombre": "Hip thrust",
                    "series": 4,
                    "reps": "8-10",
                    "carga": "60 kg",
                    "nota": "Pausa de 1 s arriba.",
                },
                {
                    "nombre": "Zancada búlgara",
                    "series": 3,
                    "reps": "10 por pierna",
                    "carga": "12 kg",
                    "nota": "",
                },
                {
                    "nombre": "Curl femoral acostada",
                    "series": 3,
                    "reps": "12-15",
                    "carga": "25 kg",
                    "nota": "",
                },
            ],
        },
        {
            "nombre": "Día 4 · Tren superior (jalón)",
            "ejercicios": [
                {
                    "nombre": "Jalón al pecho",
                    "series": 4,
                    "reps": "8-10",
                    "carga": "35 kg",
                    "nota": "",
                },
                {
                    "nombre": "Remo con barra",
                    "series": 3,
                    "reps": "8-10",
                    "carga": "30 kg",
                    "nota": "Torso a 45°.",
                },
                {"nombre": "Face pull", "series": 3, "reps": "15", "carga": "12 kg", "nota": ""},
                {
                    "nombre": "Curl de bíceps con mancuerna",
                    "series": 3,
                    "reps": "10-12",
                    "carga": "8 kg",
                    "nota": "",
                },
            ],
        },
    ],
}

MENSAJES = [
    (
        "alumna",
        "Hola Mariana, en el hip thrust siento que se me carga la espalda baja en vez "
        "del glúteo. ¿Qué ajusto?",
        datetime(2026, 8, 11, 18, 2, tzinfo=UTC),
    ),
    (
        "coach",
        "Casi siempre es el rango: estás subiendo de más y la pelvis se va a anteversión. "
        "Termina el movimiento cuando el tronco quede paralelo al piso y mete un poco la "
        "costilla. Prueba mañana con 50 kg y me cuentas.",
        datetime(2026, 8, 11, 19, 40, tzinfo=UTC),
    ),
    (
        "alumna",
        "Probé con 50 y sí, se sintió muchísimo mejor. Gracias.",
        datetime(2026, 8, 12, 20, 15, tzinfo=UTC),
    ),
]


# ---------------------------------------------------------------------------
# Siembra
# ---------------------------------------------------------------------------


#: Preguntas de ejemplo. Son suyas: sirven para que la pantalla no se vea vacia y para
#: ensenar los cuatro tipos disponibles.
PREGUNTAS_DEMO: tuple[tuple[str, str, tuple[str, ...], bool], ...] = (
    ("Cuantas horas duermes entre semana?", "numero", (), True),
    ("Has llevado alguna dieta antes?", "si_no", (), False),
    (
        "Como describirias tu nivel de entrenamiento?",
        "opcion",
        ("Nunca he entrenado", "Principiante", "Intermedia", "Avanzada"),
        True,
    ),
    ("Que te gustaria lograr en los proximos seis meses?", "texto_largo", (), False),
)


def sembrar_coach(
    sesion: Any,
    *,
    nombre: str,
    slug: str,
    marca: str,
    email: str,
    color: str,
    cartera: list[dict[str, Any]],
    con_historial: bool,
) -> int:
    coach = Coach(
        nombre=nombre,
        marca=marca,
        slug=slug,
        email=email,
        plan="profesional",
        limite_alumnas=60,
        estado="activa",
        color_acento=color,
        precio_ciclo=Decimal("1200.00"),
        dia_chequeo=1,
    )
    sesion.add(coach)
    sesion.flush()

    sesion.add(
        Usuario(
            coach_id=coach.id,
            rol="coach",
            email=email,
            hash_contrasena=hash_contrasena(CLAVE_DEMO),
            estado="activo",
        )
    )

    sesion.add(
        PresentacionCoach(
            coach_id=coach.id,
            titulo=f"Hola, soy {nombre.split(' ')[0]}",
            texto=(
                "Llevo doce anos acompanando a mujeres que ya intentaron de todo y estan "
                "cansadas de empezar de cero cada enero.\n\n"
                "Mi metodo no tiene nada de magico: medimos lo que se puede medir, ajustamos "
                "cada mes con esos numeros y no cambiamos el plan por corazonadas. Vas a "
                "comer comida de verdad y vas a entrenar fuerte.\n\n"
                "Lo que sigue son unas preguntas sobre tu salud. Contestalas con calma: de "
                "ahi sale tu primer plan."
            ),
            ficha=[
                {"rotulo": "Certificaciones", "valor": "ISAK nivel 1, NSCA-CPT, ISSN"},
                {"rotulo": "Anos de experiencia", "valor": "12"},
                {"rotulo": "Enfoque", "valor": "Recomposicion corporal en mujeres adultas"},
                {"rotulo": "Donde", "valor": "En linea, con seguimiento mensual"},
            ],
            activa=True,
        )
    )

    # Horario de consultas. Las dos coaches atienden en ratos distintos: si una alumna ve
    # los huecos de la otra, se nota a simple vista.
    tramos = (
        ((0, time(9), time(14)), (2, time(9), time(14)), (3, time(16), time(19)))
        if con_historial
        else ((5, time(8), time(12)),)
    )
    for dia, desde, hasta in tramos:
        sesion.add(
            HorarioDeAtencion(coach_id=coach.id, dia_semana=dia, desde=desde, hasta=hasta)
        )

    for orden, (texto_pregunta, tipo, opciones, obligatoria) in enumerate(PREGUNTAS_DEMO, start=1):
        sesion.add(
            PreguntaCuestionario(
                coach_id=coach.id,
                texto=texto_pregunta,
                tipo=tipo,
                opciones=list(opciones),
                obligatoria=obligatoria,
                orden=orden,
                activa=True,
            )
        )

    # Tres planes con precios distintos: es lo que hace visible que el cobro depende del
    # plan y no de un precio unico por coach.
    planes = []
    for codigo, nombre_plan, precio, intensidad in (
        ("ESENCIAL", "Esencial", Decimal("900.00"), "baja"),
        ("COMPLETO", "Completo", Decimal("1200.00"), "media"),
        ("PREMIUM", "Alto rendimiento", Decimal("1800.00"), "alta"),
    ):
        plan_comercial = Tarifa(
            coach_id=coach.id,
            codigo=codigo,
            nombre=nombre_plan,
            descripcion=f"Plan {nombre_plan.lower()} de acompanamiento mensual.",
            precio=precio,
            dias=30,
            intensidad=intensidad,
            activa=True,
        )
        sesion.add(plan_comercial)
        planes.append(plan_comercial)

    # Precios sueltos: lo que cobra aparte del plan. Sin esto el formulario de cobro no
    # tiene nada que ofrecer y hay que teclear el importe cada vez.
    for nombre_servicio, motivo_servicio, precio_servicio, descripcion_servicio in (
        ("Consulta de seguimiento", "cita", Decimal("450.00"), "45 minutos por video."),
        ("Consulta presencial", "cita", Decimal("650.00"), "Una hora en el estudio."),
        ("Inscripcion", "inscripcion", Decimal("500.00"), "Se cobra una sola vez, al entrar."),
        ("Banda de resistencia", "material", Decimal("280.00"), None),
    ):
        sesion.add(
            Servicio(
                coach_id=coach.id,
                nombre=nombre_servicio,
                descripcion=descripcion_servicio,
                motivo=motivo_servicio,
                precio=precio_servicio,
                activo=True,
            )
        )
    sesion.flush()

    for i, ficha in enumerate(cartera):
        usuario = Usuario(
            coach_id=coach.id,
            rol="alumna",
            email=ficha["correo"],
            hash_contrasena=hash_contrasena(CLAVE_DEMO),
            estado="activo",
        )
        sesion.add(usuario)
        sesion.flush()

        alumna = Alumna(
            coach_id=coach.id,
            usuario_id=usuario.id,
            nombre=ficha["nombre"],
            whatsapp="55 1234 5678",
            fecha_nacimiento=ficha["nac"],
            sexo="F",
            estatura_cm=ficha["estatura"],
            tarifa_id=planes[i % len(planes)].id,
            nivel_experiencia=ficha["nivel"],
            equipo="gimnasio_completo",
            estres=6,
            ocupacion="Trabajo de oficina",
            bascula_ref="Báscula de vidrio del baño",
            lugar_ref="Recámara, junto a la ventana",
            hora_ref="07:00",
            zona_horaria="America/Mexico_City",
            porcentaje_grasa_objetivo=Decimal("0.220"),
            cuestionario_completo=True,
            estado=ficha["estado"],
        )
        sesion.add(alumna)
        sesion.flush()

        for tipo, version, texto in CONSENTIMIENTOS:
            sesion.add(
                Consentimiento(
                    coach_id=coach.id,
                    alumna_id=alumna.id,
                    tipo=tipo,
                    version_texto=version,
                    texto_hash=_hash_texto(texto),
                    aceptado_en=_momento(date(2026, 5, 2), 14),
                    ip="187.190.0.1",
                    user_agent="Mozilla/5.0",
                )
            )

        sesion.add(
            HistorialClinico(
                coach_id=coach.id,
                alumna_id=alumna.id,
                lesiones="Esguince de tobillo derecho en 2023, ya recuperado."
                if i == 0
                else "Sin lesiones relevantes.",
                condiciones="Hipotiroidismo controlado con levotiroxina." if i == 0 else "Ninguna.",
                medicacion="Levotiroxina 50 mcg diaria, en ayunas." if i == 0 else "Ninguna.",
                restricciones="Intolerancia a la lactosa. No come mariscos."
                if i == 0
                else "Ninguna.",
                vigente_desde=_momento(date(2026, 5, 2)),
                registrado_por=usuario.id,
            )
        )

        # Relativo a hoy: con fechas fijas, la demo dejaba de funcionar el dia que el ciclo
        # vencia, y la alumna se quedaba sin poder ver su plan sin que nada estuviera roto.
        inicio_ciclo = date.today() - timedelta(days=15)
        ciclo = Ciclo(
            coach_id=coach.id,
            alumna_id=alumna.id,
            numero=ficha["ciclo"],
            inicia_en=inicio_ciclo,
            termina_en=inicio_ciclo + timedelta(days=30),
            estado="activo" if ficha["pago"] == "validado" else "pendiente_pago",
            precio=Decimal("1200.00"),
        )
        sesion.add(ciclo)
        sesion.flush()

        # El del mes pasado pagado y el proximo por venir. La tercera alumna lleva uno
        # vencido, que es lo que pausa su plan y hace visible la palanca de cobro.
        precio_plan = planes[i % len(planes)].precio
        sesion.add(
            CobroProgramado(
                coach_id=coach.id,
                alumna_id=alumna.id,
                fecha=inicio_ciclo,
                motivo="mensualidad",
                monto=precio_plan,
                estado="pagado",
                pagado_en=inicio_ciclo,
            )
        )
        sesion.add(
            CobroProgramado(
                coach_id=coach.id,
                alumna_id=alumna.id,
                fecha=inicio_ciclo + timedelta(days=30),
                motivo="mensualidad",
                monto=precio_plan,
                estado="pendiente",
            )
        )
        if i == 2:
            sesion.add(
                CobroProgramado(
                    coach_id=coach.id,
                    alumna_id=alumna.id,
                    fecha=date.today() - timedelta(days=6),
                    motivo="cita",
                    concepto="Consulta extra de ajuste",
                    monto=Decimal("350.00"),
                    estado="pendiente",
                )
            )

        # Todas llevan consulta: es lo que abre su ventana de chequeo. La primera cae hoy
        # para que la ventana este abierta al entrar a probar.
        consultas = [(0, "Consulta de este ciclo", "video")]
        if i < 3:
            consultas.append((16 + i, "Revision de medio ciclo", "presencial"))
        for dias, titulo, modalidad in consultas:
            arranque = datetime.combine(
                date.today() + timedelta(days=dias), time(hour=9 + i)
            ).replace(tzinfo=UTC)
            sesion.add(
                Cita(
                    coach_id=coach.id,
                    alumna_id=alumna.id,
                    titulo=titulo,
                    tipo="consulta",
                    modalidad=modalidad,
                    estado="confirmada" if dias < 7 else "agendada",
                    inicia_en=arranque,
                    termina_en=arranque + timedelta(minutes=45),
                )
            )

        sesion.add(
            Pago(
                coach_id=coach.id,
                alumna_id=alumna.id,
                ciclo_id=ciclo.id,
                monto=Decimal("1200.00"),
                metodo="Transferencia SPEI",
                ocr={"monto": 1200, "fecha": "2026-07-14", "referencia": "SPEI 4471982"},
                confianza=Decimal("0.940"),
                estado=ficha["pago"],
                validado_en=_momento(date(2026, 7, 14), 21)
                if ficha["pago"] == "validado"
                else None,
            )
        )

        sesion.add(
            ParametrosCiclo(
                coach_id=coach.id,
                alumna_id=alumna.id,
                ciclo_id=ciclo.id,
                nivel_actividad="activo",
                porcentaje_ajuste=Decimal("-0.200"),
                reparto_carbohidrato=Decimal("0.400"),
                reparto_proteina=Decimal("0.320"),
                reparto_grasa=Decimal("0.280"),
                base_proteina="masa_libre_de_grasa",
                dias_refeed=1,
                porcentaje_dia_refeed=Decimal("0.000"),
                relacion_ganancia="2:1",
            )
        )

        if con_historial and i == 0:
            _sembrar_historial_de_andrea(sesion, coach.id, alumna.id, ciclo.id, usuario.id)

    return coach.id


def _sembrar_historial_de_andrea(
    sesion: Any, coach_id: int, alumna_id: int, ciclo_id: int, usuario_id: int
) -> None:
    """Cuatro chequeos completos: es lo que hace que las gráficas y la comparativa tengan
    algo que enseñar."""
    for datos in CHEQUEOS_ANDREA:
        chequeo = Chequeo(
            coach_id=coach_id,
            alumna_id=alumna_id,
            ciclo_id=ciclo_id,
            fecha=datos["fecha"],
            estado=datos["estado"],
            ayuno_confirmado=True,
            enviado_en=_momento(datos["fecha"], 7),
            validado_en=_momento(datos["fecha"] + timedelta(days=1), 11)
            if datos["estado"] == "validado"
            else None,
            validado_por=usuario_id if datos["estado"] == "validado" else None,
            feedback=datos["feedback"],
            porcentaje_grasa=Decimal(datos["grasa"]),
            estimado_por=usuario_id,
            bascula_usada="Báscula de vidrio del baño",
            lugar_usado="Recámara, junto a la ventana",
            hora_usada="07:00",
        )
        sesion.add(chequeo)
        sesion.flush()

        sesion.add(
            Pesaje(
                coach_id=coach_id,
                alumna_id=alumna_id,
                chequeo_id=chequeo.id,
                fecha=datos["fecha"],
                peso_kg=Decimal(datos["peso"]),
                bascula_ref="Báscula de vidrio del baño",
            )
        )

        for tipo in TipoMedida:
            sesion.add(
                Medida(
                    coach_id=coach_id,
                    chequeo_id=chequeo.id,
                    tipo=tipo.value,
                    valor=Decimal(datos["medidas"][tipo.value]),
                )
            )

        for angulo in ("frontal", "perfil", "espalda"):
            llave = f"coach/{coach_id}/alumna/{alumna_id}/chequeo/{chequeo.id}/{angulo}.webp"
            _marcador_de_foto(llave, angulo, str(datos["fecha"]))
            sesion.add(
                Foto(
                    coach_id=coach_id,
                    chequeo_id=chequeo.id,
                    angulo=angulo,
                    storage_key=llave,
                    ancho=1200,
                    alto=1600,
                    bytes=380_000,
                    nitidez=Decimal("142.500"),
                    luminancia=Decimal("128.40"),
                    estado_auto="aprobada",
                    es_linea_base=datos["numero"] == 1,
                    tomada_en=_momento(datos["fecha"], 7),
                    subida_en=_momento(datos["fecha"], 7),
                )
            )

    # Planes del ciclo vigente.
    sesion.add(
        Plan(
            coach_id=coach_id,
            alumna_id=alumna_id,
            ciclo_id=ciclo_id,
            tipo="nutricion",
            estado="publicado",
            publicado_en=_momento(date(2026, 7, 2)),
            contenido=PLAN_NUTRICION,
            kcal_objetivo=1850,
            proteina_g=140,
            carbohidrato_g=175,
            grasa_g=58,
        )
    )
    sesion.add(
        Plan(
            coach_id=coach_id,
            alumna_id=alumna_id,
            ciclo_id=ciclo_id,
            tipo="entrenamiento",
            estado="publicado",
            publicado_en=_momento(date(2026, 7, 2)),
            contenido=PLAN_ENTRENAMIENTO,
        )
    )

    for autor, cuerpo, momento in MENSAJES:
        sesion.add(
            Mensaje(
                coach_id=coach_id,
                alumna_id=alumna_id,
                autor=autor,
                cuerpo=cuerpo,
                enviado_en=momento,
            )
        )


#: Base publica (coach_id nulo). En produccion el catalogo sale del dataset MIT; esto es
#: la muestra minima para probar el buscador del constructor.
ALIMENTOS_BASE = [
    ("Pechuga de pollo", 100, "g", 165, 31.0, 0.0, 3.6, "Proteína animal"),
    ("Huevo entero", 50, "g", 72, 6.3, 0.4, 4.8, "Proteína animal"),
    ("Claras de huevo", 100, "g", 52, 11.0, 0.7, 0.2, "Proteína animal"),
    ("Salmón", 100, "g", 208, 22.0, 0.0, 13.0, "Proteína animal"),
    ("Atún en agua", 100, "g", 116, 26.0, 0.0, 1.0, "Proteína animal"),
    ("Carne molida de res 90/10", 100, "g", 176, 20.0, 0.0, 10.0, "Proteína animal"),
    ("Avena en hojuelas", 100, "g", 380, 13.0, 67.0, 7.0, "Cereal"),
    ("Arroz integral cocido", 100, "g", 111, 2.6, 23.0, 0.9, "Cereal"),
    ("Tortilla de maíz", 30, "g", 65, 1.7, 13.0, 0.8, "Cereal"),
    ("Pan integral", 30, "g", 74, 3.6, 12.0, 1.1, "Cereal"),
    ("Camote", 100, "g", 86, 1.6, 20.0, 0.1, "Tubérculo"),
    ("Papa cocida", 100, "g", 87, 2.0, 20.0, 0.1, "Tubérculo"),
    ("Frijol cocido", 100, "g", 127, 8.7, 22.8, 0.5, "Leguminosa"),
    ("Lenteja cocida", 100, "g", 116, 9.0, 20.0, 0.4, "Leguminosa"),
    ("Plátano", 100, "g", 89, 1.1, 23.0, 0.3, "Fruta"),
    ("Manzana", 100, "g", 52, 0.3, 14.0, 0.2, "Fruta"),
    ("Arándanos", 100, "g", 57, 0.7, 14.0, 0.3, "Fruta"),
    ("Brócoli", 100, "g", 34, 2.8, 7.0, 0.4, "Verdura"),
    ("Espinaca", 100, "g", 23, 2.9, 3.6, 0.4, "Verdura"),
    ("Espárragos", 100, "g", 20, 2.2, 3.9, 0.1, "Verdura"),
    ("Aguacate", 100, "g", 160, 2.0, 9.0, 15.0, "Grasa"),
    ("Aceite de oliva", 10, "ml", 88, 0.0, 0.0, 10.0, "Grasa"),
    ("Almendras", 100, "g", 579, 21.0, 22.0, 50.0, "Grasa"),
    ("Nuez", 100, "g", 654, 15.0, 14.0, 65.0, "Grasa"),
    ("Yogur griego natural", 100, "g", 59, 10.0, 3.6, 0.4, "Lácteo"),
    ("Leche descremada", 100, "ml", 34, 3.4, 5.0, 0.1, "Lácteo"),
    ("Queso panela", 100, "g", 215, 18.0, 3.0, 15.0, "Lácteo"),
    ("Proteína en polvo (suero)", 30, "g", 120, 24.0, 3.0, 1.5, "Suplemento"),
]

EJERCICIOS_BASE = [
    ("Sentadilla trasera", "Cuádriceps", "Barra", "Rodilla dominante", "Molestia lumbar aguda"),
    ("Sentadilla goblet", "Cuádriceps", "Mancuernas", "Rodilla dominante", None),
    ("Prensa de pierna", "Cuádriceps", "Máquina", "Rodilla dominante", None),
    ("Zancada búlgara", "Cuádriceps", "Mancuernas", "Unilateral", "Inestabilidad de tobillo"),
    ("Peso muerto rumano", "Isquiotibiales", "Barra", "Cadera dominante", "Hernia discal"),
    ("Curl femoral acostada", "Isquiotibiales", "Máquina", "Rodilla dominante", None),
    ("Hip thrust", "Glúteo", "Barra", "Cadera dominante", None),
    ("Puente de glúteo", "Glúteo", "Peso corporal", "Cadera dominante", None),
    ("Elevación de talones sentada", "Pantorrilla", "Máquina", "Aislamiento", None),
    ("Press de banca con barra", "Pectoral", "Barra", "Empuje horizontal", "Dolor de hombro"),
    ("Press de banca con mancuernas", "Pectoral", "Mancuernas", "Empuje horizontal", None),
    ("Aperturas en polea", "Pectoral", "Polea", "Aislamiento", None),
    (
        "Press militar sentada",
        "Deltoide",
        "Mancuernas",
        "Empuje vertical",
        "Inestabilidad de hombro",
    ),
    ("Elevaciones laterales", "Deltoide", "Mancuernas", "Aislamiento", None),
    ("Face pull", "Deltoide posterior", "Polea", "Jalón horizontal", None),
    ("Jalón al pecho", "Dorsal", "Polea", "Jalón vertical", None),
    ("Dominadas asistidas", "Dorsal", "Máquina", "Jalón vertical", None),
    ("Remo con barra", "Dorsal", "Barra", "Jalón horizontal", "Molestia lumbar aguda"),
    ("Remo sentado en polea", "Dorsal", "Polea", "Jalón horizontal", None),
    ("Curl de bíceps con mancuerna", "Bíceps", "Mancuernas", "Aislamiento", None),
    ("Extensión de tríceps en polea", "Tríceps", "Polea", "Aislamiento", None),
    ("Fondos en máquina asistida", "Tríceps", "Máquina", "Empuje vertical", "Dolor de hombro"),
    ("Plancha frontal", "Core", "Peso corporal", "Antiextensión", None),
    ("Pallof press", "Core", "Polea", "Antirrotación", None),
]


def sembrar_catalogos(sesion: Any) -> None:
    """Base pública compartida. Va con `coach_id = NULL` para que la vean todas."""
    for nombre, porcion, unidad, kcal, p, c, g, grupo in ALIMENTOS_BASE:
        sesion.add(
            Alimento(
                coach_id=None,
                nombre=nombre,
                marca="Genérico",
                porcion=Decimal(str(porcion)),
                unidad=unidad,
                kcal=Decimal(str(kcal)),
                proteina=Decimal(str(p)),
                carbo=Decimal(str(c)),
                grasa=Decimal(str(g)),
                grupo_equivalente=grupo,
            )
        )

    for nombre, grupo, equipo, patron, contra in EJERCICIOS_BASE:
        sesion.add(
            Ejercicio(
                coach_id=None,
                nombre=nombre,
                grupo=grupo,
                equipo=equipo,
                patron=patron,
                contraindicaciones=contra,
            )
        )


def sembrar_plataforma(sesion: Any, coach_ids: list[int]) -> None:
    """El inquilino de la plataforma, su superadmin y suscripciones de ejemplo. El
    superadmin cuelga de un inquilino como cualquiera: lo que lo distingue es su rol."""
    plataforma = Coach(
        nombre="MyFittPlan",
        marca="MyFittPlan",
        slug="plataforma",
        email="hola@myfittplan.com",
        plan="plataforma",
        limite_alumnas=0,
        color_acento="#c9a227",
        estado="activa",
    )
    sesion.add(plataforma)
    sesion.flush()

    sesion.add(
        Usuario(
            coach_id=plataforma.id,
            rol="admin_plataforma",
            email="admin@myfittplan.com",
            hash_contrasena=hash_contrasena(CLAVE_DEMO),
            estado="activo",
        )
    )

    hoy = date.today()
    # Una al corriente y una en cortesia: el panel de facturacion no se entiende con una sola
    # fila, y los dos estados se pintan distinto.
    sesion.add(
        SuscripcionCoach(
            coach_id=coach_ids[0],
            plan="profesional",
            precio=Decimal("1500.00"),
            periodicidad="mensual",
            estado="al_corriente",
            inicia_en=hoy - timedelta(days=120),
            vigente_hasta=hoy + timedelta(days=20),
        )
    )
    sesion.add(
        SuscripcionCoach(
            coach_id=coach_ids[1],
            plan="basico",
            precio=Decimal(0),
            periodicidad="mensual",
            estado="cortesia",
            inicia_en=hoy - timedelta(days=30),
            nota="Primeros tres meses sin costo.",
        )
    )

    for i in range(4):
        inicio = (hoy.replace(day=1) - timedelta(days=30 * i)).replace(day=1)
        sesion.add(
            CobroCoach(
                coach_id=coach_ids[0],
                monto=Decimal("1500.00"),
                fecha=inicio,
                metodo="transferencia",
                periodo_inicia=inicio,
                periodo_termina=inicio + timedelta(days=30),
            )
        )


def sembrar(reiniciar: bool = False) -> None:
    # Estas cuentas tienen contrasena conocida y `--reiniciar` borra todas las tablas:
    # contra la base real seria abrir una puerta trasera y perder los datos a la vez.
    from app.config import ajustes

    if ajustes().es_produccion:
        raise SystemExit("La semilla no corre en produccion: crea cuentas con contrasena conocida.")

    with sesion_sin_alcance("siembra de datos de desarrollo, cruza inquilinos") as s:
        existentes = s.scalars(select(Coach)).all()
        if existentes and not reiniciar:
            print(f"Ya hay {len(existentes)} coaches. Usa --reiniciar para volver a sembrar.")
            return
        if existentes:
            from app.datos.base import Base

            # Sobre `s.connection()`: el SELECT de arriba dejo una transaccion abierta, y
            # un DROP desde otra conexion del pool esperaria su metadata lock para siempre.
            conexion = s.connection()
            Base.metadata.drop_all(bind=conexion)
            Base.metadata.create_all(bind=conexion)
            s.commit()
            print("Base reiniciada.")

        sembrar_catalogos(s)

        principal = sembrar_coach(
            s,
            nombre="Mariana Cervantes",
            slug="leanmuscle",
            marca="LeanMuscle",
            email="mariana@leanmuscle.mx",
            color="#c9a227",
            cartera=CARTERA,
            con_historial=True,
        )
        segunda = sembrar_coach(
            s,
            nombre="Regina Solís",
            slug="reginafit",
            marca="ReginaFit",
            email="regina@reginafit.mx",
            color="#2f5d8a",
            cartera=CARTERA_SEGUNDA,
            con_historial=False,
        )

        sembrar_plataforma(s, [principal, segunda])

    print(
        "Sembrado.\n"
        f"  Coach 1 (id {principal}) · LeanMuscle · mariana@leanmuscle.mx · {len(CARTERA)} alumnas\n"
        f"  Coach 2 (id {segunda}) · ReginaFit · regina@reginafit.mx · {len(CARTERA_SEGUNDA)} alumnas\n"
        f"  Contraseña de todas las cuentas: {CLAVE_DEMO}\n"
        "\nLa segunda coach existe para que una fuga entre inquilinos se vea. No la borres."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Siembra datos de desarrollo.")
    parser.add_argument("--reiniciar", action="store_true", help="borra todo y vuelve a sembrar")
    sembrar(parser.parse_args().reiniciar)


if __name__ == "__main__":
    main()
