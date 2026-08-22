import os
from pathlib import Path

SCRIPTS_DIR = Path("backend/database/scripts")
EXPECTED = [
    "backup_database.ps1",
    "restore_database.ps1",
    "start_postgres.ps1",
    "stop_postgres.ps1",
    "install_portable_postgres.ps1",
]


def test_database_scripts_exist():
    for name in EXPECTED:
        assert (SCRIPTS_DIR / name).exists(), f"{name} missing"


def test_references_updated():
    readme = Path("README.md").read_text(encoding="utf-8")
    assert "backend/database/scripts/" in readme
    assert "scripts\\backup_database.ps1" not in readme
