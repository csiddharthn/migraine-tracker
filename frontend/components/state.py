from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import streamlit as st
from sqlalchemy.orm import Session, sessionmaker
from streamlit.errors import StreamlitSecretNotFoundError

from backend.config import get_settings
from backend.database.session import create_session_factory


@st.cache_resource(show_spinner=False)
def session_factory() -> sessionmaker[Session]:
    try:
        secret_url = st.secrets.get("MIGRAINE_DATABASE_URL")
    except (FileNotFoundError, StreamlitSecretNotFoundError):
        secret_url = None
    return create_session_factory(str(secret_url or get_settings().database_url))


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
