"""Purpose: Tests for database script file locations.

Usage: Verifies scripts moved to backend/database/scripts and launchers
reference the new location.
"""

from pathlib import Path

SCRIPTS_DIR = Path("backend/database/scripts")
EXPECTED_SCRIPT_NAMES = [
    "backup_database.ps1",
    "restore_database.ps1",
    "start_postgres.ps1",
    "stop_postgres.ps1",
    "install_portable_postgres.ps1",
]
README_PATH = Path("README.md")
LAUNCHER_PATH = Path("scripts/launch_app.ps1")
INITIAL_SETUP_PATH = Path("scripts/initial_setup.ps1")
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
