$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$pgCtl = Join-Path $projectRoot ".runtime\pgsql\bin\pg_ctl.exe"
$data = Join-Path $projectRoot ".runtime\pgdata"

if (-not (Test-Path -LiteralPath $pgCtl)) {
  throw "Die lokale PostgreSQL-Laufzeit wurde nicht gefunden."
}
& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -eq 0) {
  & $pgCtl stop -D $data -m fast -w
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht beendet werden." }
  Write-Host "PostgreSQL wurde beendet."
} else {
  Write-Host "PostgreSQL läuft nicht."
}
