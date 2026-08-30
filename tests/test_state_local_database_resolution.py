from __future__ import annotations

from pathlib import Path

from frontend.components import state


def _create_portable_runtime(project_root: Path) -> None:
    pg_ctl = project_root / ".runtime" / "pgsql" / "bin" / "pg_ctl.exe"
    pg_version = project_root / ".runtime" / "pgdata" / "PG_VERSION"
    pg_ctl.parent.mkdir(parents=True)
    pg_version.parent.mkdir(parents=True)
    pg_ctl.write_bytes(b"")
    pg_version.write_text("17", encoding="utf-8")


def test_portable_runtime_uses_canonical_local_url_instead_of_stale_process_url(tmp_path, monkeypatch):
    _create_portable_runtime(tmp_path)
    (tmp_path / ".env").write_text('POSTGRES_PASSWORD="pa ss@word"\n', encoding="utf-8")
    monkeypatch.setattr(state, "PROJECT_ROOT", tmp_path)
    monkeypatch.delenv("POSTGRES_PASSWORD", raising=False)
    monkeypatch.setenv(
        "MIGRAINE_DATABASE_URL",
        "postgresql+psycopg://migraine:old@192.0.2.10:5432/migraine_tracker",
    )

    assert state._database_url() == (
        "postgresql+psycopg://migraine:pa%20ss%40word@127.0.0.1:5433/migraine_tracker"
    )


def test_non_portable_install_keeps_explicit_process_database_url(tmp_path, monkeypatch):
    monkeypatch.setattr(state, "PROJECT_ROOT", tmp_path)
    expected = "postgresql+psycopg://user:password@database.example:5432/migraine_tracker"
    monkeypatch.setenv("MIGRAINE_DATABASE_URL", expected)

    assert state._database_url() == expected
