param(
  [string]$Workbook = (Join-Path $PSScriptRoot "..\..\Kopfschmerzkalender.xlsx"),
  [string]$Annotations = "",
  [Parameter(Mandatory = $true)]
  [string]$User
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$envFile = Join-Path $projectRoot ".env"

if (-not (Test-Path -LiteralPath $python)) {
  throw "Die Python-Umgebung fehlt. Bitte zuerst die Installation aus der README ausführen."
}
if (-not (Test-Path -LiteralPath $envFile)) {
  throw "Die Datei .env fehlt. Bitte .env.example nach .env kopieren und ein lokales Passwort setzen."
}

$workbookPath = (Resolve-Path -LiteralPath $Workbook).Path
$reportPath = Join-Path $projectRoot "artifacts\migration_report.json"
$annotationArgs = @()
if (-not [string]::IsNullOrWhiteSpace($Annotations)) {
  $annotationPath = (Resolve-Path -LiteralPath $Annotations).Path
  $annotationArgs = @("--annotations", $annotationPath)
}

Push-Location $projectRoot
try {
  if (Test-Path -LiteralPath (Join-Path $projectRoot ".runtime\pgsql\bin\postgres.exe")) {
    & (Join-Path $PSScriptRoot "start_postgres.ps1")
  } elseif (Get-Command docker -ErrorAction SilentlyContinue) {
    Write-Host "PostgreSQL wird über Docker gestartet ..."
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw "PostgreSQL konnte nicht gestartet werden." }
  } else {
    throw "Weder die lokale PostgreSQL-Laufzeit noch Docker wurde gefunden. Bitte scripts\install_portable_postgres.ps1 ausführen."
  }

  & $python -m alembic upgrade head
  if ($LASTEXITCODE -ne 0) { throw "Die Datenbankmigration ist fehlgeschlagen." }

  & $python scripts\import_excel.py $workbookPath --user $User @annotationArgs --report $reportPath
  if ($LASTEXITCODE -ne 0) { throw "Der Excel-Import ist fehlgeschlagen." }

  & $python scripts\validate_migration.py $workbookPath --user $User
  if ($LASTEXITCODE -ne 0) { throw "Der Abgleich mit Excel ist fehlgeschlagen." }

  Write-Host "Einrichtung und Abgleich sind abgeschlossen."
} finally {
  Pop-Location
}
