from __future__ import annotations

"""Purpose: App-level and per-user username/password access control.

Usage: Renders a login form before the Streamlit app loads. The credentials
configured via .env (AUTH_USERNAME / AUTH_PASSWORD) are the app-level admin
credentials. Other usernames are verified against the database-backed
user_credentials table and are linked to their corresponding user profile.
"""

import streamlit as st

from backend.config.settings import get_settings
from backend.services.auth_service import AuthService
from frontend.components.state import database_session


def _database_user_identity(username: str, password: str):
    """Return (user_id, is_admin) for valid database credentials, else None."""
    with database_session() as session:
        auth_service = AuthService(session)
        credential = auth_service.repository.get_by_username(username)
        if credential is None:
            return None
        if not auth_service.verify_password(password, credential.password_hash):
            return None
        profile = credential.user
        return credential.user_id, getattr(profile, "role", "user") == "admin"


def render_auth_gate() -> bool:
    settings = get_settings()
    if st.session_state.get("authenticated"):
        # Repair sessions created by the older gate, which marked the user as
        # authenticated but never set the role. App-level credentials are the
        # admin credentials; per-user sessions carry user_credential_username.
        if not st.session_state.get("user_credential_username"):
            st.session_state["is_admin"] = True
        return True

    st.title("Access Control")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        expected_user = settings.auth_username
        expected_pass = settings.auth_password.get_secret_value() if settings.auth_password else ""

        # App-level credentials always grant administrator access.
        if username == expected_user and password == expected_pass:
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = True
            st.session_state.pop("user_credential_username", None)
            st.session_state.pop("active_user_id", None)
            st.rerun()

        # All other accounts are authenticated against user_credentials and
        # remain linked to the user_profile referenced by that credential.
        identity = _database_user_identity(username, password)
        if identity is not None:
            user_id, is_admin = identity
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = is_admin
            st.session_state["user_credential_username"] = username
            st.session_state["active_user_id"] = user_id
            st.rerun()

        st.error("Invalid credentials")
    st.stop()
    return False
