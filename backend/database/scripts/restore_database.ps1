param(
  [Parameter(Mandatory = $true)]
  [string]$InputFile
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$inputPath = (Resolve-Path -LiteralPath $InputFile).Path
$backupRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
$backupPrefix = $backupRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if (-not $inputPath.StartsWith($backupPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Wiederherstellungen sind nur aus dem Projektordner 'backups' erlaubt."
}
Push-Location $projectRoot
try {
  $portablePsql = Join-Path $projectRoot ".runtime\pgsql\bin\psql.exe"
  if (Test-Path -LiteralPath $portablePsql) {
    $passwordLine = Get-Content -LiteralPath (Join-Path $projectRoot ".env") -Encoding utf8 | Where-Object { $_ -match '^POSTGRES_PASSWORD=' } | Select-Object -First 1
    if (-not $passwordLine) { throw "POSTGRES_PASSWORD fehlt in .env." }
    $env:PGPASSWORD = $passwordLine.Substring("POSTGRES_PASSWORD=".Length)
    try {
      & $portablePsql -h 127.0.0.1 -p 5433 -U migraine -d migraine_tracker -v ON_ERROR_STOP=1 --file=$inputPath
      if ($LASTEXITCODE -ne 0) { throw "psql ist fehlgeschlagen." }
    } finally {
      Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
  } else {
    Get-Content -LiteralPath $inputPath -Raw -Encoding UTF8 | docker compose exec -T postgres psql -v ON_ERROR_STOP=1 -U migraine -d migraine_tracker
  }
  Write-Host "Sicherung wiederhergestellt: $inputPath"
} finally {
  Pop-Location
}
