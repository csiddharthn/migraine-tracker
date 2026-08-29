$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"
$startPostgres = Join-Path $projectRoot "backend\database\scripts\start_postgres.ps1"

if (-not (Test-Path -LiteralPath $python)) {
  throw "Die Python-Umgebung fehlt. Bitte zuerst die Installation aus der README ausführen."
}
if (-not (Test-Path -LiteralPath $envFile)) {
  throw "Die Datei .env fehlt. Bitte .env.example nach .env kopieren und ein lokales Passwort setzen."
}

Push-Location $projectRoot
try {
  if ((Test-Path -LiteralPath (Join-Path $projectRoot ".runtime\pgsql\bin\postgres.exe")) -or
      (Test-Path -LiteralPath (Join-Path $projectRoot "backend\database\.runtime\pgsql\bin\postgres.exe"))) {
    & $startPostgres
  } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "PostgreSQL wird über Docker gestartet ..."
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht gestartet werden." }
  } else {
    throw "Weder die lokale PostgreSQL-Laufzeit noch Docker wurde gefunden. Bitte backend/database/scripts/install_portable_postgres.ps1 ausführen."
  }

  & $python -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw "Die Datenbankmigration ist fehlgeschlagen." }

  Write-Host "PostgreSQL ist gestartet und das Datenbankschema ist aktuell."
} finally {
  Pop-Location
}
