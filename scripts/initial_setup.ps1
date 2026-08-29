$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$repoEnvFile = Join-Path $projectRoot ".env"
$startPostgres = Join-Path $projectRoot "backend\database\scripts\start_postgres.ps1"
$legacyRuntimeRoot = Join-Path $projectRoot "backend\database\.runtime"
$legacyEnvFile = Join-Path $projectRoot "backend\database\.env"

function Import-DatabaseEnvironment {
  param(
    [Parameter(Mandatory = $true)][string]$RuntimeRoot
  )

  $databaseEnvFile = $repoEnvFile
  $runtimeFull = [System.IO.Path]::GetFullPath($RuntimeRoot).TrimEnd('\')
  $legacyFull = [System.IO.Path]::GetFullPath($legacyRuntimeRoot).TrimEnd('\')

  if (($runtimeFull -ieq $legacyFull) -and (Test-Path -LiteralPath $legacyEnvFile)) {
    $databaseEnvFile = $legacyEnvFile
    Write-Host "Die bestehende Datenbank unter backend\database\.runtime wird mit ihrer zugehörigen Datenbank-Konfiguration verwendet."
  }

  foreach ($name in @("POSTGRES_PASSWORD", "MIGRAINE_DATABASE_URL", "MIGRAINE_TEST_DATABASE_URL")) {
    $prefix = "$name="
    $line = Get-Content -LiteralPath $databaseEnvFile -Encoding utf8 |
      Where-Object { $_.StartsWith($prefix) } |
      Select-Object -First 1
    if ($line) {
      Set-Item -Path "Env:$name" -Value $line.Substring($prefix.Length)
    }
  }

  if (-not $env:MIGRAINE_DATABASE_URL) {
    throw "MIGRAINE_DATABASE_URL fehlt in der Datenbank-Konfiguration: $databaseEnvFile"
  }
}

if (-not (Test-Path -LiteralPath $python)) {
  throw "Die Python-Umgebung fehlt. Bitte zuerst die Installation aus der README ausführen."
}
if (-not (Test-Path -LiteralPath $repoEnvFile)) {
  throw "Die Datei .env fehlt. Bitte .env.example nach .env kopieren und ein lokales Passwort setzen."
}

Push-Location $projectRoot
try {
  if ((Test-Path -LiteralPath (Join-Path $projectRoot ".runtime\pgsql\bin\postgres.exe")) -or
      (Test-Path -LiteralPath (Join-Path $projectRoot "backend\database\.runtime\pgsql\bin\postgres.exe"))) {
    $runtimeRoot = (& $startPostgres -PassThruRuntimeRoot | Select-Object -Last 1)
    if (-not $runtimeRoot) { throw "Der verwendete PostgreSQL-Datenordner konnte nicht ermittelt werden." }
    Import-DatabaseEnvironment -RuntimeRoot $runtimeRoot
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
