from __future__ import annotations

"""Purpose: Streamlit session state and database session management.

Usage: Provides session_factory and database_session context manager.

Functions available:
- session_factory, database_session

Classes available:
- None

Call hierarchy:
- state.py -> backend.database.session, backend.config
"""

import os
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from urllib.parse import quote

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker
from streamlit.errors import StreamlitSecretNotFoundError

from backend.config import get_settings
from backend.database.session import create_session_factory


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _portable_runtime_root() -> Path | None:
    """Return the bundled PostgreSQL runtime root when this is a local install."""
    candidates = (
        PROJECT_ROOT / ".runtime",
        PROJECT_ROOT / "backend" / "database" / ".runtime",
    )
    for candidate in candidates:
        if (candidate / "pgsql" / "bin" / "pg_ctl.exe").is_file() and (candidate / "pgdata" / "PG_VERSION").is_file():
            return candidate
    return None


def _env_file_value(name: str) -> str | None:
    """Read one simple KEY=VALUE entry from the repository .env file."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.is_file():
        return None
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() != name:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        return value
    return None


def _local_portable_database_url() -> str | None:
    """Build the canonical URL for the bundled Windows PostgreSQL database.

    Local copies can retain a stale MIGRAINE_DATABASE_URL after being moved or
    copied. If the bundled PostgreSQL runtime is present, its fixed local
    address is authoritative and only the password is taken from configuration.
    """
    if _portable_runtime_root() is None:
        return None
    password = os.environ.get("POSTGRES_PASSWORD") or _env_file_value("POSTGRES_PASSWORD")
    if not password:
        return None
    encoded_password = quote(password, safe="")
    return f"postgresql+psycopg://migraine:{encoded_password}@127.0.0.1:5433/migraine_tracker"


def _database_url() -> str:
    """Resolve the database URL, preferring the bundled local database when present.

    The portable Windows install always uses PostgreSQL on 127.0.0.1:5433. Its
    location should win over stale URLs left in a moved/copied .env file, shell
    environment, or Streamlit secrets. Non-portable deployments continue to use
    the normal environment/secrets/settings precedence.
    """
    local_url = _local_portable_database_url()
    if local_url:
        return local_url

    process_url = os.environ.get("MIGRAINE_DATABASE_URL")
    if process_url:
        return process_url.strip()

    try:
        secret_url = st.secrets.get("MIGRAINE_DATABASE_URL")
    except (FileNotFoundError, StreamlitSecretNotFoundError):
        secret_url = None
    if secret_url:
        return str(secret_url).strip()

    return str(get_settings().database_url).strip()


@st.cache_resource(show_spinner=False)
def session_factory() -> sessionmaker[Session]:
    return create_session_factory(_database_url())


@contextmanager
def database_session() -> Iterator[Session]:
    factory = session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def clear_data_cache() -> None:
    st.cache_data.clear()


def groq_api_key() -> str | None:
    try:
        secret_value = st.secrets.get("GROQ_API_KEY")
    except (FileNotFoundError, StreamlitSecretNotFoundError):
        secret_value = None
    if secret_value:
        return str(secret_value).strip() or None
    configured = get_settings().groq_api_key
    return configured.get_secret_value().strip() if configured else None
