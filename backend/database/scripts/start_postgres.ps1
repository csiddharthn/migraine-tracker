param(
  [switch]$PassThruRuntimeRoot
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
$legacyDatabaseRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path

# Older installations stored the portable PostgreSQL runtime below
# backend\database\.runtime. Prefer that existing database when both the old
# and the newer repository-root runtime exist so upgrades do not silently
# switch the user to a fresh/empty database.
$runtimeCandidates = @(
  (Join-Path $legacyDatabaseRoot ".runtime"),
  (Join-Path $repoRoot ".runtime")
)

$validRuntimeRoots = @()
foreach ($candidate in $runtimeCandidates) {
  $candidatePgCtl = Join-Path $candidate "pgsql\bin\pg_ctl.exe"
  $candidatePgVersion = Join-Path $candidate "pgdata\PG_VERSION"
  if ((Test-Path -LiteralPath $candidatePgCtl) -and (Test-Path -LiteralPath $candidatePgVersion)) {
    $validRuntimeRoots += $candidate
  }
}

$runtimeRoot = $validRuntimeRoots | Select-Object -First 1
if (-not $runtimeRoot) {
  $locations = $runtimeCandidates -join "`n - "
  throw "Die lokale PostgreSQL-Laufzeit oder der Datenordner wurde nicht gefunden. Geprüfte Orte:`n - $locations"
}

# Only one Migraine Tracker cluster may own port 5433. If a second local
# runtime is currently running, stop it before starting the preferred one.
foreach ($otherRuntimeRoot in $validRuntimeRoots) {
  if ([System.IO.Path]::GetFullPath($otherRuntimeRoot).TrimEnd('\') -ieq [System.IO.Path]::GetFullPath($runtimeRoot).TrimEnd('\')) {
    continue
  }
  $otherPgCtl = Join-Path $otherRuntimeRoot "pgsql\bin\pg_ctl.exe"
  $otherData = Join-Path $otherRuntimeRoot "pgdata"
  & $otherPgCtl status -D $otherData *> $null
  if ($LASTEXITCODE -eq 0) {
    Write-Host "Eine zweite lokale PostgreSQL-Instanz des Kopfschmerz-Trackers wird beendet, damit die bestehende Datenbank verwendet werden kann."
    & $otherPgCtl stop -D $otherData -m fast -w | Out-Host
    if ($LASTEXITCODE -ne 0) {
      throw "Die zweite lokale PostgreSQL-Instanz konnte nicht sauber beendet werden: $otherData"
    }
  }
}

$bin = Join-Path $runtimeRoot "pgsql\bin"
$data = Join-Path $runtimeRoot "pgdata"
$log = Join-Path $runtimeRoot "postgresql.log"
$pgCtl = Join-Path $bin "pg_ctl.exe"
$pgIsReady = Join-Path $bin "pg_isready.exe"
$serverOptions = '"-p 5433 -h 127.0.0.1"'

function Test-TrackerPostgresReady {
  & $pgIsReady -h 127.0.0.1 -p 5433 -d postgres *> $null
  return $LASTEXITCODE -eq 0
}

function Start-TrackerPostgres {
  & $pgCtl start -D $data -l $log -o $serverOptions -w | Out-Host
  if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL konnte nicht auf 127.0.0.1:5433 gestartet werden. Siehe $log"
  }
}

& $pgCtl status -D $data *> $null
$clusterRunning = $LASTEXITCODE -eq 0

if ($clusterRunning) {
  if (-not (Test-TrackerPostgresReady)) {
    Write-Host "PostgreSQL läuft bereits, aber nicht auf dem für den Kopfschmerz-Tracker benötigten Port 5433. Die lokale Instanz wird neu gestartet."
    & $pgCtl stop -D $data -m fast -w | Out-Host
    if ($LASTEXITCODE -ne 0) {
      throw "Die laufende lokale PostgreSQL-Instanz konnte nicht sauber beendet werden. Siehe $log"
    }
    Start-TrackerPostgres
  }
} else {
  Start-TrackerPostgres
}

if (-not (Test-TrackerPostgresReady)) {
  throw "PostgreSQL beantwortet weiterhin keine Verbindungen auf Port 5433. Siehe $log"
}
Write-Host "PostgreSQL ist auf 127.0.0.1:5433 bereit. Datenordner: $data"

if ($PassThruRuntimeRoot) {
  Write-Output $runtimeRoot
}
