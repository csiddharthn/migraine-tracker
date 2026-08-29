import os
from types import SimpleNamespace

import frontend.components.state as state


def test_database_url_prefers_process_environment(monkeypatch):
    monkeypatch.setenv("MIGRAINE_DATABASE_URL", "postgresql+psycopg://env-user:env-pass@127.0.0.1:5433/env-db")
    monkeypatch.setattr(state, "st", SimpleNamespace(secrets={"MIGRAINE_DATABASE_URL": "postgresql+psycopg://secret-user:secret-pass@127.0.0.1:5433/secret-db"}))
    monkeypatch.setattr(state, "get_settings", lambda: SimpleNamespace(database_url="postgresql+psycopg://settings-user:settings-pass@127.0.0.1:5433/settings-db"))

    assert state._database_url() == "postgresql+psycopg://env-user:env-pass@127.0.0.1:5433/env-db"


def test_database_url_uses_streamlit_secret_when_no_process_override(monkeypatch):
    monkeypatch.delenv("MIGRAINE_DATABASE_URL", raising=False)
    monkeypatch.setattr(state, "st", SimpleNamespace(secrets={"MIGRAINE_DATABASE_URL": "postgresql+psycopg://secret-user:secret-pass@127.0.0.1:5433/secret-db"}))
    monkeypatch.setattr(state, "get_settings", lambda: SimpleNamespace(database_url="postgresql+psycopg://settings-user:settings-pass@127.0.0.1:5433/settings-db"))

    assert state._database_url() == "postgresql+psycopg://secret-user:secret-pass@127.0.0.1:5433/secret-db"


def test_database_url_falls_back_to_settings(monkeypatch):
    monkeypatch.delenv("MIGRAINE_DATABASE_URL", raising=False)
    monkeypatch.setattr(state, "st", SimpleNamespace(secrets={}))
    monkeypatch.setattr(state, "get_settings", lambda: SimpleNamespace(database_url="postgresql+psycopg://settings-user:settings-pass@127.0.0.1:5433/settings-db"))

    assert state._database_url() == "postgresql+psycopg://settings-user:settings-pass@127.0.0.1:5433/settings-db"
