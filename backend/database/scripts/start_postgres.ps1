param(
  [switch]$PassThruRuntimeRoot
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
$legacyDatabaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

$runtimeCandidates = @(
  (Join-Path $repoRoot ".runtime"),
  (Join-Path $legacyDatabaseRoot ".runtime")
)

$runtimeRoot = $null
foreach ($candidate in $runtimeCandidates) {
  $candidatePgCtl = Join-Path $candidate "pgsql\bin\pg_ctl.exe"
  $candidatePgVersion = Join-Path $candidate "pgdata\PG_VERSION"
  if ((Test-Path -LiteralPath $candidatePgCtl) -and (Test-Path -LiteralPath $candidatePgVersion)) {
    $runtimeRoot = $candidate
    break
  }
}

if (-not $runtimeRoot) {
  $locations = $runtimeCandidates -join "`n - "
  throw "Die lokale PostgreSQL-Laufzeit oder der Datenordner wurde nicht gefunden. Geprüfte Orte:`n - $locations"
}

$bin = Join-Path $runtimeRoot "pgsql\bin"
$data = Join-Path $runtimeRoot "pgdata"
$log = Join-Path $runtimeRoot "postgresql.log"
$pgCtl = Join-Path $bin "pg_ctl.exe"
$pgIsReady = Join-Path $bin "pg_isready.exe"

& $pgCtl status -D $data *> $null
if ($LASTEXITCODE -ne 0) {
  & $pgCtl start -D $data -l $log -o '"-p 5433 -h 127.0.0.1"' -w | Out-Host
  if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht gestartet werden. Siehe $log" }
}

& $pgIsReady -h 127.0.0.1 -p 5433 -d postgres *> $null
if ($LASTEXITCODE -ne 0) { throw "PostgreSQL beantwortet keine Verbindungen auf Port 5433." }
Write-Host "PostgreSQL ist auf 127.0.0.1:5433 bereit. Datenordner: $data"

if ($PassThruRuntimeRoot) {
  Write-Output $runtimeRoot
}
