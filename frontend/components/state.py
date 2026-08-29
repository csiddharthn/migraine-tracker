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
from typing import Iterator

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker
from streamlit.errors import StreamlitSecretNotFoundError

from backend.config import get_settings
from backend.database.session import create_session_factory


def _database_url() -> str:
    """Resolve the database URL, preferring a launcher-provided process override.

    The local launcher selects the PostgreSQL runtime first and exports the
    matching MIGRAINE_DATABASE_URL into the Streamlit process. That explicit
    runtime-specific value must win over a potentially stale
    .streamlit/secrets.toml entry. Streamlit secrets remain a supported fallback
    for deployments that do not provide an environment variable.
    """
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
