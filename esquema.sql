-- Esquema de MyProgressPlan
--
-- Generado desde la base con `herramientas/volcar_esquema.py`. Es una foto para leer en el
-- editor: **no contiene datos** y no se usa para restaurar nada. La fuente de verdad del
-- esquema son los modelos de `app/datos/modelos.py` y la migracion de `migraciones/`.
--
-- Para abrirlo con resaltado y navegacion en VS Code basta la extension de SQL; para
-- consultar la base de verdad, una de cliente MySQL apuntando a la URL de tu config.env.
--
-- Generado: 2026-08-20 18:41 UTC
-- Motor:    8.0.45
-- Tablas:   43

SET FOREIGN_KEY_CHECKS = 0;


-- --------------------------------------------------------------------------
-- acceso_sensible
-- --------------------------------------------------------------------------

CREATE TABLE `acceso_sensible` (
  `actor_id` bigint NOT NULL,
  `alumna_id` bigint NOT NULL,
  `recurso` varchar(60) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_acceso_sensible_ulid` (`ulid`),
  KEY `fk_acceso_sensible_actor_id` (`actor_id`),
  KEY `ix_acceso_sensible_coach_id` (`coach_id`),
  KEY `ix_acceso_alumna_creado` (`alumna_id`,`creado_en`),
  CONSTRAINT `fk_acceso_sensible_actor_id` FOREIGN KEY (`actor_id`) REFERENCES `usuario` (`id`),
  CONSTRAINT `fk_acceso_sensible_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- alembic_version
-- --------------------------------------------------------------------------

CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- alimento
-- --------------------------------------------------------------------------

CREATE TABLE `alimento` (
  `coach_id` bigint DEFAULT NULL,
  `nombre` varchar(160) NOT NULL,
  `marca` varchar(120) DEFAULT NULL,
  `porcion` decimal(7,2) NOT NULL,
  `unidad` varchar(10) NOT NULL,
  `kcal` decimal(7,2) NOT NULL,
  `proteina` decimal(6,2) NOT NULL,
  `carbo` decimal(6,2) NOT NULL,
  `grasa` decimal(6,2) NOT NULL,
  `fibra` decimal(6,2) DEFAULT NULL,
  `sodio` decimal(8,2) DEFAULT NULL,
  `grupo_equivalente` varchar(60) DEFAULT NULL,
  `alergenos` json DEFAULT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_alimento_ulid` (`ulid`),
  KEY `ix_alimento_coach_nombre` (`coach_id`,`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- alumna
-- --------------------------------------------------------------------------

CREATE TABLE `alumna` (
  `usuario_id` bigint DEFAULT NULL,
  `nombre` varchar(120) NOT NULL,
  `whatsapp` varchar(30) DEFAULT NULL,
  `fecha_nacimiento` date NOT NULL,
  `sexo` varchar(1) DEFAULT NULL,
  `estatura_cm` int DEFAULT NULL,
  `tarifa_id` bigint DEFAULT NULL,
  `nivel_experiencia` varchar(20) DEFAULT NULL,
  `equipo` varchar(30) DEFAULT NULL,
  `estres` tinyint DEFAULT NULL,
  `ocupacion` varchar(180) DEFAULT NULL,
  `zona_horaria` varchar(60) NOT NULL,
  `porcentaje_grasa_objetivo` decimal(4,3) DEFAULT NULL,
  `bascula_ref` varchar(120) DEFAULT NULL,
  `lugar_ref` varchar(120) DEFAULT NULL,
  `hora_ref` varchar(5) DEFAULT NULL,
  `cuestionario_completo` tinyint(1) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `baja_en` datetime(3) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_alumna_ulid` (`ulid`),
  KEY `fk_alumna_usuario_id` (`usuario_id`),
  KEY `fk_alumna_tarifa_id` (`tarifa_id`),
  KEY `ix_alumna_coach_id` (`coach_id`),
  CONSTRAINT `fk_alumna_tarifa_id` FOREIGN KEY (`tarifa_id`) REFERENCES `tarifa` (`id`),
  CONSTRAINT `fk_alumna_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`),
  CONSTRAINT `ck_alumna_estatura_rango` CHECK (((`estatura_cm` is null) or (`estatura_cm` between 100 and 250))),
  CONSTRAINT `ck_alumna_estres_rango` CHECK (((`estres` is null) or (`estres` between 1 and 10)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- anuncio
-- --------------------------------------------------------------------------

CREATE TABLE `anuncio` (
  `titulo` varchar(80) NOT NULL,
  `cuerpo` varchar(300) NOT NULL,
  `enviado_por` bigint NOT NULL,
  `enviado_en` datetime(3) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_anuncio_ulid` (`ulid`),
  KEY `fk_anuncio_enviado_por` (`enviado_por`),
  KEY `ix_anuncio_coach_id` (`coach_id`),
  KEY `ix_anuncio_coach_enviado` (`coach_id`,`enviado_en`),
  CONSTRAINT `fk_anuncio_enviado_por` FOREIGN KEY (`enviado_por`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- aviso_enviado
-- --------------------------------------------------------------------------

CREATE TABLE `aviso_enviado` (
  `destinatario_id` bigint DEFAULT NULL,
  `destinatario_correo` varchar(180) NOT NULL,
  `tipo` varchar(40) NOT NULL,
  `llave` varchar(160) NOT NULL,
  `canal` varchar(20) NOT NULL,
  `contexto` json NOT NULL,
  `enviado_en` datetime(3) DEFAULT NULL,
  `error` text,
  `intentos` int NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_aviso_llave` (`coach_id`,`llave`),
  UNIQUE KEY `uq_aviso_enviado_ulid` (`ulid`),
  KEY `ix_aviso_destinatario` (`destinatario_id`,`creado_en`),
  KEY `ix_aviso_enviado_coach_id` (`coach_id`),
  CONSTRAINT `fk_aviso_enviado_destinatario_id` FOREIGN KEY (`destinatario_id`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- bitacora
-- --------------------------------------------------------------------------

CREATE TABLE `bitacora` (
  `actor_tipo` varchar(20) NOT NULL,
  `actor_id` bigint DEFAULT NULL,
  `accion` varchar(60) NOT NULL,
  `entidad` varchar(60) NOT NULL,
  `entidad_id` bigint DEFAULT NULL,
  `detalle` json DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_bitacora_ulid` (`ulid`),
  KEY `ix_bitacora_coach_creado` (`coach_id`,`creado_en`),
  KEY `ix_bitacora_coach_id` (`coach_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- chequeo
-- --------------------------------------------------------------------------

CREATE TABLE `chequeo` (
  `alumna_id` bigint NOT NULL,
  `ciclo_id` bigint NOT NULL,
  `fecha` date NOT NULL,
  `estado` varchar(30) NOT NULL,
  `ayuno_confirmado` tinyint(1) NOT NULL,
  `enviado_en` datetime(3) DEFAULT NULL,
  `validado_en` datetime(3) DEFAULT NULL,
  `validado_por` bigint DEFAULT NULL,
  `feedback` text,
  `motivo_rechazo` text,
  `nota_alumna` text,
  `alerta_outlier` tinyint(1) NOT NULL,
  `justificacion_outlier` text,
  `varianza_confirmada` tinyint(1) NOT NULL,
  `porcentaje_grasa` decimal(4,3) DEFAULT NULL,
  `estimado_por` bigint DEFAULT NULL,
  `bascula_usada` varchar(120) DEFAULT NULL,
  `lugar_usado` varchar(120) DEFAULT NULL,
  `hora_usada` varchar(5) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chequeo_ulid` (`ulid`),
  KEY `fk_chequeo_ciclo_id` (`ciclo_id`),
  KEY `fk_chequeo_validado_por` (`validado_por`),
  KEY `fk_chequeo_estimado_por` (`estimado_por`),
  KEY `ix_chequeo_alumna_fecha` (`alumna_id`,`fecha`),
  KEY `ix_chequeo_coach_id` (`coach_id`),
  CONSTRAINT `fk_chequeo_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_chequeo_ciclo_id` FOREIGN KEY (`ciclo_id`) REFERENCES `ciclo` (`id`),
  CONSTRAINT `fk_chequeo_estimado_por` FOREIGN KEY (`estimado_por`) REFERENCES `usuario` (`id`),
  CONSTRAINT `fk_chequeo_validado_por` FOREIGN KEY (`validado_por`) REFERENCES `usuario` (`id`),
  CONSTRAINT `ck_chequeo_estado_valido` CHECK ((`estado` in (_utf8mb4'borrador',_utf8mb4'pendiente_evaluacion',_utf8mb4'validado',_utf8mb4'rechazado_calidad',_utf8mb4'descartado')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- ciclo
-- --------------------------------------------------------------------------

CREATE TABLE `ciclo` (
  `alumna_id` bigint NOT NULL,
  `numero` int NOT NULL,
  `inicia_en` date NOT NULL,
  `termina_en` date NOT NULL,
  `estado` varchar(20) NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ciclo_alumna_numero` (`alumna_id`,`numero`),
  UNIQUE KEY `uq_ciclo_ulid` (`ulid`),
  KEY `ix_ciclo_coach_id` (`coach_id`),
  CONSTRAINT `fk_ciclo_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- cita
-- --------------------------------------------------------------------------

CREATE TABLE `cita` (
  `alumna_id` bigint DEFAULT NULL,
  `titulo` varchar(160) NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `modalidad` varchar(20) NOT NULL,
  `inicia_en` datetime(3) NOT NULL,
  `termina_en` datetime(3) NOT NULL,
  `enlace` varchar(255) DEFAULT NULL,
  `lugar` varchar(160) DEFAULT NULL,
  `notas` text,
  `recordatorio_enviado_en` datetime(3) DEFAULT NULL,
  `cancelada_en` datetime(3) DEFAULT NULL,
  `motivo_cancelacion` varchar(255) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cita_ulid` (`ulid`),
  KEY `fk_cita_alumna_id` (`alumna_id`),
  KEY `ix_cita_coach_id` (`coach_id`),
  KEY `ix_cita_coach_inicia` (`coach_id`,`inicia_en`),
  CONSTRAINT `fk_cita_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `ck_cita_estado_valido` CHECK ((`estado` in (_utf8mb4'agendada',_utf8mb4'confirmada',_utf8mb4'realizada',_utf8mb4'cancelada'))),
  CONSTRAINT `ck_cita_modalidad_valida` CHECK ((`modalidad` in (_utf8mb4'presencial',_utf8mb4'video',_utf8mb4'telefono'))),
  CONSTRAINT `ck_cita_rango_valido` CHECK ((`termina_en` > `inicia_en`)),
  CONSTRAINT `ck_cita_tipo_valido` CHECK ((`tipo` in (_utf8mb4'consulta',_utf8mb4'bloqueo')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- clave_temporal
-- --------------------------------------------------------------------------

CREATE TABLE `clave_temporal` (
  `alumna_id` bigint NOT NULL,
  `emitida_por` bigint NOT NULL,
  `hash` varchar(255) NOT NULL,
  `vence_en` datetime(3) NOT NULL,
  `usada_en` datetime(3) DEFAULT NULL,
  `motivo_verificacion` varchar(255) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_clave_temporal_ulid` (`ulid`),
  KEY `fk_clave_temporal_alumna_id` (`alumna_id`),
  KEY `fk_clave_temporal_emitida_por` (`emitida_por`),
  KEY `ix_clave_temporal_coach_id` (`coach_id`),
  CONSTRAINT `fk_clave_temporal_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_clave_temporal_emitida_por` FOREIGN KEY (`emitida_por`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- coach
-- --------------------------------------------------------------------------

CREATE TABLE `coach` (
  `nombre` varchar(120) NOT NULL,
  `marca` varchar(120) DEFAULT NULL,
  `slug` varchar(60) NOT NULL,
  `email` varchar(180) NOT NULL,
  `plan` varchar(40) NOT NULL,
  `limite_alumnas` int NOT NULL,
  `estado` varchar(20) NOT NULL,
  `logo_key` varchar(255) DEFAULT NULL,
  `color_acento` varchar(9) NOT NULL,
  `color_secundario` varchar(9) NOT NULL,
  `precio_ciclo` decimal(10,2) NOT NULL,
  `dia_chequeo` tinyint NOT NULL,
  `duracion_consulta_min` int NOT NULL,
  `margen_consulta_min` int NOT NULL,
  `antelacion_horas` int NOT NULL,
  `horizonte_semanas` int NOT NULL,
  `zona_horaria` varchar(60) NOT NULL,
  `registro_abierto` tinyint(1) NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_coach_slug` (`slug`),
  UNIQUE KEY `uq_coach_email` (`email`),
  UNIQUE KEY `uq_coach_ulid` (`ulid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- cobro_coach
-- --------------------------------------------------------------------------

CREATE TABLE `cobro_coach` (
  `coach_id` bigint NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` date NOT NULL,
  `metodo` varchar(40) NOT NULL,
  `periodo_inicia` date DEFAULT NULL,
  `periodo_termina` date DEFAULT NULL,
  `nota` text,
  `registrado_por` bigint DEFAULT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cobro_coach_ulid` (`ulid`),
  KEY `fk_cobro_coach_registrado_por` (`registrado_por`),
  KEY `ix_cobro_coach_fecha` (`coach_id`,`fecha`),
  CONSTRAINT `fk_cobro_coach_coach_id` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`),
  CONSTRAINT `fk_cobro_coach_registrado_por` FOREIGN KEY (`registrado_por`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- cobro_programado
-- --------------------------------------------------------------------------

CREATE TABLE `cobro_programado` (
  `alumna_id` bigint NOT NULL,
  `fecha` date NOT NULL,
  `motivo` varchar(20) NOT NULL,
  `concepto` varchar(180) DEFAULT NULL,
  `monto` decimal(10,2) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `movimiento_id` bigint DEFAULT NULL,
  `pagado_en` date DEFAULT NULL,
  `nota` text,
  `comprobante_key` varchar(255) DEFAULT NULL,
  `subido_en` datetime(3) DEFAULT NULL,
  `ocr` json DEFAULT NULL,
  `confianza` decimal(4,3) DEFAULT NULL,
  `motivo_rechazo` text,
  `revisado_en` datetime(3) DEFAULT NULL,
  `comprobante_purgado_en` datetime(3) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_cobro_programado_ulid` (`ulid`),
  KEY `fk_cobro_programado_movimiento_id` (`movimiento_id`),
  KEY `ix_cobro_alumna_fecha` (`alumna_id`,`fecha`),
  KEY `ix_cobro_programado_coach_id` (`coach_id`),
  CONSTRAINT `fk_cobro_programado_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_cobro_programado_movimiento_id` FOREIGN KEY (`movimiento_id`) REFERENCES `movimiento_financiero` (`id`),
  CONSTRAINT `ck_cobro_programado_estado_cobro_valido` CHECK ((`estado` in (_utf8mb4'pendiente',_utf8mb4'en_revision',_utf8mb4'pagado',_utf8mb4'cancelado'))),
  CONSTRAINT `ck_cobro_programado_monto_positivo` CHECK ((`monto` > 0)),
  CONSTRAINT `ck_cobro_programado_motivo_valido` CHECK ((`motivo` in (_utf8mb4'inscripcion',_utf8mb4'mensualidad',_utf8mb4'cita',_utf8mb4'material',_utf8mb4'otro')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- consentimiento
-- --------------------------------------------------------------------------

CREATE TABLE `consentimiento` (
  `alumna_id` bigint NOT NULL,
  `tipo` varchar(30) NOT NULL,
  `version_texto` varchar(20) NOT NULL,
  `texto_hash` varchar(64) NOT NULL,
  `aceptado_en` datetime(3) NOT NULL,
  `revocado_en` datetime(3) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_consentimiento_ulid` (`ulid`),
  KEY `ix_consentimiento_coach_id` (`coach_id`),
  KEY `ix_consentimiento_alumna_tipo` (`alumna_id`,`tipo`),
  CONSTRAINT `fk_consentimiento_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `ck_consentimiento_tipo_valido` CHECK ((`tipo` in (_utf8mb4'terminos',_utf8mb4'privacidad',_utf8mb4'protocolo_foto',_utf8mb4'datos_salud')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- ejercicio
-- --------------------------------------------------------------------------

CREATE TABLE `ejercicio` (
  `coach_id` bigint DEFAULT NULL,
  `nombre` varchar(160) NOT NULL,
  `grupo` varchar(60) DEFAULT NULL,
  `equipo` varchar(60) DEFAULT NULL,
  `patron` varchar(60) DEFAULT NULL,
  `video_key` varchar(255) DEFAULT NULL,
  `instrucciones` text,
  `contraindicaciones` text,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_ejercicio_ulid` (`ulid`),
  KEY `ix_ejercicio_coach_nombre` (`coach_id`,`nombre`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- foto
-- --------------------------------------------------------------------------

CREATE TABLE `foto` (
  `chequeo_id` bigint NOT NULL,
  `angulo` varchar(10) NOT NULL,
  `storage_key` varchar(255) DEFAULT NULL,
  `ancho` int DEFAULT NULL,
  `alto` int DEFAULT NULL,
  `bytes` bigint DEFAULT NULL,
  `nitidez` decimal(10,3) DEFAULT NULL,
  `luminancia` decimal(6,2) DEFAULT NULL,
  `estado_auto` varchar(20) NOT NULL,
  `es_linea_base` tinyint(1) NOT NULL,
  `tomada_en` datetime(3) DEFAULT NULL,
  `subida_en` datetime(3) DEFAULT NULL,
  `purgada_en` datetime(3) DEFAULT NULL,
  `motivo_purga` varchar(60) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_foto_chequeo_angulo` (`chequeo_id`,`angulo`),
  UNIQUE KEY `uq_foto_ulid` (`ulid`),
  KEY `ix_foto_purga` (`purgada_en`,`tomada_en`),
  KEY `ix_foto_coach_id` (`coach_id`),
  CONSTRAINT `fk_foto_chequeo_id` FOREIGN KEY (`chequeo_id`) REFERENCES `chequeo` (`id`),
  CONSTRAINT `ck_foto_angulo_valido` CHECK ((`angulo` in (_utf8mb4'frontal',_utf8mb4'perfil',_utf8mb4'espalda')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- foto_de_comida
-- --------------------------------------------------------------------------

CREATE TABLE `foto_de_comida` (
  `alumna_id` bigint NOT NULL,
  `storage_key` varchar(255) DEFAULT NULL,
  `subida_en` datetime(3) NOT NULL,
  `purgada_en` datetime(3) DEFAULT NULL,
  `tiempo` varchar(60) DEFAULT NULL,
  `nota` text,
  `comentario` text,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_foto_de_comida_ulid` (`ulid`),
  KEY `ix_foto_comida_purga` (`purgada_en`,`subida_en`),
  KEY `ix_foto_de_comida_coach_id` (`coach_id`),
  KEY `ix_foto_comida_alumna_subida` (`alumna_id`,`subida_en`),
  CONSTRAINT `fk_foto_de_comida_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- historial_clinico
-- --------------------------------------------------------------------------

CREATE TABLE `historial_clinico` (
  `alumna_id` bigint NOT NULL,
  `lesiones` text,
  `condiciones` text,
  `medicacion` text,
  `restricciones` text,
  `vigente_desde` datetime(3) NOT NULL,
  `registrado_por` bigint DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_historial_clinico_ulid` (`ulid`),
  KEY `fk_historial_clinico_registrado_por` (`registrado_por`),
  KEY `ix_historial_clinico_coach_id` (`coach_id`),
  KEY `ix_historial_alumna_vigente` (`alumna_id`,`vigente_desde`),
  CONSTRAINT `fk_historial_clinico_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_historial_clinico_registrado_por` FOREIGN KEY (`registrado_por`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- horario_atencion
-- --------------------------------------------------------------------------

CREATE TABLE `horario_atencion` (
  `dia_semana` tinyint NOT NULL,
  `desde` time NOT NULL,
  `hasta` time NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_horario_atencion_ulid` (`ulid`),
  KEY `ix_horario_coach_dia` (`coach_id`,`dia_semana`),
  KEY `ix_horario_atencion_coach_id` (`coach_id`),
  CONSTRAINT `ck_horario_atencion_dia_semana_valido` CHECK ((`dia_semana` between 0 and 6)),
  CONSTRAINT `ck_horario_atencion_tramo_valido` CHECK ((`hasta` > `desde`))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- intento_de_acceso
-- --------------------------------------------------------------------------

CREATE TABLE `intento_de_acceso` (
  `correo` varchar(180) NOT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `exitoso` tinyint(1) NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_intento_de_acceso_ulid` (`ulid`),
  KEY `ix_intento_ip_cuando` (`ip`,`creado_en`),
  KEY `ix_intento_correo_cuando` (`correo`,`creado_en`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- medida
-- --------------------------------------------------------------------------

CREATE TABLE `medida` (
  `chequeo_id` bigint NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `valor` decimal(5,1) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_medida_chequeo_tipo` (`chequeo_id`,`tipo`),
  UNIQUE KEY `uq_medida_ulid` (`ulid`),
  KEY `ix_medida_coach_id` (`coach_id`),
  CONSTRAINT `fk_medida_chequeo_id` FOREIGN KEY (`chequeo_id`) REFERENCES `chequeo` (`id`),
  CONSTRAINT `ck_medida_tipo_valido` CHECK ((`tipo` in (_utf8mb4'cintura',_utf8mb4'abdomen',_utf8mb4'cadera',_utf8mb4'busto',_utf8mb4'pecho',_utf8mb4'brazo',_utf8mb4'muslo',_utf8mb4'pantorrilla'))),
  CONSTRAINT `ck_medida_valor_positivo` CHECK ((`valor` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- mensaje
-- --------------------------------------------------------------------------

CREATE TABLE `mensaje` (
  `alumna_id` bigint NOT NULL,
  `autor` varchar(10) NOT NULL,
  `cuerpo` text NOT NULL,
  `adjunto_key` varchar(255) DEFAULT NULL,
  `enviado_en` datetime(3) NOT NULL,
  `leido_en` datetime(3) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_mensaje_ulid` (`ulid`),
  KEY `ix_mensaje_alumna_enviado` (`alumna_id`,`enviado_en`),
  KEY `ix_mensaje_coach_id` (`coach_id`),
  CONSTRAINT `fk_mensaje_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- movimiento_financiero
-- --------------------------------------------------------------------------

CREATE TABLE `movimiento_financiero` (
  `tipo` varchar(10) NOT NULL,
  `categoria` varchar(30) NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `fecha` date NOT NULL,
  `concepto` varchar(200) NOT NULL,
  `alumna_id` bigint DEFAULT NULL,
  `pago_id` bigint DEFAULT NULL,
  `automatico` tinyint(1) NOT NULL,
  `comprobante_key` varchar(255) DEFAULT NULL,
  `nota` text,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_movimiento_financiero_ulid` (`ulid`),
  KEY `fk_movimiento_financiero_alumna_id` (`alumna_id`),
  KEY `fk_movimiento_financiero_pago_id` (`pago_id`),
  KEY `ix_movimiento_financiero_coach_id` (`coach_id`),
  KEY `ix_movimiento_coach_fecha` (`coach_id`,`fecha`),
  CONSTRAINT `fk_movimiento_financiero_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_movimiento_financiero_pago_id` FOREIGN KEY (`pago_id`) REFERENCES `pago` (`id`),
  CONSTRAINT `ck_movimiento_financiero_monto_positivo` CHECK ((`monto` > 0)),
  CONSTRAINT `ck_movimiento_financiero_tipo_valido` CHECK ((`tipo` in (_utf8mb4'ingreso',_utf8mb4'gasto')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- notificacion
-- --------------------------------------------------------------------------

CREATE TABLE `notificacion` (
  `destinatario_id` bigint NOT NULL,
  `tipo` varchar(40) NOT NULL,
  `payload` json NOT NULL,
  `canal` varchar(20) NOT NULL,
  `enviada_en` datetime(3) DEFAULT NULL,
  `leida_en` datetime(3) DEFAULT NULL,
  `anuncio_id` bigint DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_notificacion_ulid` (`ulid`),
  KEY `fk_notificacion_anuncio_id` (`anuncio_id`),
  KEY `ix_notificacion_destinatario` (`destinatario_id`,`leida_en`),
  KEY `ix_notificacion_coach_id` (`coach_id`),
  CONSTRAINT `fk_notificacion_anuncio_id` FOREIGN KEY (`anuncio_id`) REFERENCES `anuncio` (`id`),
  CONSTRAINT `fk_notificacion_destinatario_id` FOREIGN KEY (`destinatario_id`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- pago
-- --------------------------------------------------------------------------

CREATE TABLE `pago` (
  `alumna_id` bigint NOT NULL,
  `ciclo_id` bigint NOT NULL,
  `monto` decimal(10,2) NOT NULL,
  `metodo` varchar(40) DEFAULT NULL,
  `comprobante_key` varchar(255) DEFAULT NULL,
  `ocr` json DEFAULT NULL,
  `confianza` decimal(4,3) DEFAULT NULL,
  `estado` varchar(20) NOT NULL,
  `validado_por` bigint DEFAULT NULL,
  `validado_en` datetime(3) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pago_ulid` (`ulid`),
  KEY `fk_pago_alumna_id` (`alumna_id`),
  KEY `fk_pago_ciclo_id` (`ciclo_id`),
  KEY `fk_pago_validado_por` (`validado_por`),
  KEY `ix_pago_coach_id` (`coach_id`),
  CONSTRAINT `fk_pago_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_pago_ciclo_id` FOREIGN KEY (`ciclo_id`) REFERENCES `ciclo` (`id`),
  CONSTRAINT `fk_pago_validado_por` FOREIGN KEY (`validado_por`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- parametros_ciclo
-- --------------------------------------------------------------------------

CREATE TABLE `parametros_ciclo` (
  `alumna_id` bigint NOT NULL,
  `ciclo_id` bigint NOT NULL,
  `nivel_actividad` varchar(20) NOT NULL,
  `porcentaje_ajuste` decimal(4,3) NOT NULL,
  `reparto_carbohidrato` decimal(4,3) NOT NULL,
  `reparto_proteina` decimal(4,3) NOT NULL,
  `reparto_grasa` decimal(4,3) NOT NULL,
  `base_proteina` varchar(30) NOT NULL,
  `dias_refeed` tinyint NOT NULL,
  `porcentaje_dia_refeed` decimal(4,3) NOT NULL,
  `relacion_ganancia` varchar(5) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_parametros_ciclo` (`ciclo_id`),
  UNIQUE KEY `uq_parametros_ciclo_ulid` (`ulid`),
  KEY `fk_parametros_ciclo_alumna_id` (`alumna_id`),
  KEY `ix_parametros_ciclo_coach_id` (`coach_id`),
  CONSTRAINT `fk_parametros_ciclo_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_parametros_ciclo_ciclo_id` FOREIGN KEY (`ciclo_id`) REFERENCES `ciclo` (`id`),
  CONSTRAINT `ck_parametros_ciclo_dias_refeed_rango` CHECK ((`dias_refeed` between 0 and 2)),
  CONSTRAINT `ck_parametros_ciclo_reparto_suma_uno` CHECK ((((`reparto_carbohidrato` + `reparto_proteina`) + `reparto_grasa`) = 1.000))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- pesaje
-- --------------------------------------------------------------------------

CREATE TABLE `pesaje` (
  `alumna_id` bigint NOT NULL,
  `chequeo_id` bigint DEFAULT NULL,
  `fecha` date NOT NULL,
  `peso_kg` decimal(5,1) NOT NULL,
  `bascula_ref` varchar(120) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pesaje_alumna_fecha` (`alumna_id`,`fecha`),
  UNIQUE KEY `uq_pesaje_ulid` (`ulid`),
  KEY `fk_pesaje_chequeo_id` (`chequeo_id`),
  KEY `ix_pesaje_coach_id` (`coach_id`),
  CONSTRAINT `fk_pesaje_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_pesaje_chequeo_id` FOREIGN KEY (`chequeo_id`) REFERENCES `chequeo` (`id`),
  CONSTRAINT `ck_pesaje_peso_rango` CHECK ((`peso_kg` between 30.0 and 250.0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- plan
-- --------------------------------------------------------------------------

CREATE TABLE `plan` (
  `alumna_id` bigint NOT NULL,
  `ciclo_id` bigint NOT NULL,
  `tipo` varchar(20) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `publicado_en` datetime(3) DEFAULT NULL,
  `contenido` json NOT NULL,
  `kcal_objetivo` int DEFAULT NULL,
  `proteina_g` int DEFAULT NULL,
  `carbohidrato_g` int DEFAULT NULL,
  `grasa_g` int DEFAULT NULL,
  `frecuencia_fotos` varchar(12) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_plan_ulid` (`ulid`),
  KEY `fk_plan_ciclo_id` (`ciclo_id`),
  KEY `ix_plan_alumna_ciclo` (`alumna_id`,`ciclo_id`),
  KEY `ix_plan_coach_id` (`coach_id`),
  CONSTRAINT `fk_plan_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_plan_ciclo_id` FOREIGN KEY (`ciclo_id`) REFERENCES `ciclo` (`id`),
  CONSTRAINT `ck_plan_estado_valido` CHECK ((`estado` in (_utf8mb4'borrador',_utf8mb4'publicado'))),
  CONSTRAINT `ck_plan_tipo_valido` CHECK ((`tipo` in (_utf8mb4'nutricion',_utf8mb4'entrenamiento')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- plantilla
-- --------------------------------------------------------------------------

CREATE TABLE `plantilla` (
  `codigo` varchar(30) NOT NULL,
  `nombre` varchar(160) NOT NULL,
  `dias` json NOT NULL,
  `usos` int NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_plantilla_codigo` (`coach_id`,`codigo`),
  UNIQUE KEY `uq_plantilla_ulid` (`ulid`),
  KEY `ix_plantilla_coach_id` (`coach_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- pregunta_cuestionario
-- --------------------------------------------------------------------------

CREATE TABLE `pregunta_cuestionario` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `coach_id` bigint NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `texto` varchar(300) NOT NULL,
  `ayuda` varchar(300) DEFAULT NULL,
  `tipo` varchar(20) NOT NULL DEFAULT 'texto',
  `opciones` json NOT NULL,
  `obligatoria` tinyint(1) NOT NULL DEFAULT '0',
  `orden` int NOT NULL DEFAULT '0',
  `activa` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_pregunta_cuestionario_ulid` (`ulid`),
  KEY `ix_pregunta_coach_orden` (`coach_id`,`orden`),
  CONSTRAINT `fk_pregunta_cuestionario_coach_id` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`),
  CONSTRAINT `ck_pregunta_cuestionario_tipo_pregunta_valido` CHECK ((`tipo` in (_utf8mb4'texto',_utf8mb4'texto_largo',_utf8mb4'numero',_utf8mb4'opcion',_utf8mb4'si_no')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- presentacion_coach
-- --------------------------------------------------------------------------

CREATE TABLE `presentacion_coach` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `coach_id` bigint NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `foto_key` varchar(255) DEFAULT NULL,
  `titulo` varchar(160) NOT NULL DEFAULT '',
  `texto` text NOT NULL,
  `ficha` json NOT NULL,
  `activa` tinyint(1) NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_presentacion_coach_ulid` (`ulid`),
  UNIQUE KEY `uq_presentacion_coach` (`coach_id`),
  KEY `ix_presentacion_coach_coach_id` (`coach_id`),
  CONSTRAINT `fk_presentacion_coach_coach_id` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- respuesta_cuestionario
-- --------------------------------------------------------------------------

CREATE TABLE `respuesta_cuestionario` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `coach_id` bigint NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  `alumna_id` bigint NOT NULL,
  `pregunta_id` bigint NOT NULL,
  `valor` text NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_respuesta_cuestionario_ulid` (`ulid`),
  UNIQUE KEY `uq_respuesta_alumna_pregunta` (`alumna_id`,`pregunta_id`),
  KEY `fk_respuesta_cuestionario_pregunta_id` (`pregunta_id`),
  KEY `ix_respuesta_cuestionario_coach_id` (`coach_id`),
  CONSTRAINT `fk_respuesta_cuestionario_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `fk_respuesta_cuestionario_coach_id` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`),
  CONSTRAINT `fk_respuesta_cuestionario_pregunta_id` FOREIGN KEY (`pregunta_id`) REFERENCES `pregunta_cuestionario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- servicio
-- --------------------------------------------------------------------------

CREATE TABLE `servicio` (
  `nombre` varchar(120) NOT NULL,
  `descripcion` text,
  `motivo` varchar(20) NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `activo` tinyint(1) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_servicio_ulid` (`ulid`),
  KEY `ix_servicio_coach_id` (`coach_id`),
  KEY `ix_servicio_coach_motivo` (`coach_id`,`motivo`),
  CONSTRAINT `ck_servicio_motivo_servicio_valido` CHECK ((`motivo` in (_utf8mb4'inscripcion',_utf8mb4'mensualidad',_utf8mb4'cita',_utf8mb4'material',_utf8mb4'otro'))),
  CONSTRAINT `ck_servicio_precio_servicio_positivo` CHECK ((`precio` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- sesion
-- --------------------------------------------------------------------------

CREATE TABLE `sesion` (
  `usuario_id` bigint NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `vence_en` datetime(3) NOT NULL,
  `revocada_en` datetime(3) DEFAULT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_sesion_token_hash` (`token_hash`),
  UNIQUE KEY `uq_sesion_ulid` (`ulid`),
  KEY `fk_sesion_usuario_id` (`usuario_id`),
  KEY `ix_sesion_coach_id` (`coach_id`),
  KEY `ix_sesion_vence_en` (`vence_en`),
  CONSTRAINT `fk_sesion_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- solicitud_arco
-- --------------------------------------------------------------------------

CREATE TABLE `solicitud_arco` (
  `alumna_id` bigint NOT NULL,
  `derecho` varchar(1) NOT NULL,
  `recibida_en` datetime(3) NOT NULL,
  `respondida_en` datetime(3) DEFAULT NULL,
  `resuelta_en` datetime(3) DEFAULT NULL,
  `estado` varchar(20) NOT NULL,
  `detalle` text,
  `respuesta` text,
  `notas` text,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_solicitud_arco_ulid` (`ulid`),
  KEY `fk_solicitud_arco_alumna_id` (`alumna_id`),
  KEY `ix_solicitud_arco_coach_id` (`coach_id`),
  CONSTRAINT `fk_solicitud_arco_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `ck_solicitud_arco_derecho_valido` CHECK ((`derecho` in (_utf8mb4'A',_utf8mb4'R',_utf8mb4'C',_utf8mb4'O')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- solicitud_registro
-- --------------------------------------------------------------------------

CREATE TABLE `solicitud_registro` (
  `alumna_id` bigint NOT NULL,
  `estado` varchar(20) NOT NULL,
  `codigo_hash` varchar(64) NOT NULL,
  `codigo_vence_en` datetime(3) NOT NULL,
  `intentos` tinyint NOT NULL,
  `ip` varchar(45) DEFAULT NULL,
  `recordatorio_enviado_en` datetime(3) DEFAULT NULL,
  `decidida_en` datetime(3) DEFAULT NULL,
  `motivo_descarte` varchar(255) DEFAULT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_solicitud_alumna` (`alumna_id`),
  UNIQUE KEY `uq_solicitud_registro_ulid` (`ulid`),
  KEY `ix_solicitud_registro_coach_id` (`coach_id`),
  KEY `ix_solicitud_coach_estado` (`coach_id`,`estado`),
  CONSTRAINT `fk_solicitud_registro_alumna_id` FOREIGN KEY (`alumna_id`) REFERENCES `alumna` (`id`),
  CONSTRAINT `ck_solicitud_registro_estado_solicitud_valido` CHECK ((`estado` in (_utf8mb4'sin_verificar',_utf8mb4'en_curso',_utf8mb4'esperando',_utf8mb4'aceptada',_utf8mb4'descartada')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- suscripcion_coach
-- --------------------------------------------------------------------------

CREATE TABLE `suscripcion_coach` (
  `coach_id` bigint NOT NULL,
  `plan` varchar(40) NOT NULL,
  `precio` decimal(10,2) NOT NULL,
  `periodicidad` varchar(10) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `inicia_en` date NOT NULL,
  `vigente_hasta` date DEFAULT NULL,
  `nota` text,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_suscripcion_coach` (`coach_id`),
  UNIQUE KEY `uq_suscripcion_coach_ulid` (`ulid`),
  CONSTRAINT `fk_suscripcion_coach_coach_id` FOREIGN KEY (`coach_id`) REFERENCES `coach` (`id`),
  CONSTRAINT `ck_suscripcion_coach_estado_valido` CHECK ((`estado` in (_utf8mb4'cortesia',_utf8mb4'al_corriente',_utf8mb4'por_vencer',_utf8mb4'vencida',_utf8mb4'cancelada'))),
  CONSTRAINT `ck_suscripcion_coach_periodicidad_valida` CHECK ((`periodicidad` in (_utf8mb4'mensual',_utf8mb4'anual')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- suscripcion_push
-- --------------------------------------------------------------------------

CREATE TABLE `suscripcion_push` (
  `usuario_id` bigint NOT NULL,
  `endpoint` varchar(500) NOT NULL,
  `endpoint_hash` varchar(64) NOT NULL,
  `p256dh` varchar(255) NOT NULL,
  `auth` varchar(255) NOT NULL,
  `user_agent` varchar(255) DEFAULT NULL,
  `ultimo_envio_en` datetime(3) DEFAULT NULL,
  `fallos` int NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_suscripcion_endpoint` (`endpoint_hash`),
  UNIQUE KEY `uq_suscripcion_push_ulid` (`ulid`),
  KEY `ix_suscripcion_push_coach_id` (`coach_id`),
  KEY `ix_suscripcion_usuario` (`usuario_id`),
  CONSTRAINT `fk_suscripcion_push_usuario_id` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- tarifa
-- --------------------------------------------------------------------------

CREATE TABLE `tarifa` (
  `codigo` varchar(30) NOT NULL,
  `nombre` varchar(120) NOT NULL,
  `descripcion` text,
  `precio` decimal(10,2) NOT NULL,
  `dias` int NOT NULL,
  `intensidad` varchar(10) NOT NULL,
  `activa` tinyint(1) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_tarifa_codigo` (`coach_id`,`codigo`),
  UNIQUE KEY `uq_tarifa_ulid` (`ulid`),
  KEY `ix_tarifa_coach_id` (`coach_id`),
  CONSTRAINT `ck_tarifa_dias_rango` CHECK ((`dias` between 1 and 365)),
  CONSTRAINT `ck_tarifa_intensidad_valida` CHECK ((`intensidad` in (_utf8mb4'baja',_utf8mb4'media',_utf8mb4'alta'))),
  CONSTRAINT `ck_tarifa_precio_positivo` CHECK ((`precio` > 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- trabajo
-- --------------------------------------------------------------------------

CREATE TABLE `trabajo` (
  `tipo` varchar(60) NOT NULL,
  `payload` json NOT NULL,
  `estado` varchar(20) NOT NULL,
  `correr_en` datetime(3) NOT NULL,
  `intentos` int NOT NULL,
  `max_intentos` int NOT NULL,
  `ultimo_error` text,
  `terminado_en` datetime(3) DEFAULT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_trabajo_ulid` (`ulid`),
  KEY `ix_trabajo_estado_correr` (`estado`,`correr_en`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- usuario
-- --------------------------------------------------------------------------

CREATE TABLE `usuario` (
  `rol` varchar(20) NOT NULL,
  `email` varchar(180) NOT NULL,
  `hash_contrasena` varchar(255) NOT NULL,
  `estado` varchar(20) NOT NULL,
  `ultimo_acceso_en` datetime(3) DEFAULT NULL,
  `debe_cambiar_contrasena` tinyint(1) NOT NULL,
  `coach_id` bigint NOT NULL,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_usuario_email` (`email`),
  UNIQUE KEY `uq_usuario_ulid` (`ulid`),
  KEY `ix_usuario_coach_id` (`coach_id`),
  CONSTRAINT `ck_usuario_rol_valido` CHECK ((`rol` in (_utf8mb4'coach',_utf8mb4'alumna',_utf8mb4'admin_plataforma')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- --------------------------------------------------------------------------
-- vulneracion
-- --------------------------------------------------------------------------

CREATE TABLE `vulneracion` (
  `detectada_en` datetime(3) NOT NULL,
  `descripcion` text NOT NULL,
  `causa` text,
  `alcance` text,
  `notificado_en` datetime(3) DEFAULT NULL,
  `acciones_correctivas` text,
  `id` bigint NOT NULL AUTO_INCREMENT,
  `ulid` char(26) NOT NULL,
  `creado_en` datetime(3) NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_vulneracion_ulid` (`ulid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;


SET FOREIGN_KEY_CHECKS = 1;
