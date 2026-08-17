#!/usr/bin/env bash
#
# Volumen cifrado para los datos sensibles, en Ubuntu con un solo disco.
#
# Crea un contenedor LUKS en un archivo y lo monta en /var/lib/myfittplan. Ahí viven las
# fotografías de chequeo y los comprobantes de pago; la base de datos va aparte (ver abajo).
#
# QUÉ PROTEGE Y QUÉ NO — importa entenderlo antes de confiar en esto:
#
#   Protege  el disco fuera de servicio. Cuando el proveedor recicla el almacenamiento, o
#            alguien se lleva una copia del volumen, o queda una instantánea vieja en el
#            panel del proveedor, lo que hay dentro es ruido.
#
#   NO       protege contra alguien que entre al servidor con el sistema encendido. La llave
#   protege  está en el propio servidor para que el arranque no exija que alguien teclee una
#            frase a las tres de la mañana; con el volumen montado, root lee los archivos.
#            Contra eso sirven el endurecimiento (`endurecer.sh`) y la bitácora, no el cifrado.
#
# Si prefieres la protección fuerte, quita el archivo de llave y monta a mano tras cada
# reinicio: `cryptsetup open ... && mount ...`. Es una decisión de operación, no de código.
#
# Uso:
#   sudo bash despliegue/volumen-cifrado.sh crear 20      # 20 GiB
#   sudo bash despliegue/volumen-cifrado.sh montar
#   sudo bash despliegue/volumen-cifrado.sh estado

set -euo pipefail

CONTENEDOR=/var/lib/myfittplan.luks
NOMBRE=myfittplan
PUNTO=/var/lib/myfittplan
LLAVE=/etc/myfittplan/volumen.key
USUARIO=myfittplan

exigir_root() {
    [[ $EUID -eq 0 ]] || { echo "Esto necesita root: usa sudo." >&2; exit 1; }
}

crear() {
    local gib=${1:-20}

    command -v cryptsetup >/dev/null || {
        echo "== Instalando cryptsetup"
        apt-get update -qq && apt-get install -y -qq cryptsetup
    }

    [[ -e $CONTENEDOR ]] && { echo "Ya existe $CONTENEDOR. No lo toco." >&2; exit 1; }

    echo "== Reservando ${gib} GiB en $CONTENEDOR"
    # `fallocate` reserva el espacio de golpe: si el disco se llena, es mejor descubrirlo
    # ahora que a mitad de una subida.
    fallocate -l "${gib}G" "$CONTENEDOR"
    chmod 600 "$CONTENEDOR"

    echo "== Generando la llave"
    install -d -m 700 /etc/myfittplan
    # 512 bits de /dev/urandom. Una frase que alguien pueda recordar no aguanta un ataque
    # por diccionario contra una copia del contenedor.
    dd if=/dev/urandom of="$LLAVE" bs=64 count=1 status=none
    chmod 400 "$LLAVE"

    echo "== Formateando el contenedor (LUKS2, argon2id)"
    cryptsetup luksFormat --type luks2 --pbkdf argon2id --batch-mode "$CONTENEDOR" "$LLAVE"

    echo "== Abriendo y formateando el sistema de archivos"
    cryptsetup open --key-file "$LLAVE" "$CONTENEDOR" "$NOMBRE"
    mkfs.ext4 -q -L myfittplan "/dev/mapper/$NOMBRE"

    mkdir -p "$PUNTO"
    mount "/dev/mapper/$NOMBRE" "$PUNTO"

    id -u "$USUARIO" >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin "$USUARIO"
    # 750 y no 755: nginx entra por el grupo para servir con X-Accel-Redirect; nadie más pasa.
    chown -R "$USUARIO:www-data" "$PUNTO"
    chmod 750 "$PUNTO"

    echo "== Dejándolo en crypttab y fstab para que sobreviva a un reinicio"
    grep -q "^$NOMBRE " /etc/crypttab 2>/dev/null || \
        echo "$NOMBRE $CONTENEDOR $LLAVE luks,nofail" >> /etc/crypttab
    grep -q "^/dev/mapper/$NOMBRE " /etc/fstab 2>/dev/null || \
        echo "/dev/mapper/$NOMBRE $PUNTO ext4 defaults,nofail 0 2" >> /etc/fstab

    cat <<AVISO

Listo. El volumen está montado en $PUNTO.

  LM_RUTA_DATOS=$PUNTO   <- ponlo en /etc/myfittplan/config.env

RESPALDA LA LLAVE AHORA, fuera de este servidor:

  sudo base64 $LLAVE

Sin ella el contenedor es irrecuperable. No hay recuperación de contraseña, no hay soporte
que la reponga: es el punto entero de que esté cifrado.

AVISO
}

montar() {
    if [[ ! -e /dev/mapper/$NOMBRE ]]; then
        cryptsetup open --key-file "$LLAVE" "$CONTENEDOR" "$NOMBRE"
    fi
    mountpoint -q "$PUNTO" || mount "/dev/mapper/$NOMBRE" "$PUNTO"
    echo "Montado en $PUNTO"
}

desmontar() {
    mountpoint -q "$PUNTO" && umount "$PUNTO"
    [[ -e /dev/mapper/$NOMBRE ]] && cryptsetup close "$NOMBRE"
    echo "Cerrado. Los datos quedan cifrados en $CONTENEDOR"
}

estado() {
    echo "Contenedor: $CONTENEDOR"
    [[ -e $CONTENEDOR ]] && ls -lh "$CONTENEDOR" | awk '{print "  tamaño:", $5}'
    if mountpoint -q "$PUNTO"; then
        echo "  montado en $PUNTO"
        df -h "$PUNTO" | tail -1 | awk '{print "  usado:", $3, "de", $2, "(" $5 ")"}'
    else
        echo "  NO montado: los datos están cifrados y la aplicación no puede escribir"
    fi
}

exigir_root
case "${1:-estado}" in
    crear)     crear "${2:-20}" ;;
    montar)    montar ;;
    desmontar) desmontar ;;
    estado)    estado ;;
    *) echo "Uso: $0 {crear [GiB]|montar|desmontar|estado}" >&2; exit 1 ;;
esac
