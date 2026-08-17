#!/usr/bin/env bash
#
# Endurecimiento del VPS Ubuntu.
#
# El cifrado del volumen protege el disco apagado. Esto protege el servidor encendido, que es
# el escenario que de verdad ocurre: nadie roba discos de un centro de datos, entran por SSH
# con credenciales adivinadas o por un servicio que no debería estar escuchando.
#
# Es idempotente: se puede volver a correr sin romper nada.
#
#   sudo bash despliegue/endurecer.sh

set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Esto necesita root: usa sudo." >&2; exit 1; }

paso() { echo -e "\n== $1"; }

paso "Actualizaciones de seguridad automáticas"
apt-get update -qq
apt-get install -y -qq unattended-upgrades apt-listchanges
# Solo seguridad y sin reinicios automáticos: un reinicio a media madrugada con el volumen
# cifrado montado por crypttab está bien, pero conviene decidirlo, no descubrirlo.
cat > /etc/apt/apt.conf.d/51myfittplan <<'CONF'
Unattended-Upgrade::Allowed-Origins {
    "${distro_id}:${distro_codename}-security";
};
Unattended-Upgrade::Automatic-Reboot "false";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
CONF
systemctl enable --now unattended-upgrades

paso "Cortafuegos"
apt-get install -y -qq ufw
ufw --force reset >/dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
# MySQL **no** se abre. Escucha en 127.0.0.1 y la aplicación vive en el mismo servidor;
# exponer 3306 a internet es la forma más rápida de perder la base entera.
ufw --force enable
ufw status verbose

paso "SSH"
install -d -m 755 /etc/ssh/sshd_config.d
cat > /etc/ssh/sshd_config.d/60-myfittplan.conf <<'CONF'
# Sin contraseñas: solo llave. Un servidor con datos de salud expuesto a fuerza bruta sobre
# contraseñas es cuestión de tiempo, no de suerte.
PasswordAuthentication no
KbdInteractiveAuthentication no
PermitRootLogin prohibit-password
MaxAuthTries 3
LoginGraceTime 20
X11Forwarding no
AllowAgentForwarding no
CONF

if ! grep -rqE '^\s*ssh-(rsa|ed25519)' /root/.ssh/authorized_keys /home/*/.ssh/authorized_keys 2>/dev/null; then
    echo "   AVISO: no encontré ninguna llave pública autorizada." >&2
    echo "   NO reinicio sshd: te quedarías fuera del servidor." >&2
    echo "   Copia tu llave (ssh-copy-id) y vuelve a correr esto." >&2
else
    sshd -t && systemctl reload ssh
    echo "   sshd recargado: solo llave"
fi

paso "Bloqueo de intentos repetidos"
apt-get install -y -qq fail2ban
cat > /etc/fail2ban/jail.d/myfittplan.conf <<'CONF'
[sshd]
enabled  = true
maxretry = 4
bantime  = 1h
findtime = 10m

[nginx-http-auth]
enabled = true
CONF
systemctl enable --now fail2ban

paso "Permisos de la configuración"
# config.env lleva la contraseña de la base, el secreto de sesión, la contraseña de
# aplicación del correo y la llave privada VAPID. Nadie más que root la lee.
if [[ -f /etc/myfittplan/config.env ]]; then
    chown root:myfittplan /etc/myfittplan/config.env 2>/dev/null || chown root:root /etc/myfittplan/config.env
    chmod 640 /etc/myfittplan/config.env
    ls -l /etc/myfittplan/config.env
fi

paso "MySQL solo en local"
if [[ -d /etc/mysql/mysql.conf.d ]]; then
    cat > /etc/mysql/mysql.conf.d/99-myfittplan.cnf <<'CONF'
[mysqld]
bind-address = 127.0.0.1
local_infile = 0
CONF
    systemctl restart mysql
    ss -lntp | grep -E '3306' || true
fi

paso "Comprobación final"
echo "  ufw:        $(ufw status | head -1)"
echo "  fail2ban:   $(systemctl is-active fail2ban)"
echo "  ssh:        $(sshd -T 2>/dev/null | grep -E '^passwordauthentication' || echo '¿?')"
echo "  volumen:    $(mountpoint -q /var/lib/myfittplan && echo montado || echo 'NO montado')"

cat <<'PENDIENTE'

Lo que este script NO hace y hay que hacer a mano:

  1. Certificado: sudo certbot --nginx -d myfittplan.com -d www.myfittplan.com
     Bloqueante. Sin HTTPS no se manejan datos de salud.

  2. Copiar fuera del servidor la llave del volumen y la del respaldo. Las dos.

  3. Probar la restauración: sudo bash despliegue/respaldo.sh verificar
     Un respaldo que nunca se restauró no es un respaldo.

PENDIENTE
