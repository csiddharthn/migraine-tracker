param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$startPostgres = Join-Path $projectRoot "backend\database\scripts\start_postgres.ps1"
$repairPostgresCredentials = Join-Path $projectRoot "backend\database\scripts\repair_local_postgres_credentials.ps1"
$repoEnvFile = Join-Path $projectRoot ".env"
$legacyRuntimeRoot = Join-Path $projectRoot "backend\database\.runtime"
$legacyEnvFile = Join-Path $projectRoot "backend\database\.env"
$logDirectory = Join-Path $projectRoot ".runtime\logs"
$appUrl = "http://127.0.0.1:8501"

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
    if (-not $env:POSTGRES_PASSWORD) {
        throw "POSTGRES_PASSWORD fehlt in der Datenbank-Konfiguration: $databaseEnvFile"
    }
}

function Test-LocalDatabaseCredential {
    param(
        [Parameter(Mandatory = $true)][string]$RuntimeRoot
    )

    $psql = Join-Path $RuntimeRoot "pgsql\bin\psql.exe"
    if (-not (Test-Path -LiteralPath $psql)) { return $false }

    $env:PGPASSWORD = $env:POSTGRES_PASSWORD
    try {
        & $psql -h 127.0.0.1 -p 5433 -U migraine -d migraine_tracker -tAc "SELECT 1" *> $null
        return $LASTEXITCODE -eq 0
    }
    finally {
        Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
    }
}

try {
    if (-not (Test-Path -LiteralPath $python)) {
        throw "Die Python-Umgebung der Anwendung wurde nicht gefunden."
    }
    if (-not (Test-Path -LiteralPath $repoEnvFile)) {
        throw "Die lokale Konfigurationsdatei .env wurde nicht gefunden."
    }
    if (-not (Test-Path -LiteralPath $startPostgres)) {
        throw "Das PostgreSQL-Startskript wurde nicht gefunden: $startPostgres"
    }

    $runtimeRoot = (& $startPostgres -PassThruRuntimeRoot | Select-Object -Last 1)
    if (-not $runtimeRoot) {
        throw "Der verwendete PostgreSQL-Datenordner konnte nicht ermittelt werden."
    }
    Import-DatabaseEnvironment -RuntimeRoot $runtimeRoot

    if (-not (Test-LocalDatabaseCredential -RuntimeRoot $runtimeRoot)) {
        if (-not (Test-Path -LiteralPath $repairPostgresCredentials)) {
            throw "Die PostgreSQL-Anmeldung stimmt nicht mit .env überein und das Reparaturskript fehlt."
        }
        Write-Host "Das lokale PostgreSQL-Passwort stimmt nicht mit der aktuellen .env-Datei überein. Es wird einmalig repariert."
        & $repairPostgresCredentials -RuntimeRoot $runtimeRoot
        if ($LASTEXITCODE -ne 0) {
            throw "Die lokale PostgreSQL-Anmeldung konnte nicht repariert werden."
        }
    }

    Push-Location $projectRoot
    try {
        & $python -m alembic upgrade head
        if ($LASTEXITCODE -ne 0) {
            throw "Die Datenbank konnte nicht aktualisiert werden."
        }

        $listener = Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($listener) {
            $existingProcess = Get-Process -Id $listener.OwningProcess -ErrorAction SilentlyContinue
            if ($existingProcess -and $existingProcess.ProcessName -in @("python", "pythonw")) {
                Write-Host "Eine laufende Kopfschmerz-Tracker-Instanz wird neu gestartet, damit die aktuelle Datenbank-Konfiguration verwendet wird."
                Stop-Process -Id $listener.OwningProcess -Force
                Start-Sleep -Milliseconds 500
            } else {
                throw "Port 8501 wird bereits von einem anderen Prozess verwendet. Bitte diesen Prozess beenden und den Kopfschmerz-Tracker erneut starten."
            }
        }

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
