param(
  [Parameter(Mandatory = $true)][string]$RuntimeRoot
)

$ErrorActionPreference = "Stop"

if (-not $env:POSTGRES_PASSWORD) {
  throw "POSTGRES_PASSWORD ist nicht gesetzt; die Datenbank-Zugangsdaten können nicht repariert werden."
}

$bin = Join-Path $RuntimeRoot "pgsql\bin"
$data = Join-Path $RuntimeRoot "pgdata"
$pgCtl = Join-Path $bin "pg_ctl.exe"
$postgres = Join-Path $bin "postgres.exe"
$psql = Join-Path $bin "psql.exe"

foreach ($path in @($pgCtl, $postgres, $psql, (Join-Path $data "PG_VERSION"))) {
  if (-not (Test-Path -LiteralPath $path)) {
    throw "Erforderliche PostgreSQL-Datei fehlt: $path"
  }
}

$wasRunning = $false
& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -eq 0) {
  $wasRunning = $true
  & $pgCtl stop -D $data -m fast -w | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte für die Zugangsdaten-Reparatur nicht gestoppt werden." }
}

try {
  $escapedPassword = $env:POSTGRES_PASSWORD.Replace("'", "''")
  $sql = @"
DO `$repair`$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'migraine') THEN
    ALTER ROLE migraine WITH LOGIN PASSWORD '$escapedPassword';
  ELSE
    CREATE ROLE migraine LOGIN PASSWORD '$escapedPassword';
  END IF;
END
`$repair`$;
"@

  $sql | & $postgres --single -D $data postgres
  if ($LASTEXITCODE -ne 0) {
    throw "Das Passwort der PostgreSQL-Rolle 'migraine' konnte nicht repariert werden."
  }
}
finally {
  if ($wasRunning) {
    & $pgCtl start -D $data -l (Join-Path $RuntimeRoot "postgresql.log") -o '\"-p 5433 -h 127.0.0.1\"' -w | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nach der Zugangsdaten-Reparatur nicht neu gestartet werden." }
  }
}

$env:PGPASSWORD = $env:POSTGRES_PASSWORD
try {
  & $psql -h 127.0.0.1 -p 5433 -U migraine -d migraine_tracker -tAc "SELECT 1" *> $null
  if ($LASTEXITCODE -ne 0) {
    throw "Die PostgreSQL-Zugangsdaten wurden geändert, aber die Anmeldung als 'migraine' funktioniert weiterhin nicht."
  }
}
finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "Die lokale PostgreSQL-Anmeldung wurde repariert. Vorhandene Daten wurden nicht verändert."
