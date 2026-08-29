param(
  [string]$DownloadUrl = "https://get.enterprisedb.com/postgresql/postgresql-17.10-2-windows-x64-binaries.zip"
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..\..\..")).Path
$runtimeRoot = Join-Path $projectRoot ".runtime"
$pgsqlRoot = Join-Path $runtimeRoot "pgsql"
$dataRoot = Join-Path $runtimeRoot "pgdata"
$archive = Join-Path $runtimeRoot "postgresql-windows-x64-binaries.zip"
$envFile = Join-Path $projectRoot ".env"

New-Item -ItemType Directory -Path $runtimeRoot -Force | Out-Null

if (-not (Test-Path -LiteralPath (Join-Path $pgsqlRoot "bin\postgres.exe"))) {
  Write-Host "PostgreSQL 17 wird aus der offiziellen Windows-Binärdistribution geladen ..."
  Invoke-WebRequest -Uri $DownloadUrl -OutFile $archive -UseBasicParsing
  Write-Host "PostgreSQL wird entpackt ..."
  Expand-Archive -LiteralPath $archive -DestinationPath $runtimeRoot -Force
  Remove-Item -LiteralPath $archive -Force
}

if (-not (Test-Path -LiteralPath $envFile)) {
  $alphabet = "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789"
  $bytes = New-Object byte[] 40
  $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
  try {
    $generator.GetBytes($bytes)
  } finally {
    $generator.Dispose()
  }
  $password = -join ($bytes | ForEach-Object { $alphabet[$_ % $alphabet.Length] })
  @(
    "POSTGRES_PASSWORD=$password"
    "MIGRAINE_DATABASE_URL=postgresql+psycopg://migraine:$password@127.0.0.1:5433/migraine_tracker"
    "MIGRAINE_TEST_DATABASE_URL=postgresql+psycopg://migraine:$password@127.0.0.1:5433/migraine_tracker_test"
    "MIGRAINE_LOG_LEVEL=INFO"
  ) | Set-Content -LiteralPath $envFile -Encoding utf8
  Write-Host "Eine lokale .env-Datei mit zufälligem Passwort wurde erstellt."
} else {
  $passwordLine = Get-Content -LiteralPath $envFile -Encoding utf8 | Where-Object { $_ -match '^POSTGRES_PASSWORD=' } | Select-Object -First 1
  if (-not $passwordLine) { throw "POSTGRES_PASSWORD fehlt in .env." }
  $password = $passwordLine.Substring("POSTGRES_PASSWORD=".Length)
}

$initDb = Join-Path $pgsqlRoot "bin\initdb.exe"
$psql = Join-Path $pgsqlRoot "bin\psql.exe"
if (-not (Test-Path -LiteralPath (Join-Path $dataRoot "PG_VERSION"))) {
  $passwordFile = Join-Path $runtimeRoot "init-password.tmp"
  try {
    Set-Content -LiteralPath $passwordFile -Value $password -Encoding ascii -NoNewline
    & $initDb -D $dataRoot -U postgres -A scram-sha-256 --pwfile=$passwordFile --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw "initdb ist fehlgeschlagen." }
  } finally {
    if (Test-Path -LiteralPath $passwordFile) { Remove-Item -LiteralPath $passwordFile -Force }
  }
}

& (Join-Path $PSScriptRoot "start_postgres.ps1")

$escaped = $password.Replace("'", "''")
$roleSql = @"
DO `$migraine`$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'migraine') THEN
    CREATE ROLE migraine LOGIN;
  END IF;
END
`$migraine`$;
ALTER ROLE migraine WITH LOGIN PASSWORD '$escaped';
"@

$env:PGPASSWORD = $password
try {
  $roleSql | & $psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1
  if ($LASTEXITCODE -ne 0) { throw "Die Anwendungsrolle konnte nicht eingerichtet werden." }
  foreach ($database in @("migraine_tracker", "migraine_tracker_test")) {
    "SELECT format('CREATE DATABASE %I OWNER migraine', '$database') WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$database')\gexec" |
      & $psql -h 127.0.0.1 -p 5433 -U postgres -d postgres -v ON_ERROR_STOP=1
    if ($LASTEXITCODE -ne 0) { throw "Die Datenbank $database konnte nicht eingerichtet werden." }
  }
} finally {
  Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

Write-Host "PostgreSQL 17 und beide Migraine-Tracker-Datenbanken sind eingerichtet."
