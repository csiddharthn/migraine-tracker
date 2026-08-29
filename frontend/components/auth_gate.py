from __future__ import annotations

"""Purpose: App-level username/password access control gate.

Usage: Renders a login form before the Streamlit app loads. The credentials
configured via .env (AUTH_USERNAME / AUTH_PASSWORD) are the app-level admin
credentials, so a successful login must also establish the admin role in
Streamlit session state.
"""

import streamlit as st

from backend.config.settings import get_settings


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
        if username == expected_user and password == expected_pass:
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = True
            st.session_state.pop("user_credential_username", None)
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()
    return False
