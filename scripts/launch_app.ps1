param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$startPostgres = Join-Path $projectRoot "backend\database\scripts\start_postgres.ps1"
$logDirectory = Join-Path $projectRoot ".runtime\logs"
$appUrl = "http://127.0.0.1:8501"

try {
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Die Python-Umgebung der Anwendung wurde nicht gefunden."
    }
    if (-not (Test-Path -LiteralPath (Join-Path $projectRoot ".env"))) {
        throw "Die lokale Konfigurationsdatei .env wurde nicht gefunden."
    }
    if (-not (Test-Path -LiteralPath $startPostgres)) {
        throw "Das PostgreSQL-Startskript wurde nicht gefunden: $startPostgres"
    }

    & $startPostgres
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL konnte nicht gestartet werden."
    }

    Push-Location $projectRoot
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Die Datenbank konnte nicht aktualisiert werden."
        }

        $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue
        if (-not $listener) {
            New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
            Start-Process `
                -FilePath $python `
                -ArgumentList @(
                    "-m", "streamlit", "run", "app.py",
                    "--server.address", "127.0.0.1",
                    "--server.port", "8501",
                    "--server.headless", "true"
                ) `
                -WorkingDirectory $projectRoot `
                -WindowStyle Hidden `
                -RedirectStandardOutput (Join-Path $logDirectory "streamlit.stdout.log") `
                -RedirectStandardError (Join-Path $logDirectory "streamlit.stderr.log")
        }
    }
    finally {
        Pop-Location
    }

    $deadline = (Get-Date).AddSeconds(30)
    do {
        try {
            $response = Invoke-WebRequest -Uri $appUrl -UseBasicParsing -TimeoutSec 2
            if ($response.StatusCode -eq 200) {
                if (-not $NoBrowser) {
                    Start-Process $appUrl
                }
                exit 0
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    } while ((Get-Date) -lt $deadline)

    throw "Die Anwendung wurde gestartet, war aber nach 30 Sekunden noch nicht erreichbar."
}
catch {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        $_.Exception.Message,
        "Kopfschmerz-Tracker",
        [System.Windows.MessageBoxButton]::OK,
        [System.Windows.MessageBoxImage]::Error
    ) | Out-Null
    exit 1
}
