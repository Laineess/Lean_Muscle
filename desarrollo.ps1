# Levanta el entorno de desarrollo completo en un comando.
#
#   .\desarrollo.ps1              prepara todo y deja la base lista
#   .\desarrollo.ps1 -Reiniciar   borra la base y la vuelve a sembrar
#
# Usa MySQL en local igual que en producción: lo que pruebas es lo que despliegas, y la
# prueba de fuga entre coaches solo corre contra MySQL.

param(
    [switch]$Reiniciar,
    [string]$UsuarioMysql = "root",
    [string]$ClaveMysql = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Paso($texto) { Write-Host "`n== $texto" -ForegroundColor Cyan }

# --- Python -----------------------------------------------------------------
Paso "Entorno de Python"
if (-not (Test-Path .venv)) {
    python -m venv .venv
    Write-Host "   entorno virtual creado"
}
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\.venv\Scripts\python.exe -m pip install --quiet -r requirements-dev.txt
Write-Host "   dependencias al día"

# --- Configuración ----------------------------------------------------------
Paso "Configuración"

# Se aceptan los dos nombres y **el último de la lista gana** (ver `app/config.py`), así que
# crear `config.env` cuando ya hay un `.env` con valores reales lo taparía en silencio con
# los marcadores de la plantilla. Es un fallo que se manifiesta como «acceso denegado» sin
# que nada haya cambiado en la base.
if ((Test-Path .env) -and -not (Test-Path config.env)) {
    Write-Host "   .env ya existe, no creo config.env: taparía tus valores reales"
} elseif (-not (Test-Path config.env)) {
    Copy-Item config.env.example config.env
    $secreto = & .\.venv\Scripts\python.exe -c "import secrets;print(secrets.token_urlsafe(64))"
    (Get-Content config.env) -replace 'LM_SECRETO_SESION=.*', "LM_SECRETO_SESION=$secreto" |
        Set-Content config.env -Encoding utf8
    Write-Host "   config.env creado con un secreto de sesión nuevo"
    Write-Warning "Revisa LM_BD_URL en config.env antes de seguir."
} else {
    Write-Host "   config.env ya existe, no se toca"
}

# --- Base de datos ----------------------------------------------------------
Paso "Base de datos"

# El instalador de MySQL para Windows no agrega su `bin` al PATH, así que se busca donde
# suele quedar antes de rendirse. Es la piedra con la que tropieza todo el mundo la primera
# vez, y el mensaje de error no dice nada útil.
$mysqlExe = (Get-Command mysql -ErrorAction SilentlyContinue).Source
if (-not $mysqlExe) {
    $candidatos = Get-ChildItem "C:\Program Files\MySQL\MySQL Server *\bin\mysql.exe" -ErrorAction SilentlyContinue
    if ($candidatos) { $mysqlExe = $candidatos[0].FullName }
}
if (-not $mysqlExe) {
    Write-Warning @"
No encontré el cliente de MySQL, ni en el PATH ni en C:\Program Files\MySQL.

MySQL corre en local igual que en producción, a propósito: SQLite no tiene las vistas por
inquilino ni la variable de sesión en las que se apoya el aislamiento entre coaches, así
que la prueba de fuga —lo único que legalmente no puede fallar— no podría correr.

Instálalo desde https://dev.mysql.com/downloads/installer/ y vuelve a ejecutar esto.
"@
    exit 1
}
Write-Host "   cliente: $mysqlExe"

# Usuario, clave y base salen de LM_BD_URL, que es la fuente de verdad. Escribirlos otra vez
# aquí garantizaría que un día dejaran de coincidir y nadie supiera por qué no conecta.
$config = & .\.venv\Scripts\python.exe -c @"
from urllib.parse import urlsplit
from app.config import ajustes
u = urlsplit(ajustes().bd_url)
print(u.username or 'root')
print(u.password or '')
print((u.path.lstrip('/').split('?')[0]) or 'leanmuscle')
"@
$bdUsuario, $bdClave, $bdNombre = $config

$argsMysql = @("-u", $UsuarioMysql)
if ($ClaveMysql) { $argsMysql += "-p$ClaveMysql" }

# Se crean base y usuario en una sola pasada. El GRANT va solo sobre esa base: la cuenta de
# la aplicación no tiene por qué poder tocar `mysql.user` ni ninguna otra base del servidor.
$sql = @"
CREATE DATABASE IF NOT EXISTS ``$bdNombre`` CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER IF NOT EXISTS '$bdUsuario'@'localhost' IDENTIFIED BY '$bdClave';
CREATE USER IF NOT EXISTS '$bdUsuario'@'127.0.0.1' IDENTIFIED BY '$bdClave';
ALTER USER '$bdUsuario'@'localhost' IDENTIFIED BY '$bdClave';
ALTER USER '$bdUsuario'@'127.0.0.1' IDENTIFIED BY '$bdClave';
GRANT ALL PRIVILEGES ON ``$bdNombre``.* TO '$bdUsuario'@'localhost';
GRANT ALL PRIVILEGES ON ``$bdNombre``.* TO '$bdUsuario'@'127.0.0.1';
FLUSH PRIVILEGES;
"@

& $mysqlExe @argsMysql -e $sql
if ($LASTEXITCODE -ne 0) {
    Write-Warning @"
MySQL rechazó la conexión como '$UsuarioMysql'.

Si tu root tiene contraseña, pásala:
    .\desarrollo.ps1 -ClaveMysql 'tu-clave-de-root'
"@
    exit 1
}
Write-Host "   base '$bdNombre' y usuario '$bdUsuario' listos"

# Comprobación real: que la aplicación conecte con SUS credenciales, no con las de root.
& .\.venv\Scripts\python.exe -c "from app.datos.alcance import motor; motor().connect()"
if ($LASTEXITCODE -ne 0) {
    Write-Warning "La base existe pero la aplicación no conecta. Revisa LM_BD_URL."
    exit 1
}
Write-Host "   la aplicación conecta con sus propias credenciales"

Paso "Migraciones"
& .\.venv\Scripts\alembic.exe upgrade head

Paso "Semilla"
if ($Reiniciar) {
    & .\.venv\Scripts\python.exe -m app.semilla --reiniciar
} else {
    & .\.venv\Scripts\python.exe -m app.semilla
}

# --- Frontend ---------------------------------------------------------------
Paso "Frontend"
Set-Location web
if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund }
Write-Host "   dependencias al día"
Set-Location $PSScriptRoot

# --- Listo ------------------------------------------------------------------
Write-Host @"

Todo listo. Hacen falta DOS terminales, una para cada proceso:

  Terminal 1   .\.venv\Scripts\uvicorn app.main:app --reload
               API en http://127.0.0.1:8000

  Terminal 2   cd web; npm run dev
               Abre http://localhost:5173

La web sola no basta: Vite manda todo lo que empiece por /api al 8000. Si ves
'ECONNREFUSED 127.0.0.1:8000' en la consola, es que falta la terminal 1.

Cuentas de prueba, todas con la contraseña Demo1234! :

  mariana@leanmuscle.mx     coach de LeanMuscle
  regina@reginafit.mx       segunda coach, para ver que no se filtran datos entre ellas
  admin@myprogressplan.com  superadmin de la plataforma

Las alumnas de la semilla entran con su propio correo y la misma contraseña.

Pruebas:

  .\.venv\Scripts\python -m pytest pruebas -q               todo
  .\.venv\Scripts\python -m pytest pruebas/aislamiento -q   la fuga entre coaches

"@ -ForegroundColor Green
