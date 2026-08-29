"""Purpose: Tests for database script file locations.

Usage: Verifies scripts moved to backend/database/scripts and launchers
reference the new location while preserving legacy local database installs.
"""

from pathlib import Path

SCRIPTS_DIR = Path("backend/database/scripts")
EXPECTED_SCRIPT_NAMES = [
    "backup_database.ps1",
    "restore_database.ps1",
    "start_postgres.ps1",
    "stop_postgres.ps1",
    "install_portable_postgres.ps1",
    "repair_local_postgres_credentials.ps1",
]
README_PATH = Path("README.md")
LAUNCHER_PATH = Path("scripts/launch_app.ps1")
INITIAL_SETUP_PATH = Path("scripts/initial_setup.ps1")
INSTALLER_PATH = SCRIPTS_DIR / "install_portable_postgres.ps1"
START_POSTGRES_PATH = SCRIPTS_DIR / "start_postgres.ps1"
REPAIR_CREDENTIALS_PATH = SCRIPTS_DIR / "repair_local_postgres_credentials.ps1"
EXPECTED_REFERENCE = "backend/database/scripts/"
OLD_REFERENCE = "scripts\\backup_database.ps1"


def test_database_scripts_exist():
    for name in EXPECTED_SCRIPT_NAMES:
        assert (SCRIPTS_DIR / name).exists(), f"{name} missing"


def test_references_updated():
    readme = README_PATH.read_text(encoding="utf-8")
    assert EXPECTED_REFERENCE in readme
    assert OLD_REFERENCE not in readme


def test_launcher_starts_postgres_from_backend_database_scripts():
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert 'backend\\database\\scripts\\start_postgres.ps1' in launcher
    assert '..\\database\\scripts\\start_postgres.ps1' not in launcher


def test_initial_setup_uses_backend_database_scripts():
    initial_setup = INITIAL_SETUP_PATH.read_text(encoding="utf-8")
    assert 'backend\\database\\scripts\\start_postgres.ps1' in initial_setup


def test_installer_uses_repository_root_for_runtime_and_env():
    installer = INSTALLER_PATH.read_text(encoding="utf-8")
    assert 'Join-Path $PSScriptRoot "..\\..\\.."' in installer
    assert 'Join-Path $PSScriptRoot ".."' not in installer


def test_start_postgres_can_report_selected_runtime():
    start_script = START_POSTGRES_PATH.read_text(encoding="utf-8")
    assert "[switch]$PassThruRuntimeRoot" in start_script
    assert "Write-Output $runtimeRoot" in start_script


def test_launcher_uses_legacy_env_for_legacy_runtime():
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert 'backend\\database\\.runtime' in launcher
    assert 'backend\\database\\.env' in launcher
    assert "Import-DatabaseEnvironment" in launcher
    assert "MIGRAINE_DATABASE_URL" in launcher


def test_launcher_restarts_existing_streamlit_python_process():
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert "OwningProcess" in launcher
    assert 'ProcessName -in @("python", "pythonw")' in launcher
    assert "Stop-Process -Id $listener.OwningProcess -Force" in launcher


def test_initial_setup_uses_legacy_env_for_legacy_runtime():
    initial_setup = INITIAL_SETUP_PATH.read_text(encoding="utf-8")
    assert 'backend\\database\\.runtime' in initial_setup
    assert 'backend\\database\\.env' in initial_setup
    assert "Import-DatabaseEnvironment" in initial_setup


def test_launcher_repairs_mismatched_local_database_password():
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    assert "Test-LocalDatabaseCredential" in launcher
    assert "repair_local_postgres_credentials.ps1" in launcher
    assert "POSTGRES_PASSWORD" in launcher


def test_credential_repair_preserves_pgdata_and_changes_only_role_password():
    repair = REPAIR_CREDENTIALS_PATH.read_text(encoding="utf-8")
    assert "ALTER ROLE migraine WITH LOGIN PASSWORD" in repair
    assert "CREATE ROLE migraine LOGIN PASSWORD" in repair
    assert "& $postgres --single -D $data postgres" in repair
    assert "DROP DATABASE" not in repair.upper()
    assert "initdb" not in repair.lower()
