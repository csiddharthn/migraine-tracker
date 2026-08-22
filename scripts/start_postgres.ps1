$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$bin = Join-Path $projectRoot ".runtime\pgsql\bin"
$data = Join-Path $projectRoot ".runtime\pgdata"
$log = Join-Path $projectRoot ".runtime\postgresql.log"
$pgCtl = Join-Path $bin "pg_ctl.exe"
$pgIsReady = Join-Path $bin "pg_isready.exe"

if (-not (Test-Path -LiteralPath $pgCtl)) {
  throw "Die lokale PostgreSQL-Laufzeit fehlt. Bitte zuerst scripts\install_portable_postgres.ps1 ausführen."
}
if (-not (Test-Path -LiteralPath (Join-Path $data "PG_VERSION"))) {
  throw "Der lokale PostgreSQL-Datenordner ist nicht initialisiert."
}

& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -ne 0) {
  & $pgCtl start -D $data -l $log -o '"-p 5433 -h 127.0.0.1"' -w
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht gestartet werden. Siehe $log" }
}

& $pgIsReady -h 127.0.0.1 -p 5433 -d postgres *> $null
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL beantwortet keine Verbindungen auf Port 5433." }
Write-Host "PostgreSQL ist auf 127.0.0.1:5433 bereit."
