"""Esquema completo de MyProgressPlan.

Revision: 0001_esquema
Anterior: ninguna
Fecha: 2026-08-26

Sustituye a las dieciseis migraciones anteriores. Se juntaron en una porque la cadena no se
podia replicar: la primera llamaba a `Base.metadata.create_all`, que refleja los modelos de
**hoy** y no el esquema de aquel dia, asi que creaba de golpe tablas y columnas que las
migraciones siguientes volvian a crear. Sobre una base vacia reventaba en la sexta.

Este archivo no mira los modelos: las tablas van escritas una a una, congeladas. Es lo que
permite que `alembic upgrade head` de el mismo resultado hoy y dentro de un anio. Nunca
vuelva a aparecer un `create_all` aqui dentro.

Se pudo juntar sin riesgo porque no hay ninguna base desplegada a medio camino: la de
desarrollo se sella en esta revision, y el VPS parte de cero.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# El tipo de marca de tiempo del proyecto. Se importa el modulo entero porque las columnas
# de abajo lo nombran con su ruta completa, tal como lo dejo el autogenerador.
import app.datos.base

revision: str = "0001_esquema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "alimento",
        sa.Column("coach_id", sa.BigInteger(), nullable=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("marca", sa.String(length=120), nullable=True),
        sa.Column("porcion", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("unidad", sa.String(length=10), nullable=False),
        sa.Column("kcal", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("proteina", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("carbo", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("grasa", sa.Numeric(precision=6, scale=2), nullable=False),
        sa.Column("fibra", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("sodio", sa.Numeric(precision=8, scale=2), nullable=True),
        sa.Column("grupo_equivalente", sa.String(length=60), nullable=True),
        sa.Column("alergenos", mysql.JSON(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alimento")),
        sa.UniqueConstraint("ulid", name=op.f("uq_alimento_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_alimento_coach_nombre", "alimento", ["coach_id", "nombre"], unique=False)
    op.create_table(
        "bitacora",
        sa.Column("actor_tipo", sa.String(length=20), nullable=False),
        sa.Column("actor_id", sa.BigInteger(), nullable=True),
        sa.Column("accion", sa.String(length=60), nullable=False),
        sa.Column("entidad", sa.String(length=60), nullable=False),
        sa.Column("entidad_id", sa.BigInteger(), nullable=True),
        sa.Column("detalle", mysql.JSON(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bitacora")),
        sa.UniqueConstraint("ulid", name=op.f("uq_bitacora_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_bitacora_coach_creado", "bitacora", ["coach_id", "creado_en"], unique=False)
    op.create_index(op.f("ix_bitacora_coach_id"), "bitacora", ["coach_id"], unique=False)
    op.create_table(
        "coach",
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("marca", sa.String(length=120), nullable=True),
        sa.Column("slug", sa.String(length=60), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("limite_alumnas", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("logo_key", sa.String(length=255), nullable=True),
        sa.Column("color_acento", sa.String(length=9), nullable=False),
        sa.Column("color_secundario", sa.String(length=9), nullable=False),
        sa.Column("precio_ciclo", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("dia_chequeo", mysql.TINYINT(), nullable=False),
        sa.Column("duracion_consulta_min", sa.Integer(), nullable=False),
        sa.Column("margen_consulta_min", sa.Integer(), nullable=False),
        sa.Column("antelacion_horas", sa.Integer(), nullable=False),
        sa.Column("horizonte_semanas", sa.Integer(), nullable=False),
        sa.Column("zona_horaria", sa.String(length=60), nullable=False),
        sa.Column("registro_abierto", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_coach")),
        sa.UniqueConstraint("email", name=op.f("uq_coach_email")),
        sa.UniqueConstraint("slug", name=op.f("uq_coach_slug")),
        sa.UniqueConstraint("ulid", name=op.f("uq_coach_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "ejercicio",
        sa.Column("coach_id", sa.BigInteger(), nullable=True),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("grupo", sa.String(length=60), nullable=True),
        sa.Column("equipo", sa.String(length=60), nullable=True),
        sa.Column("patron", sa.String(length=60), nullable=True),
        sa.Column("video_key", sa.String(length=255), nullable=True),
        sa.Column("instrucciones", sa.Text(), nullable=True),
        sa.Column("contraindicaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ejercicio")),
        sa.UniqueConstraint("ulid", name=op.f("uq_ejercicio_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_ejercicio_coach_nombre", "ejercicio", ["coach_id", "nombre"], unique=False)
    op.create_table(
        "horario_atencion",
        sa.Column("dia_semana", mysql.TINYINT(), nullable=False),
        sa.Column("desde", sa.Time(), nullable=False),
        sa.Column("hasta", sa.Time(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dia_semana between 0 and 6", name=op.f("ck_horario_atencion_dia_semana_valido")
        ),
        sa.CheckConstraint("hasta > desde", name=op.f("ck_horario_atencion_tramo_valido")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horario_atencion")),
        sa.UniqueConstraint("ulid", name=op.f("uq_horario_atencion_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_horario_atencion_coach_id"), "horario_atencion", ["coach_id"], unique=False
    )
    op.create_index(
        "ix_horario_coach_dia", "horario_atencion", ["coach_id", "dia_semana"], unique=False
    )
    op.create_table(
        "intento_de_acceso",
        sa.Column("correo", sa.String(length=180), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("exitoso", sa.Boolean(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_intento_de_acceso")),
        sa.UniqueConstraint("ulid", name=op.f("uq_intento_de_acceso_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_intento_correo_cuando", "intento_de_acceso", ["correo", "creado_en"], unique=False
    )
    op.create_index("ix_intento_ip_cuando", "intento_de_acceso", ["ip", "creado_en"], unique=False)
    op.create_table(
        "plantilla",
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=160), nullable=False),
        sa.Column("dias", mysql.JSON(), nullable=False),
        sa.Column("usos", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plantilla")),
        sa.UniqueConstraint("coach_id", "codigo", name="uq_plantilla_codigo"),
        sa.UniqueConstraint("ulid", name=op.f("uq_plantilla_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_plantilla_coach_id"), "plantilla", ["coach_id"], unique=False)
    op.create_table(
        "pregunta_cuestionario",
        sa.Column("texto", sa.String(length=300), nullable=False),
        sa.Column("ayuda", sa.String(length=300), nullable=True),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("opciones", mysql.JSON(), nullable=False),
        sa.Column("obligatoria", sa.Boolean(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo in ('texto','texto_largo','numero','opcion','si_no')",
            name=op.f("ck_pregunta_cuestionario_tipo_pregunta_valido"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pregunta_cuestionario")),
        sa.UniqueConstraint("ulid", name=op.f("uq_pregunta_cuestionario_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_pregunta_coach_orden", "pregunta_cuestionario", ["coach_id", "orden"], unique=False
    )
    op.create_index(
        op.f("ix_pregunta_cuestionario_coach_id"),
        "pregunta_cuestionario",
        ["coach_id"],
        unique=False,
    )
    op.create_table(
        "presentacion_coach",
        sa.Column("foto_key", sa.String(length=255), nullable=True),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("texto", sa.Text(), nullable=False),
        sa.Column("ficha", mysql.JSON(), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_presentacion_coach")),
        sa.UniqueConstraint("coach_id", name="uq_presentacion_coach"),
        sa.UniqueConstraint("ulid", name=op.f("uq_presentacion_coach_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_presentacion_coach_coach_id"), "presentacion_coach", ["coach_id"], unique=False
    )
    op.create_table(
        "servicio",
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("motivo", sa.String(length=20), nullable=False),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "motivo in ('inscripcion','mensualidad','cita','material','otro')",
            name=op.f("ck_servicio_motivo_servicio_valido"),
        ),
        sa.CheckConstraint("precio > 0", name=op.f("ck_servicio_precio_servicio_positivo")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_servicio")),
        sa.UniqueConstraint("ulid", name=op.f("uq_servicio_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_servicio_coach_id"), "servicio", ["coach_id"], unique=False)
    op.create_index("ix_servicio_coach_motivo", "servicio", ["coach_id", "motivo"], unique=False)
    op.create_table(
        "tarifa",
        sa.Column("codigo", sa.String(length=30), nullable=False),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("dias", sa.Integer(), nullable=False),
        sa.Column("intensidad", sa.String(length=10), nullable=False),
        sa.Column("activa", sa.Boolean(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "intensidad in ('baja','media','alta')", name=op.f("ck_tarifa_intensidad_valida")
        ),
        sa.CheckConstraint("dias between 1 and 365", name=op.f("ck_tarifa_dias_rango")),
        sa.CheckConstraint("precio > 0", name=op.f("ck_tarifa_precio_positivo")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tarifa")),
        sa.UniqueConstraint("coach_id", "codigo", name="uq_tarifa_codigo"),
        sa.UniqueConstraint("ulid", name=op.f("uq_tarifa_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_tarifa_coach_id"), "tarifa", ["coach_id"], unique=False)
    op.create_table(
        "trabajo",
        sa.Column("tipo", sa.String(length=60), nullable=False),
        sa.Column("payload", mysql.JSON(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("correr_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("max_intentos", sa.Integer(), nullable=False),
        sa.Column("ultimo_error", sa.Text(), nullable=True),
        sa.Column("terminado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_trabajo")),
        sa.UniqueConstraint("ulid", name=op.f("uq_trabajo_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_trabajo_estado_correr", "trabajo", ["estado", "correr_en"], unique=False)
    op.create_table(
        "usuario",
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=180), nullable=False),
        sa.Column("hash_contrasena", sa.String(length=255), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("ultimo_acceso_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("debe_cambiar_contrasena", sa.Boolean(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "rol in ('coach','alumna','admin_plataforma')", name=op.f("ck_usuario_rol_valido")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_usuario")),
        sa.UniqueConstraint("email", name=op.f("uq_usuario_email")),
        sa.UniqueConstraint("ulid", name=op.f("uq_usuario_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_usuario_coach_id"), "usuario", ["coach_id"], unique=False)
    op.create_table(
        "vulneracion",
        sa.Column("detectada_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("causa", sa.Text(), nullable=True),
        sa.Column("alcance", sa.Text(), nullable=True),
        sa.Column("notificado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("acciones_correctivas", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_vulneracion")),
        sa.UniqueConstraint("ulid", name=op.f("uq_vulneracion_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "alumna",
        sa.Column("usuario_id", sa.BigInteger(), nullable=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("whatsapp", sa.String(length=30), nullable=True),
        sa.Column("fecha_nacimiento", sa.Date(), nullable=False),
        sa.Column("sexo", sa.String(length=1), nullable=True),
        sa.Column("estatura_cm", sa.Integer(), nullable=True),
        sa.Column("tarifa_id", sa.BigInteger(), nullable=True),
        sa.Column("nivel_experiencia", sa.String(length=20), nullable=True),
        sa.Column("equipo", sa.String(length=30), nullable=True),
        sa.Column("estres", mysql.TINYINT(), nullable=True),
        sa.Column("ocupacion", sa.String(length=180), nullable=True),
        sa.Column("zona_horaria", sa.String(length=60), nullable=False),
        sa.Column("porcentaje_grasa_objetivo", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("bascula_ref", sa.String(length=120), nullable=True),
        sa.Column("lugar_ref", sa.String(length=120), nullable=True),
        sa.Column("hora_ref", sa.String(length=5), nullable=True),
        sa.Column("cuestionario_completo", sa.Boolean(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("baja_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estatura_cm is null or estatura_cm between 100 and 250",
            name=op.f("ck_alumna_estatura_rango"),
        ),
        sa.CheckConstraint(
            "estres is null or estres between 1 and 10", name=op.f("ck_alumna_estres_rango")
        ),
        sa.ForeignKeyConstraint(["tarifa_id"], ["tarifa.id"], name=op.f("fk_alumna_tarifa_id")),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name=op.f("fk_alumna_usuario_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_alumna")),
        sa.UniqueConstraint("ulid", name=op.f("uq_alumna_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_alumna_coach_id"), "alumna", ["coach_id"], unique=False)
    op.create_table(
        "anuncio",
        sa.Column("titulo", sa.String(length=80), nullable=False),
        sa.Column("cuerpo", sa.String(length=300), nullable=False),
        sa.Column("enviado_por", sa.BigInteger(), nullable=False),
        sa.Column("enviado_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["enviado_por"], ["usuario.id"], name=op.f("fk_anuncio_enviado_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_anuncio")),
        sa.UniqueConstraint("ulid", name=op.f("uq_anuncio_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_anuncio_coach_enviado", "anuncio", ["coach_id", "enviado_en"], unique=False)
    op.create_index(op.f("ix_anuncio_coach_id"), "anuncio", ["coach_id"], unique=False)
    op.create_table(
        "aviso_enviado",
        sa.Column("destinatario_id", sa.BigInteger(), nullable=True),
        sa.Column("destinatario_correo", sa.String(length=180), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("llave", sa.String(length=160), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("contexto", mysql.JSON(), nullable=False),
        sa.Column("enviado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("intentos", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_id"], ["usuario.id"], name=op.f("fk_aviso_enviado_destinatario_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aviso_enviado")),
        sa.UniqueConstraint("coach_id", "llave", name="uq_aviso_llave"),
        sa.UniqueConstraint("ulid", name=op.f("uq_aviso_enviado_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_aviso_destinatario", "aviso_enviado", ["destinatario_id", "creado_en"], unique=False
    )
    op.create_index(op.f("ix_aviso_enviado_coach_id"), "aviso_enviado", ["coach_id"], unique=False)
    op.create_table(
        "cobro_coach",
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("metodo", sa.String(length=40), nullable=False),
        sa.Column("periodo_inicia", sa.Date(), nullable=True),
        sa.Column("periodo_termina", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("registrado_por", sa.BigInteger(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["coach_id"], ["coach.id"], name=op.f("fk_cobro_coach_coach_id")),
        sa.ForeignKeyConstraint(
            ["registrado_por"], ["usuario.id"], name=op.f("fk_cobro_coach_registrado_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cobro_coach")),
        sa.UniqueConstraint("ulid", name=op.f("uq_cobro_coach_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_cobro_coach_fecha", "cobro_coach", ["coach_id", "fecha"], unique=False)
    op.create_table(
        "sesion",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("vence_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("revocada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuario.id"], name=op.f("fk_sesion_usuario_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sesion")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sesion_token_hash")),
        sa.UniqueConstraint("ulid", name=op.f("uq_sesion_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_sesion_coach_id"), "sesion", ["coach_id"], unique=False)
    op.create_index("ix_sesion_vence_en", "sesion", ["vence_en"], unique=False)
    op.create_table(
        "suscripcion_coach",
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("plan", sa.String(length=40), nullable=False),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("periodicidad", sa.String(length=10), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("inicia_en", sa.Date(), nullable=False),
        sa.Column("vigente_hasta", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('cortesia','al_corriente','por_vencer','vencida','cancelada')",
            name=op.f("ck_suscripcion_coach_estado_valido"),
        ),
        sa.CheckConstraint(
            "periodicidad in ('mensual','anual')",
            name=op.f("ck_suscripcion_coach_periodicidad_valida"),
        ),
        sa.ForeignKeyConstraint(
            ["coach_id"], ["coach.id"], name=op.f("fk_suscripcion_coach_coach_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suscripcion_coach")),
        sa.UniqueConstraint("coach_id", name="uq_suscripcion_coach"),
        sa.UniqueConstraint("ulid", name=op.f("uq_suscripcion_coach_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_table(
        "suscripcion_push",
        sa.Column("usuario_id", sa.BigInteger(), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("endpoint_hash", sa.String(length=64), nullable=False),
        sa.Column("p256dh", sa.String(length=255), nullable=False),
        sa.Column("auth", sa.String(length=255), nullable=False),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("ultimo_envio_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("fallos", sa.Integer(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"], ["usuario.id"], name=op.f("fk_suscripcion_push_usuario_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suscripcion_push")),
        sa.UniqueConstraint("endpoint_hash", name="uq_suscripcion_endpoint"),
        sa.UniqueConstraint("ulid", name=op.f("uq_suscripcion_push_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_suscripcion_push_coach_id"), "suscripcion_push", ["coach_id"], unique=False
    )
    op.create_index("ix_suscripcion_usuario", "suscripcion_push", ["usuario_id"], unique=False)
    op.create_table(
        "acceso_sensible",
        sa.Column("actor_id", sa.BigInteger(), nullable=False),
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("recurso", sa.String(length=60), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"], ["usuario.id"], name=op.f("fk_acceso_sensible_actor_id")
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_acceso_sensible_alumna_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_acceso_sensible")),
        sa.UniqueConstraint("ulid", name=op.f("uq_acceso_sensible_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_acceso_alumna_creado", "acceso_sensible", ["alumna_id", "creado_en"], unique=False
    )
    op.create_index(
        op.f("ix_acceso_sensible_coach_id"), "acceso_sensible", ["coach_id"], unique=False
    )
    op.create_table(
        "ciclo",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("inicia_en", sa.Date(), nullable=False),
        sa.Column("termina_en", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("precio", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_ciclo_alumna_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ciclo")),
        sa.UniqueConstraint("alumna_id", "numero", name="uq_ciclo_alumna_numero"),
        sa.UniqueConstraint("ulid", name=op.f("uq_ciclo_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_ciclo_coach_id"), "ciclo", ["coach_id"], unique=False)
    op.create_table(
        "cita",
        sa.Column("alumna_id", sa.BigInteger(), nullable=True),
        sa.Column("titulo", sa.String(length=160), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("modalidad", sa.String(length=20), nullable=False),
        sa.Column("inicia_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("termina_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("enlace", sa.String(length=255), nullable=True),
        sa.Column("lugar", sa.String(length=160), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("recordatorio_enviado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("cancelada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("motivo_cancelacion", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('agendada','confirmada','realizada','cancelada')",
            name=op.f("ck_cita_estado_valido"),
        ),
        sa.CheckConstraint(
            "modalidad in ('presencial','video','telefono')", name=op.f("ck_cita_modalidad_valida")
        ),
        sa.CheckConstraint("tipo in ('consulta','bloqueo')", name=op.f("ck_cita_tipo_valido")),
        sa.CheckConstraint("termina_en > inicia_en", name=op.f("ck_cita_rango_valido")),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_cita_alumna_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cita")),
        sa.UniqueConstraint("ulid", name=op.f("uq_cita_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_cita_coach_id"), "cita", ["coach_id"], unique=False)
    op.create_index("ix_cita_coach_inicia", "cita", ["coach_id", "inicia_en"], unique=False)
    op.create_table(
        "clave_temporal",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("emitida_por", sa.BigInteger(), nullable=False),
        sa.Column("hash", sa.String(length=255), nullable=False),
        sa.Column("vence_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("usada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("motivo_verificacion", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_clave_temporal_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["emitida_por"], ["usuario.id"], name=op.f("fk_clave_temporal_emitida_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clave_temporal")),
        sa.UniqueConstraint("ulid", name=op.f("uq_clave_temporal_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_clave_temporal_coach_id"), "clave_temporal", ["coach_id"], unique=False
    )
    op.create_table(
        "consentimiento",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=30), nullable=False),
        sa.Column("version_texto", sa.String(length=20), nullable=False),
        sa.Column("texto_hash", sa.String(length=64), nullable=False),
        sa.Column("aceptado_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("revocado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo in ('terminos','privacidad','protocolo_foto','datos_salud')",
            name=op.f("ck_consentimiento_tipo_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_consentimiento_alumna_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_consentimiento")),
        sa.UniqueConstraint("ulid", name=op.f("uq_consentimiento_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_consentimiento_alumna_tipo", "consentimiento", ["alumna_id", "tipo"], unique=False
    )
    op.create_index(
        op.f("ix_consentimiento_coach_id"), "consentimiento", ["coach_id"], unique=False
    )
    op.create_table(
        "foto_de_comida",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("subida_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("purgada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("tiempo", sa.String(length=60), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("comentario", sa.Text(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_foto_de_comida_alumna_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_foto_de_comida")),
        sa.UniqueConstraint("ulid", name=op.f("uq_foto_de_comida_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_foto_comida_alumna_subida", "foto_de_comida", ["alumna_id", "subida_en"], unique=False
    )
    op.create_index(
        "ix_foto_comida_purga", "foto_de_comida", ["purgada_en", "subida_en"], unique=False
    )
    op.create_index(
        op.f("ix_foto_de_comida_coach_id"), "foto_de_comida", ["coach_id"], unique=False
    )
    op.create_table(
        "historial_clinico",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("lesiones", sa.Text(), nullable=True),
        sa.Column("condiciones", sa.Text(), nullable=True),
        sa.Column("medicacion", sa.Text(), nullable=True),
        sa.Column("restricciones", sa.Text(), nullable=True),
        sa.Column("vigente_desde", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("registrado_por", sa.BigInteger(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_historial_clinico_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["registrado_por"], ["usuario.id"], name=op.f("fk_historial_clinico_registrado_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_historial_clinico")),
        sa.UniqueConstraint("ulid", name=op.f("uq_historial_clinico_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_historial_alumna_vigente",
        "historial_clinico",
        ["alumna_id", "vigente_desde"],
        unique=False,
    )
    op.create_index(
        op.f("ix_historial_clinico_coach_id"), "historial_clinico", ["coach_id"], unique=False
    )
    op.create_table(
        "mensaje",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("autor", sa.String(length=10), nullable=False),
        sa.Column("cuerpo", sa.Text(), nullable=False),
        sa.Column("adjunto_key", sa.String(length=255), nullable=True),
        sa.Column("enviado_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("leido_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_mensaje_alumna_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_mensaje")),
        sa.UniqueConstraint("ulid", name=op.f("uq_mensaje_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_mensaje_alumna_enviado", "mensaje", ["alumna_id", "enviado_en"], unique=False
    )
    op.create_index(op.f("ix_mensaje_coach_id"), "mensaje", ["coach_id"], unique=False)
    op.create_table(
        "notificacion",
        sa.Column("destinatario_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=40), nullable=False),
        sa.Column("payload", mysql.JSON(), nullable=False),
        sa.Column("canal", sa.String(length=20), nullable=False),
        sa.Column("enviada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("leida_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("anuncio_id", sa.BigInteger(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["anuncio_id"], ["anuncio.id"], name=op.f("fk_notificacion_anuncio_id")
        ),
        sa.ForeignKeyConstraint(
            ["destinatario_id"], ["usuario.id"], name=op.f("fk_notificacion_destinatario_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notificacion")),
        sa.UniqueConstraint("ulid", name=op.f("uq_notificacion_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_notificacion_coach_id"), "notificacion", ["coach_id"], unique=False)
    op.create_index(
        "ix_notificacion_destinatario",
        "notificacion",
        ["destinatario_id", "leida_en"],
        unique=False,
    )
    op.create_table(
        "respuesta_cuestionario",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("pregunta_id", sa.BigInteger(), nullable=False),
        sa.Column("valor", sa.Text(), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_respuesta_cuestionario_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["pregunta_id"],
            ["pregunta_cuestionario.id"],
            name=op.f("fk_respuesta_cuestionario_pregunta_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_respuesta_cuestionario")),
        sa.UniqueConstraint("alumna_id", "pregunta_id", name="uq_respuesta_alumna_pregunta"),
        sa.UniqueConstraint("ulid", name=op.f("uq_respuesta_cuestionario_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_respuesta_cuestionario_coach_id"),
        "respuesta_cuestionario",
        ["coach_id"],
        unique=False,
    )
    op.create_table(
        "solicitud_arco",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("derecho", sa.String(length=1), nullable=False),
        sa.Column("recibida_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("respondida_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("resuelta_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("detalle", sa.Text(), nullable=True),
        sa.Column("respuesta", sa.Text(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "derecho in ('A','R','C','O')", name=op.f("ck_solicitud_arco_derecho_valido")
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_solicitud_arco_alumna_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solicitud_arco")),
        sa.UniqueConstraint("ulid", name=op.f("uq_solicitud_arco_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_solicitud_arco_coach_id"), "solicitud_arco", ["coach_id"], unique=False
    )
    op.create_table(
        "solicitud_registro",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("codigo_hash", sa.String(length=64), nullable=False),
        sa.Column("codigo_vence_en", app.datos.base.MarcaDeTiempo(), nullable=False),
        sa.Column("intentos", mysql.TINYINT(), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=True),
        sa.Column("recordatorio_enviado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("decidida_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("motivo_descarte", sa.String(length=255), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('sin_verificar','en_curso','esperando','aceptada','descartada')",
            name=op.f("ck_solicitud_registro_estado_solicitud_valido"),
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_solicitud_registro_alumna_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_solicitud_registro")),
        sa.UniqueConstraint("alumna_id", name="uq_solicitud_alumna"),
        sa.UniqueConstraint("ulid", name=op.f("uq_solicitud_registro_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_solicitud_coach_estado", "solicitud_registro", ["coach_id", "estado"], unique=False
    )
    op.create_index(
        op.f("ix_solicitud_registro_coach_id"), "solicitud_registro", ["coach_id"], unique=False
    )
    op.create_table(
        "chequeo",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("ciclo_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("estado", sa.String(length=30), nullable=False),
        sa.Column("ayuno_confirmado", sa.Boolean(), nullable=False),
        sa.Column("enviado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("validado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("validado_por", sa.BigInteger(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("motivo_rechazo", sa.Text(), nullable=True),
        sa.Column("nota_alumna", sa.Text(), nullable=True),
        sa.Column("alerta_outlier", sa.Boolean(), nullable=False),
        sa.Column("justificacion_outlier", sa.Text(), nullable=True),
        sa.Column("varianza_confirmada", sa.Boolean(), nullable=False),
        sa.Column("porcentaje_grasa", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("estimado_por", sa.BigInteger(), nullable=True),
        sa.Column("bascula_usada", sa.String(length=120), nullable=True),
        sa.Column("lugar_usado", sa.String(length=120), nullable=True),
        sa.Column("hora_usada", sa.String(length=5), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('borrador','pendiente_evaluacion','validado','rechazado_calidad','descartado')",
            name=op.f("ck_chequeo_estado_valido"),
        ),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_chequeo_alumna_id")),
        sa.ForeignKeyConstraint(["ciclo_id"], ["ciclo.id"], name=op.f("fk_chequeo_ciclo_id")),
        sa.ForeignKeyConstraint(
            ["estimado_por"], ["usuario.id"], name=op.f("fk_chequeo_estimado_por")
        ),
        sa.ForeignKeyConstraint(
            ["validado_por"], ["usuario.id"], name=op.f("fk_chequeo_validado_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_chequeo")),
        sa.UniqueConstraint("ulid", name=op.f("uq_chequeo_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_chequeo_alumna_fecha", "chequeo", ["alumna_id", "fecha"], unique=False)
    op.create_index(op.f("ix_chequeo_coach_id"), "chequeo", ["coach_id"], unique=False)
    op.create_table(
        "pago",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("ciclo_id", sa.BigInteger(), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("metodo", sa.String(length=40), nullable=True),
        sa.Column("comprobante_key", sa.String(length=255), nullable=True),
        sa.Column("ocr", mysql.JSON(), nullable=True),
        sa.Column("confianza", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("validado_por", sa.BigInteger(), nullable=True),
        sa.Column("validado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_pago_alumna_id")),
        sa.ForeignKeyConstraint(["ciclo_id"], ["ciclo.id"], name=op.f("fk_pago_ciclo_id")),
        sa.ForeignKeyConstraint(
            ["validado_por"], ["usuario.id"], name=op.f("fk_pago_validado_por")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pago")),
        sa.UniqueConstraint("ulid", name=op.f("uq_pago_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_pago_coach_id"), "pago", ["coach_id"], unique=False)
    op.create_table(
        "parametros_ciclo",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("ciclo_id", sa.BigInteger(), nullable=False),
        sa.Column("nivel_actividad", sa.String(length=20), nullable=False),
        sa.Column("porcentaje_ajuste", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("reparto_carbohidrato", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("reparto_proteina", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("reparto_grasa", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("base_proteina", sa.String(length=30), nullable=False),
        sa.Column("dias_refeed", mysql.TINYINT(), nullable=False),
        sa.Column("porcentaje_dia_refeed", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column("relacion_ganancia", sa.String(length=5), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "dias_refeed between 0 and 2", name=op.f("ck_parametros_ciclo_dias_refeed_rango")
        ),
        sa.CheckConstraint(
            "reparto_carbohidrato + reparto_proteina + reparto_grasa = 1.000",
            name=op.f("ck_parametros_ciclo_reparto_suma_uno"),
        ),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_parametros_ciclo_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["ciclo_id"], ["ciclo.id"], name=op.f("fk_parametros_ciclo_ciclo_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_parametros_ciclo")),
        sa.UniqueConstraint("ciclo_id", name="uq_parametros_ciclo"),
        sa.UniqueConstraint("ulid", name=op.f("uq_parametros_ciclo_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        op.f("ix_parametros_ciclo_coach_id"), "parametros_ciclo", ["coach_id"], unique=False
    )
    op.create_table(
        "plan",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("ciclo_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("publicado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("contenido", mysql.JSON(), nullable=False),
        sa.Column("kcal_objetivo", sa.Integer(), nullable=True),
        sa.Column("proteina_g", sa.Integer(), nullable=True),
        sa.Column("carbohidrato_g", sa.Integer(), nullable=True),
        sa.Column("grasa_g", sa.Integer(), nullable=True),
        sa.Column("frecuencia_fotos", sa.String(length=12), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('borrador','publicado')", name=op.f("ck_plan_estado_valido")
        ),
        sa.CheckConstraint(
            "tipo in ('nutricion','entrenamiento')", name=op.f("ck_plan_tipo_valido")
        ),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_plan_alumna_id")),
        sa.ForeignKeyConstraint(["ciclo_id"], ["ciclo.id"], name=op.f("fk_plan_ciclo_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_plan")),
        sa.UniqueConstraint("ulid", name=op.f("uq_plan_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index("ix_plan_alumna_ciclo", "plan", ["alumna_id", "ciclo_id"], unique=False)
    op.create_index(op.f("ix_plan_coach_id"), "plan", ["coach_id"], unique=False)
    op.create_table(
        "foto",
        sa.Column("chequeo_id", sa.BigInteger(), nullable=False),
        sa.Column("angulo", sa.String(length=10), nullable=False),
        sa.Column("storage_key", sa.String(length=255), nullable=True),
        sa.Column("ancho", sa.Integer(), nullable=True),
        sa.Column("alto", sa.Integer(), nullable=True),
        sa.Column("bytes", sa.BigInteger(), nullable=True),
        sa.Column("nitidez", sa.Numeric(precision=10, scale=3), nullable=True),
        sa.Column("luminancia", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("estado_auto", sa.String(length=20), nullable=False),
        sa.Column("es_linea_base", sa.Boolean(), nullable=False),
        sa.Column("tomada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("subida_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("purgada_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("motivo_purga", sa.String(length=60), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "angulo in ('frontal','perfil','espalda')", name=op.f("ck_foto_angulo_valido")
        ),
        sa.ForeignKeyConstraint(["chequeo_id"], ["chequeo.id"], name=op.f("fk_foto_chequeo_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_foto")),
        sa.UniqueConstraint("chequeo_id", "angulo", name="uq_foto_chequeo_angulo"),
        sa.UniqueConstraint("ulid", name=op.f("uq_foto_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_foto_coach_id"), "foto", ["coach_id"], unique=False)
    op.create_index("ix_foto_purga", "foto", ["purgada_en", "tomada_en"], unique=False)
    op.create_table(
        "medida",
        sa.Column("chequeo_id", sa.BigInteger(), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("valor", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo in ('cintura','abdomen','cadera','busto','pecho','brazo','muslo','pantorrilla')",
            name=op.f("ck_medida_tipo_valido"),
        ),
        sa.CheckConstraint("valor > 0", name=op.f("ck_medida_valor_positivo")),
        sa.ForeignKeyConstraint(["chequeo_id"], ["chequeo.id"], name=op.f("fk_medida_chequeo_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_medida")),
        sa.UniqueConstraint("chequeo_id", "tipo", name="uq_medida_chequeo_tipo"),
        sa.UniqueConstraint("ulid", name=op.f("uq_medida_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_medida_coach_id"), "medida", ["coach_id"], unique=False)
    op.create_table(
        "movimiento_financiero",
        sa.Column("tipo", sa.String(length=10), nullable=False),
        sa.Column("categoria", sa.String(length=30), nullable=False),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("concepto", sa.String(length=200), nullable=False),
        sa.Column("alumna_id", sa.BigInteger(), nullable=True),
        sa.Column("pago_id", sa.BigInteger(), nullable=True),
        sa.Column("automatico", sa.Boolean(), nullable=False),
        sa.Column("comprobante_key", sa.String(length=255), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "tipo in ('ingreso','gasto')", name=op.f("ck_movimiento_financiero_tipo_valido")
        ),
        sa.CheckConstraint("monto > 0", name=op.f("ck_movimiento_financiero_monto_positivo")),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_movimiento_financiero_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["pago_id"], ["pago.id"], name=op.f("fk_movimiento_financiero_pago_id")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_movimiento_financiero")),
        sa.UniqueConstraint("ulid", name=op.f("uq_movimiento_financiero_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_movimiento_coach_fecha", "movimiento_financiero", ["coach_id", "fecha"], unique=False
    )
    op.create_index(
        op.f("ix_movimiento_financiero_coach_id"),
        "movimiento_financiero",
        ["coach_id"],
        unique=False,
    )
    op.create_table(
        "pesaje",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("chequeo_id", sa.BigInteger(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("peso_kg", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("bascula_ref", sa.String(length=120), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint("peso_kg between 30.0 and 250.0", name=op.f("ck_pesaje_peso_rango")),
        sa.ForeignKeyConstraint(["alumna_id"], ["alumna.id"], name=op.f("fk_pesaje_alumna_id")),
        sa.ForeignKeyConstraint(["chequeo_id"], ["chequeo.id"], name=op.f("fk_pesaje_chequeo_id")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pesaje")),
        sa.UniqueConstraint("alumna_id", "fecha", name="uq_pesaje_alumna_fecha"),
        sa.UniqueConstraint("ulid", name=op.f("uq_pesaje_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(op.f("ix_pesaje_coach_id"), "pesaje", ["coach_id"], unique=False)
    op.create_table(
        "cobro_programado",
        sa.Column("alumna_id", sa.BigInteger(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("motivo", sa.String(length=20), nullable=False),
        sa.Column("concepto", sa.String(length=180), nullable=True),
        sa.Column("monto", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("estado", sa.String(length=20), nullable=False),
        sa.Column("movimiento_id", sa.BigInteger(), nullable=True),
        sa.Column("pagado_en", sa.Date(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("comprobante_key", sa.String(length=255), nullable=True),
        sa.Column("subido_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("ocr", mysql.JSON(), nullable=True),
        sa.Column("confianza", sa.Numeric(precision=4, scale=3), nullable=True),
        sa.Column("motivo_rechazo", sa.Text(), nullable=True),
        sa.Column("revisado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("comprobante_purgado_en", app.datos.base.MarcaDeTiempo(), nullable=True),
        sa.Column("coach_id", sa.BigInteger(), nullable=False),
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ulid", mysql.CHAR(length=26), nullable=False),
        sa.Column(
            "creado_en",
            app.datos.base.MarcaDeTiempo(),
            server_default=sa.text("now(3)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "estado in ('pendiente','en_revision','pagado','cancelado')",
            name=op.f("ck_cobro_programado_estado_cobro_valido"),
        ),
        sa.CheckConstraint(
            "motivo in ('inscripcion','mensualidad','cita','material','otro')",
            name=op.f("ck_cobro_programado_motivo_valido"),
        ),
        sa.CheckConstraint("monto > 0", name=op.f("ck_cobro_programado_monto_positivo")),
        sa.ForeignKeyConstraint(
            ["alumna_id"], ["alumna.id"], name=op.f("fk_cobro_programado_alumna_id")
        ),
        sa.ForeignKeyConstraint(
            ["movimiento_id"],
            ["movimiento_financiero.id"],
            name=op.f("fk_cobro_programado_movimiento_id"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_cobro_programado")),
        sa.UniqueConstraint("ulid", name=op.f("uq_cobro_programado_ulid")),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_0900_ai_ci",
        mysql_engine="InnoDB",
    )
    op.create_index(
        "ix_cobro_alumna_fecha", "cobro_programado", ["alumna_id", "fecha"], unique=False
    )
    op.create_index(
        op.f("ix_cobro_programado_coach_id"), "cobro_programado", ["coach_id"], unique=False
    )


def downgrade() -> None:
    """Tira el esquema entero, en orden inverso al de creacion.

    Se apagan las comprobaciones de clave ajena mientras dura: al deshacer del todo no hay
    un orden bueno —hay ciclos entre alumna, usuario y coach— y el autogenerador tiraba los
    indices uno a uno, que MySQL rechaza cuando una clave ajena los necesita. Los indices se
    van con su tabla, asi que no hace falta nombrarlos.
    """
    op.execute("SET FOREIGN_KEY_CHECKS = 0")
    for tabla in (
        "cobro_programado",
        "pesaje",
        "movimiento_financiero",
        "medida",
        "foto",
        "plan",
        "parametros_ciclo",
        "pago",
        "chequeo",
        "solicitud_registro",
        "solicitud_arco",
        "respuesta_cuestionario",
        "notificacion",
        "mensaje",
        "historial_clinico",
        "foto_de_comida",
        "consentimiento",
        "clave_temporal",
        "cita",
        "ciclo",
        "acceso_sensible",
        "suscripcion_push",
        "suscripcion_coach",
        "sesion",
        "cobro_coach",
        "aviso_enviado",
        "anuncio",
        "alumna",
        "vulneracion",
        "usuario",
        "trabajo",
        "tarifa",
        "servicio",
        "presentacion_coach",
        "pregunta_cuestionario",
        "plantilla",
        "intento_de_acceso",
        "horario_atencion",
        "ejercicio",
        "coach",
        "bitacora",
        "alimento",
    ):
        op.drop_table(tabla)
    op.execute("SET FOREIGN_KEY_CHECKS = 1")
