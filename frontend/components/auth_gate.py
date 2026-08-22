from __future__ import annotations

"""Purpose: App-level username/password access control gate.

Usage: Renders a login form before the Streamlit app loads. Validates
credentials against .env settings (AUTH_USERNAME / AUTH_PASSWORD).
"""

import streamlit as st

from backend.config.settings import get_settings


def render_auth_gate() -> bool:
    settings = get_settings()
    if st.session_state.get("authenticated"):
        return True

    st.title("Access Control")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        expected_user = settings.auth_username
        expected_pass = settings.auth_password.get_secret_value() if settings.auth_password else ""
        if username == expected_user and password == expected_pass:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()
    return False
