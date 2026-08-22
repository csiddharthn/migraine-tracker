import os
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
EXPECTED_REFERENCE = "backend/database/scripts/"
OLD_REFERENCE = "scripts\\backup_database.ps1"


def test_database_scripts_exist():
    for name in EXPECTED_SCRIPT_NAMES:
        assert (SCRIPTS_DIR / name).exists(), f"{name} missing"


def test_references_updated():
    readme = README_PATH.read_text(encoding="utf-8")
    assert EXPECTED_REFERENCE in readme
    assert OLD_REFERENCE not in readme
