#!/usr/bin/env bash
#
# Respaldo cifrado de la base y de los archivos sensibles.
#
# DOS DECISIONES QUE NO SON OBVIAS:
#
# 1. **Los respaldos se cifran aparte del volumen.** El volumen LUKS protege el disco del
#    servidor; un respaldo sale de ese disco por definición —al almacenamiento remoto, al
#    correo de alguien, a un USB— y ahí el cifrado del volumen ya no lo acompaña.
#
# 2. **La rotación es corta a propósito: 30 días.** El Anexo Legal §10 promete que las
#    fotografías se borran a los 4 meses y que «la purga alcanza también a las copias de
#    respaldo al rotarlas». Un respaldo guardado un año convertiría esa promesa en mentira:
#    la foto seguiría existiendo, solo que en otro archivo. Con 30 días, lo peor que puede
#    pasar es que una foto purgada sobreviva un mes más dentro de un respaldo cifrado.
#
#    Si algún día alguien quiere «guardar un año por si acaso», eso hay que cambiarlo primero
#    en los cuatro documentos legales, no aquí.
#
# Uso:
#   sudo bash despliegue/respaldo.sh preparar     # una vez: genera la llave
#   sudo bash despliegue/respaldo.sh correr       # lo que ejecuta el timer
#   sudo bash despliegue/respaldo.sh verificar    # prueba de restauración
#   sudo bash despliegue/respaldo.sh restaurar respaldo-2026-08-13.sql.gz.gpg

set -euo pipefail

DESTINO=/var/backups/myprogressplan
DATOS=/var/lib/myprogressplan
LLAVE=/etc/myprogressplan/respaldo.key
CONFIG=/etc/myprogressplan/config.env

#: Días que se conservan. Ver la nota 2 del encabezado antes de subirlo.
DIAS_RETENCION=30

#: Copia fuera del servidor. Vacío = solo local, que no es un respaldo de verdad: un disco
#: que se pierde se lleva el original y la copia.
REMOTO="${MPP_RESPALDO_REMOTO:-}"

exigir_root() {
    [[ $EUID -eq 0 ]] || { echo "Esto necesita root: usa sudo." >&2; exit 1; }
}

bd_url() {
    # LM_BD_URL=mysql+pymysql://usuario:clave@host:puerto/base?charset=utf8mb4
    grep -E '^LM_BD_URL=' "$CONFIG" | head -1 | cut -d= -f2-
}

preparar() {
    command -v gpg >/dev/null || { apt-get update -qq && apt-get install -y -qq gnupg; }

    install -d -m 700 /etc/myprogressplan
    install -d -m 700 "$DESTINO"

    if [[ -e $LLAVE ]]; then
        echo "La llave ya existe. No la toco: regenerarla dejaría ilegibles los respaldos viejos."
        return
    fi

    # Frase larga de /dev/urandom. Nadie la teclea nunca; vive aquí y en tu gestor de
    # contraseñas, que es donde tiene que estar la copia.
    head -c 48 /dev/urandom | base64 -w0 > "$LLAVE"
    chmod 400 "$LLAVE"

    cat <<AVISO

Llave creada en $LLAVE.

CÓPIALA AHORA a tu gestor de contraseñas:

  sudo cat $LLAVE

Un respaldo cifrado sin su llave es un archivo inútil. La noche que lo necesites no vas a
tener el servidor a mano para leerla: por eso se copia hoy y no el día del incidente.

AVISO
}

correr() {
    [[ -r $LLAVE ]] || { echo "Falta la llave. Corre: $0 preparar" >&2; exit 1; }
    install -d -m 700 "$DESTINO"

    local url fecha base
    url=$(bd_url)
    fecha=$(date +%Y-%m-%d_%H%M)

    # Descompone la URL de SQLAlchemy sin depender de Python.
    local sin_esquema="${url#*://}"
    local credenciales="${sin_esquema%%@*}"
    local resto="${sin_esquema#*@}"
    local usuario="${credenciales%%:*}"
    local clave="${credenciales#*:}"
    local hostpuerto="${resto%%/*}"
    local host="${hostpuerto%%:*}"
    local puerto="${hostpuerto#*:}"
    base="${resto#*/}"; base="${base%%\?*}"

    echo "== Base de datos"
    # `--single-transaction` toma una instantánea consistente sin bloquear escrituras: en
    # InnoDB no hace falta parar la aplicación para respaldar.
    MYSQL_PWD="$clave" mysqldump \
        --single-transaction --quick --routines --events \
        -h "$host" -P "${puerto:-3306}" -u "$usuario" "$base" \
        | gzip -9 \
        | gpg --batch --yes --symmetric --cipher-algo AES256 \
              --passphrase-file "$LLAVE" \
              -o "$DESTINO/bd-$fecha.sql.gz.gpg"

    echo "== Archivos sensibles"
    if mountpoint -q "$DATOS"; then
        tar -C "$DATOS" -cf - . \
            | gzip -9 \
            | gpg --batch --yes --symmetric --cipher-algo AES256 \
                  --passphrase-file "$LLAVE" \
                  -o "$DESTINO/datos-$fecha.tar.gz.gpg"
    else
        # Respaldar el punto de montaje vacío produciría un archivo válido y vacío, que es la
        # peor clase de respaldo: el que parece que funcionó.
        echo "   AVISO: $DATOS no está montado. No respaldo archivos." >&2
    fi

    chmod 600 "$DESTINO"/*.gpg

    echo "== Rotación (${DIAS_RETENCION} días)"
    find "$DESTINO" -name '*.gpg' -mtime "+$DIAS_RETENCION" -print -delete

    if [[ -n $REMOTO ]]; then
        echo "== Copia fuera del servidor"
        rsync -a --delete "$DESTINO/" "$REMOTO/"
    else
        echo "   AVISO: sin destino remoto. Un respaldo que vive en el mismo disco que el" >&2
        echo "   original no protege del fallo que más pasa. Define MPP_RESPALDO_REMOTO." >&2
    fi

    ls -lh "$DESTINO" | tail -n +2
}

verificar() {
    # La prueba de restauración del checklist legal. Un respaldo que nunca se restauró no es
    # un respaldo: es un archivo con nombre esperanzador.
    local ultimo
    ultimo=$(ls -t "$DESTINO"/bd-*.sql.gz.gpg 2>/dev/null | head -1) || true
    [[ -n ${ultimo:-} ]] || { echo "No hay ningún respaldo que verificar." >&2; exit 1; }

    echo "== Restaurando $ultimo en una base desechable"
    local prueba="mpp_prueba_restauracion"
    local url usuario clave host puerto
    url=$(bd_url)
    local sin_esquema="${url#*://}"
    usuario="${sin_esquema%%:*}"
    clave="${sin_esquema#*:}"; clave="${clave%%@*}"
    host="${sin_esquema#*@}"; host="${host%%:*}"
    puerto="${sin_esquema##*@}"; puerto="${puerto#*:}"; puerto="${puerto%%/*}"

    MYSQL_PWD="$clave" mysql -h "$host" -P "${puerto:-3306}" -u "$usuario" \
        -e "DROP DATABASE IF EXISTS $prueba; CREATE DATABASE $prueba CHARACTER SET utf8mb4"

    gpg --batch --quiet --decrypt --passphrase-file "$LLAVE" "$ultimo" \
        | gunzip \
        | MYSQL_PWD="$clave" mysql -h "$host" -P "${puerto:-3306}" -u "$usuario" "$prueba"

    local tablas
    tablas=$(MYSQL_PWD="$clave" mysql -N -B -h "$host" -P "${puerto:-3306}" -u "$usuario" \
        -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='$prueba'")

    MYSQL_PWD="$clave" mysql -h "$host" -P "${puerto:-3306}" -u "$usuario" \
        -e "DROP DATABASE $prueba"

    if [[ $tablas -lt 25 ]]; then
        echo "FALLA: el respaldo restauró solo $tablas tablas. Deberían ser 30 y pico." >&2
        exit 1
    fi
    echo "Restauración correcta: $tablas tablas. Base de prueba eliminada."
}

restaurar() {
    local archivo=${1:?Falta el archivo de respaldo}
    cat <<ADVERTENCIA

  ATENCIÓN: esto SOBRESCRIBE la base de producción con el contenido de
  $archivo. Todo lo que haya pasado después de ese respaldo se pierde.

  Escribe exactamente: RESTAURAR
ADVERTENCIA
    read -r confirmacion
    [[ $confirmacion == "RESTAURAR" ]] || { echo "Cancelado."; exit 1; }

    local url="$(bd_url)"
    local sin_esquema="${url#*://}"
    local base="${sin_esquema#*/}"; base="${base%%\?*}"
    local usuario="${sin_esquema%%:*}"
    local clave="${sin_esquema#*:}"; clave="${clave%%@*}"
    local host="${sin_esquema#*@}"; host="${host%%:*}"

    systemctl stop myprogressplan || true
    gpg --batch --quiet --decrypt --passphrase-file "$LLAVE" "$archivo" \
        | gunzip \
        | MYSQL_PWD="$clave" mysql -h "$host" -u "$usuario" "$base"
    systemctl start myprogressplan || true
    echo "Restaurado."
}

exigir_root
case "${1:-correr}" in
    preparar)  preparar ;;
    correr)    correr ;;
    verificar) verificar ;;
    restaurar) restaurar "${2:-}" ;;
    *) echo "Uso: $0 {preparar|correr|verificar|restaurar ARCHIVO}" >&2; exit 1 ;;
esac
