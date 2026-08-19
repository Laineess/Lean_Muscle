"""Cada acción que dispara un botón de la interfaz, con datos como los que teclearía alguien.

No prueba entradas absurdas: eso ya está barrido. Prueba que el camino feliz de cada botón
termina en éxito, que es lo que se ve al usar la aplicación.
"""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
import uuid
from http.cookiejar import CookieJar
from typing import Any

BASE = "http://127.0.0.1:8000"

verde: list[str] = []
rojo: list[tuple[str, int, str]] = []


def cliente(correo: str):
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))
    pide(op, "/api/auth/login", "POST", {"correo": correo, "contrasena": "Demo1234!"})
    return op


def pide(op, ruta: str, metodo: str = "GET", cuerpo: Any = None) -> tuple[int, Any]:
    datos = json.dumps(cuerpo).encode() if cuerpo is not None else None
    pet = urllib.request.Request(BASE + ruta, data=datos, method=metodo)
    if datos:
        pet.add_header("Content-Type", "application/json")
    try:
        with op.open(pet) as r:
            crudo = r.read()
            try:
                return r.status, json.loads(crudo) if crudo else None
            except ValueError:
                return r.status, crudo
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]


def sube(op, ruta: str, datos: bytes, nombre: str, metodo: str, campos: dict | None = None):
    borde = uuid.uuid4().hex
    partes = b""
    for clave, valor in (campos or {}).items():
        partes += (
            f"--{borde}\r\nContent-Disposition: form-data; name=\"{clave}\"\r\n\r\n{valor}\r\n"
        ).encode()
    partes += (
        f"--{borde}\r\n"
        f'Content-Disposition: form-data; name="archivo"; filename="{nombre}"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode() + datos + f"\r\n--{borde}--\r\n".encode()
    pet = urllib.request.Request(BASE + ruta, data=partes, method=metodo)
    pet.add_header("Content-Type", f"multipart/form-data; boundary={borde}")
    try:
        with op.open(pet) as r:
            return r.status, r.read()[:80]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:200]


def boton(rotulo: str, resultado: tuple[int, Any], esperados=(200, 201, 204)) -> Any:
    estado, cuerpo = resultado
    if estado in esperados:
        verde.append(rotulo)
    else:
        rojo.append((rotulo, estado, str(cuerpo)[:170]))
    return cuerpo


def jpg(ancho: int = 700, alto: int = 900) -> bytes:
    from PIL import Image

    s = io.BytesIO()
    Image.new("RGB", (ancho, alto), (170, 150, 140)).save(s, "JPEG")
    return s.getvalue()


def main() -> None:
    coach = cliente("mariana@leanmuscle.mx")
    admin = cliente("admin@myfittplan.com")

    cartera = boton("Cartera · cargar alumnas", pide(coach, "/api/coach/alumnas"))
    una = cartera[0]["ulid"]

    # ---- Menú del avatar ----
    boton("Panel", pide(coach, "/api/coach/panel"))
    boton("Apariencia · leer marca", pide(coach, "/api/coach/marca"))
    marca = pide(coach, "/api/coach/marca")[1]
    boton(
        "Apariencia · Guardar marca",
        pide(coach, "/api/coach/marca", "PUT",
             {"nombre": marca["nombre"], "marca": marca["marca"], "colorAcento": marca["colorAcento"]}),
    )
    boton("Apariencia · subir logo", sube(coach, "/api/coach/logo", jpg(400, 400), "logo.jpg", "PUT"))

    pres = boton("Presentación · leer", pide(coach, "/api/coach/presentacion"))
    boton(
        "Presentación · Guardar",
        pide(coach, "/api/coach/presentacion", "PUT",
             {"titulo": pres["titulo"] or "Soy Mariana", "texto": pres["texto"] or "Llevo 8 años.",
              "ficha": pres["ficha"], "activa": True}),
    )
    boton("Presentación · subir foto",
          sube(coach, "/api/coach/presentacion/foto", jpg(500, 500), "yo.jpg", "PUT"))

    # ---- Cuestionario ----
    preguntas = boton("Cuestionario · leer", pide(coach, "/api/coach/preguntas"))
    nueva = boton(
        "Cuestionario · Nueva pregunta",
        pide(coach, "/api/coach/preguntas", "POST",
             {"texto": "¿Cuántas horas duermes?", "ayuda": None, "tipo": "numero",
              "opciones": [], "obligatoria": False, "orden": len(preguntas) + 1, "activa": True}),
    )
    if isinstance(nueva, dict):
        boton("Cuestionario · Editar pregunta",
              pide(coach, f"/api/coach/preguntas/{nueva['ulid']}", "PUT",
                   {"texto": "¿Cuántas horas duermes entre semana?", "ayuda": None,
                    "tipo": "numero", "opciones": [], "obligatoria": False, "orden": 99,
                    "activa": True}))
        boton("Cuestionario · Borrar pregunta",
              pide(coach, f"/api/coach/preguntas/{nueva['ulid']}", "DELETE"))

    # ---- Planes y precios ----
    plan = boton("Planes · Nuevo plan",
                 pide(coach, "/api/coach/tarifas", "POST",
                      {"codigo": f"PB-{uuid.uuid4().hex[:8].upper()}", "nombre": "Plan de prueba", "descripcion": None,
                       "precio": 1200, "dias": 30, "intensidad": "media", "activa": True}))
    if isinstance(plan, dict):
        boton("Planes · Editar plan",
              pide(coach, f"/api/coach/tarifas/{plan['ulid']}", "PUT",
                   {"codigo": plan["codigo"], "nombre": "Plan de prueba II", "descripcion": None,
                    "precio": 1300, "dias": 30, "intensidad": "alta", "activa": False}))

    servicio = boton("Precios · Nuevo precio",
                     pide(coach, "/api/coach/servicios", "POST",
                          {"nombre": "Consulta suelta", "descripcion": None, "motivo": "cita",
                           "precio": 450, "activo": True}))
    if isinstance(servicio, dict):
        boton("Precios · Editar", pide(coach, f"/api/coach/servicios/{servicio['ulid']}", "PUT",
                                       {"nombre": "Consulta", "descripcion": None, "motivo": "cita",
                                        "precio": 500, "activo": True}))
        boton("Precios · Borrar", pide(coach, f"/api/coach/servicios/{servicio['ulid']}", "DELETE"))

    # ---- Avisos ----
    boton("Avisos · Enviar",
          pide(coach, "/api/coach/anuncios", "POST", {"titulo": "Lunes", "cuerpo": "Con todo."}))
    boton("Avisos · historial", pide(coach, "/api/coach/anuncios"))

    # ---- Alumna: alta, edición, clave ----
    alta = boton("Alumnas · Dar de alta",
                 pide(coach, "/api/coach/alumnas", "POST",
                      {"nombre": "Prueba De Botones", "correo": f"prueba.botones.{uuid.uuid4().hex[:8]}@ejemplo.mx",
                       "whatsapp": "5512345678", "fechaNacimiento": "1992-03-11",
                       "estaturaCm": 165, "tarifaUlid": None, "nivelExperiencia": "principiante"}))
    # Nunca cae en una alumna de la semilla: restablecerle la clave le tira la sesión.
    nueva_ulid = alta["alumnaUlid"] if isinstance(alta, dict) else None
    perfil = (
        boton("Alumnas · abrir editar", pide(coach, f"/api/coach/alumnas/{nueva_ulid}"))
        if nueva_ulid
        else None
    )
    if isinstance(perfil, dict):
        boton("Alumnas · Guardar edición",
              pide(coach, f"/api/coach/alumnas/{nueva_ulid}", "PUT",
                   {"nombre": perfil["nombre"], "whatsapp": perfil["whatsapp"],
                    "estaturaCm": perfil["estaturaCm"], "tarifaUlid": perfil["tarifaUlid"],
                    "nivelExperiencia": perfil["nivelExperiencia"], "equipo": perfil["equipo"],
                    "ocupacion": perfil["ocupacion"], "basculaRef": perfil["basculaRef"],
                    "lugarRef": perfil["lugarRef"], "horaRef": perfil["horaRef"],
                    "porcentajeGrasaObjetivo": 0.24, "estado": "activa"}))
    if nueva_ulid:
        boton("Alumnas · Recuperar acceso",
              pide(coach, f"/api/coach/alumnas/{nueva_ulid}/clave-temporal", "POST",
                   {"motivoVerificacion": "Videollamada"}))

    # ---- Agenda ----
    cita = boton("Agenda · Agendar",
                 pide(coach, "/api/coach/agenda", "POST",
                      {"titulo": "Consulta de prueba", "tipo": "consulta", "modalidad": "video",
                       "alumnaUlid": una, "iniciaEn": "2026-09-01T16:00:00Z",
                       "terminaEn": "2026-09-01T17:00:00Z", "enlace": None, "lugar": None,
                       "notas": None}))
    if isinstance(cita, dict):
        boton("Agenda · Editar cita",
              pide(coach, f"/api/coach/agenda/{cita['ulid']}", "PUT",
                   {"titulo": "Consulta movida", "tipo": "consulta", "modalidad": "video",
                    "alumnaUlid": una, "iniciaEn": "2026-09-02T16:00:00Z",
                    "terminaEn": "2026-09-02T17:00:00Z", "enlace": None, "lugar": None,
                    "notas": None}))
        boton("Agenda · Cancelar cita",
              pide(coach, f"/api/coach/agenda/{cita['ulid']}/cancelar", "POST",
                   {"motivo": "Se empalmó una urgencia."}))
        boton("Agenda · Eliminar cita",
              pide(coach, f"/api/coach/agenda/{cita['ulid']}", "DELETE"))
    boton("Agenda · cargar semana", pide(coach, "/api/coach/agenda?desde=2026-09-01&dias=7"))

    # ---- Cobros y finanzas ----
    cobro = boton("Cobros · Programar",
                  pide(coach, f"/api/coach/alumnas/{una}/cobros", "POST",
                       {"fecha": "2026-09-05", "motivo": "mensualidad",
                        "concepto": "Mensualidad de septiembre", "monto": 1200, "nota": None}))
    boton("Finanzas · panel", pide(coach, "/api/coach/finanzas"))
    mov = boton("Finanzas · Nuevo movimiento",
                pide(coach, "/api/coach/finanzas/movimientos", "POST",
                     {"tipo": "gasto", "categoria": "plataforma", "monto": 890,
                      "fecha": "2026-08-18", "concepto": "Suscripción", "alumnaUlid": None,
                      "nota": None, "cobroUlid": None}))
    if isinstance(mov, dict):
        boton("Finanzas · Editar movimiento",
              pide(coach, f"/api/coach/finanzas/movimientos/{mov['ulid']}", "PUT",
                   {"tipo": "gasto", "categoria": "plataforma", "monto": 900,
                    "fecha": "2026-08-18", "concepto": "Suscripción de agosto",
                    "alumnaUlid": None, "nota": None, "cobroUlid": None}))
        boton("Finanzas · Eliminar movimiento",
              pide(coach, f"/api/coach/finanzas/movimientos/{mov['ulid']}", "DELETE"))
    boton("Finanzas · buscador de cobro", pide(coach, "/api/coach/cobrar?q=an"))

    # ---- Biblioteca ----
    boton("Constructor · buscar alimento", pide(coach, "/api/coach/alimentos?q=pollo"))
    boton("Constructor · buscar ejercicio", pide(coach, "/api/coach/ejercicios?q=sentadilla"))
    boton("Biblioteca · Crear alimento",
          pide(coach, "/api/coach/alimentos", "POST",
               {"nombre": "Pechuga de prueba", "marca": None, "porcion": 100, "unidad": "g",
                "kcal": 165, "proteina": 31, "carbo": 0, "grasa": 3.6, "grupo": None}))

    # ---- Expediente y plan ----
    boton("Expediente · validación", pide(coach, f"/api/coach/alumnas/{una}/validacion"))
    boton("Expediente · historial", pide(coach, f"/api/coach/alumnas/{una}/historial"))
    boton("Constructor · abrir", pide(coach, f"/api/coach/planes/{una}"))
    boton("Calculadora · hoja", pide(coach, f"/api/coach/hoja/{una}"))
    boton("Constructor · Guardar borrador",
          pide(coach, f"/api/coach/planes/{una}", "PUT",
               {"tipo": "nutricion", "contenido": {"notas": "", "tiempos": []},
                "kcalObjetivo": 1850, "proteinaG": 140, "carbohidratoG": 180, "grasaG": 60,
                "publicar": False, "frecuenciaFotos": "semanal",
                "parametros": {"actividad": "activo", "porcentajeAjuste": -0.28,
                               "reparto": {"carbohidrato": 0.4, "proteina": 0.35, "grasa": 0.25},
                               "baseProteina": "masa_libre_de_grasa", "diasRefeed": 1,
                               "porcentajeDiaRefeed": 0, "relacionGanancia": "2:1"}}))
    boton("PDF · plan de nutrición", pide(coach, f"/api/documentos/plan-nutricion?alumna_ulid={una}"))
    boton("PDF · rutina", pide(coach, f"/api/documentos/rutina?alumna_ulid={una}"))
    boton("PDF · evolución", pide(coach, f"/api/documentos/evolucion?alumna_ulid={una}"))

    # ---- Comprobantes ----
    boton("Comprobantes · bandeja", pide(coach, "/api/coach/comprobantes"))

    # ---- Mensajes ----
    boton("Conversación · Enviar",
          pide(coach, f"/api/coach/mensajes/{una}", "POST", {"cuerpo": "Vamos bien."}))
    boton("Conversación · leer", pide(coach, f"/api/coach/mensajes/{una}"))

    # ---- Alumna ----
    alumna = cliente("andrea.saenz@ejemplo.mx")
    boton("Alumna · inicio", pide(alumna, "/api/mi/inicio"))
    boton("Alumna · mi plan", pide(alumna, "/api/mi/plan"))
    boton("Alumna · cuestionario", pide(alumna, "/api/mi/cuestionario"))
    boton("Alumna · presentación", pide(alumna, "/api/mi/presentacion"))
    boton("Alumna · avisos", pide(alumna, "/api/mi/avisos"))
    boton("Alumna · Escribir a su coach",
          pide(alumna, "/api/mi/mensajes", "POST", {"cuerpo": "Gracias."}))
    boton("Alumna · activar notificaciones",
          pide(alumna, "/api/mi/push", "POST",
               {"endpoint": "https://fcm.googleapis.com/prueba-botones", "p256dh": "k", "auth": "a"}))
    boton("Alumna · desactivar notificaciones", pide(alumna, "/api/mi/push", "DELETE"))
    boton("Alumna · Descargar PDF", pide(alumna, "/api/documentos/evolucion"))

    cobros = boton("Alumna · sus cobros", pide(alumna, "/api/mi/cobros"))
    pendiente = next((c for c in cobros if c["estado"] != "pagado"), None) if isinstance(cobros, list) else None
    if pendiente:
        boton("Alumna · Subir comprobante",
              sube(alumna, f"/api/mi/cobros/{pendiente['ulid']}/comprobante", jpg(600, 800),
                   "comprobante.jpg", "POST"))
        boton("Coach · ver comprobante",
              pide(coach, f"/api/coach/cobros/{pendiente['ulid']}/comprobante"))
        boton("Coach · Rechazar comprobante",
              pide(coach, f"/api/coach/cobros/{pendiente['ulid']}/rechazar", "POST",
                   {"motivo": "No se ve el monto."}))

    # ---- ARCO, de punta a punta ----
    sol = boton("Alumna · Ejercer derecho ARCO",
                pide(alumna, "/api/mi/arco", "POST",
                     {"derecho": "A", "detalle": "Quiero ver todo lo que tienen de mí."}))
    boton("Alumna · sus solicitudes", pide(alumna, "/api/mi/arco"))
    lista = boton("Coach · bandeja ARCO", pide(coach, "/api/coach/arco"))
    if isinstance(sol, dict):
        boton("Coach · Contestar ARCO",
              pide(coach, f"/api/coach/arco/{sol['ulid']}/responder", "POST",
                   {"respuesta": "Te mando tu expediente en PDF."}))
        boton("Coach · Marcar resuelta",
              pide(coach, f"/api/coach/arco/{sol['ulid']}/resolver", "POST"))
    boton("Alumna · Pedir baja (cancelación)",
          pide(alumna, "/api/mi/arco", "POST", {"derecho": "C", "detalle": "Baja definitiva."}))

    # ---- Plataforma ----
    coaches = boton("Plataforma · coaches", pide(admin, "/api/plataforma/coaches"))
    boton("Plataforma · facturación", pide(admin, "/api/plataforma/facturacion"))
    boton("Plataforma · salud", pide(admin, "/api/plataforma/salud"))
    boton("Plataforma · auditoría", pide(admin, "/api/plataforma/auditoria"))
    if isinstance(coaches, list) and coaches:
        c0 = coaches[0]
        boton("Plataforma · Guardar coach",
              pide(admin, f"/api/plataforma/coaches/{c0['ulid']}", "PUT",
                   {"nombre": c0["nombre"], "marca": c0["marca"], "plan": c0["plan"],
                    "limiteAlumnas": c0["limiteAlumnas"], "estado": c0["estado"],
                    "precioCiclo": c0["precioCiclo"]}))
        boton("Plataforma · Guardar suscripción",
              pide(admin, f"/api/plataforma/coaches/{c0['ulid']}/suscripcion", "PUT",
                   {"plan": c0["plan"], "precio": 890, "periodicidad": "mensual",
                    "estado": "al_corriente", "vigenteHasta": "2026-12-31", "nota": None}))
        boton("Plataforma · Registrar cobro",
              pide(admin, f"/api/plataforma/coaches/{c0['ulid']}/cobros", "POST",
                   {"monto": 890, "fecha": "2026-08-18", "metodo": "transferencia",
                    "periodoInicia": "2026-08-01", "periodoTermina": "2026-08-31", "nota": None}))

    # ---- Legales y sesión ----
    boton("Legal · aviso de privacidad", pide(alumna, "/api/legales/privacidad"))
    boton("Cambiar contraseña (rechaza la débil)",
          pide(alumna, "/api/auth/contrasena", "POST", {"actual": "Demo1234!", "nueva": "corta"}),
          esperados=(422, 400))
    boton("Cerrar sesión", pide(alumna, "/api/auth/logout", "POST"))

    print(f"{len(verde)} botones sin error · {len(rojo)} con error\n")
    for rotulo, estado, texto in rojo:
        print(f"  {estado}  {rotulo}")
        print(f"       {texto}")


if __name__ == "__main__":
    main()
