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
if (-not (Test-Path config.env)) {
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
$mysql = (Get-Command mysql -ErrorAction SilentlyContinue)
if (-not $mysql) {
    Write-Warning @"
No encontré el cliente de MySQL en el PATH.

MySQL corre en local igual que en producción, a propósito: SQLite no tiene las vistas por
inquilino ni la variable de sesión en las que se apoya el aislamiento entre coaches, así
que la prueba de fuga —lo único que legalmente no puede fallar— no podría correr.

Instálalo desde https://dev.mysql.com/downloads/installer/ y vuelve a ejecutar esto.
"@
    exit 1
}

$argsMysql = @("-u", $UsuarioMysql)
if ($ClaveMysql) { $argsMysql += "-p$ClaveMysql" }

$sql = "CREATE DATABASE IF NOT EXISTS leanmuscle CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci"
& mysql @argsMysql -e $sql
Write-Host "   base 'leanmuscle' lista"

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

Todo listo. Dos terminales:

  .\.venv\Scripts\uvicorn app.main:app --reload      API en http://127.0.0.1:8000
  cd web; npm run dev                                 Web en http://localhost:5173

Pruebas:

  .\.venv\Scripts\python -m pytest pruebas -q         todo
  .\.venv\Scripts\python -m pytest pruebas/aislamiento -q   la fuga entre coaches

"@ -ForegroundColor Green
