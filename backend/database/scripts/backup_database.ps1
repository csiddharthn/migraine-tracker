param(
  [string]$OutputFile = (Join-Path $PSScriptRoot "..\backups\migraine_tracker_$(Get-Date -Format yyyyMMdd_HHmmss).sql")
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$requestedPath = if ([System.IO.Path]::IsPathRooted($OutputFile)) { $OutputFile } else { Join-Path $projectRoot $OutputFile }
$outputPath = [System.IO.Path]::GetFullPath($requestedPath)
$backupRoot = [System.IO.Path]::GetFullPath((Join-Path $projectRoot "backups"))
$backupPrefix = $backupRoot.TrimEnd([System.IO.Path]::DirectorySeparatorChar) + [System.IO.Path]::DirectorySeparatorChar
if (-not $outputPath.StartsWith($backupPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
  throw "Sicherungen müssen im Projektordner 'backups' gespeichert werden."
}
New-Item -ItemType Directory -Path (Split-Path -Parent $outputPath) -Force | Out-Null
Push-Location $projectRoot
try {
  $portableDump = Join-Path $projectRoot ".runtime\pgsql\bin\pg_dump.exe"
  if (Test-Path -LiteralPath $portableDump) {
    $passwordLine = Get-Content -LiteralPath (Join-Path $projectRoot ".env") -Encoding utf8 | Where-Object { $_ -match '^POSTGRES_PASSWORD=' } | Select-Object -First 1
    if (-not $passwordLine) { throw "POSTGRES_PASSWORD fehlt in .env." }
    $env:PGPASSWORD = $passwordLine.Substring("POSTGRES_PASSWORD=".Length)
    try {
      & $portableDump -h 127.0.0.1 -p 5433 -U migraine -d migraine_tracker --clean --if-exists --file=$outputPath
      if ($LASTEXITCODE -ne 0) { throw "pg_dump ist fehlgeschlagen." }
    } finally {
      Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
  } else {
    docker compose exec -T postgres pg_dump -U migraine -d migraine_tracker --clean --if-exists | Set-Content -LiteralPath $outputPath -Encoding UTF8
  }
  Write-Host "Sicherung erstellt: $outputPath"
} finally {
  Pop-Location
}
