from __future__ import annotations

"""Purpose: App-level username/password access control gate.

Usage: Renders a login form before the Streamlit app loads. Validates
credentials against .env settings (AUTH_USERNAME / AUTH_PASSWORD).
"""

import streamlit as st

from backend.config.settings import get_settings
from backend.database.session import create_session_factory


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
            st.session_state["is_admin"] = True
            st.session_state["user_credential_username"] = username
            # Ensure admin profile and credential exist
            try:
                factory = create_session_factory(get_settings().database_url)
                with factory() as session:
                    from backend.services.auth_service import AuthService
                    from backend.services.user_service import UserService
                    auth_service = AuthService(session)
                    user_service = UserService(session)
                    cred = auth_service.repository.get_by_username(username)
                    if cred is None:
                        # Create admin profile and link credential
                        profile = user_service.create(username, None)
                        profile.role = "admin"
                        session.commit()
                        auth_service.create_credentials(profile.id, username, expected_pass)
                    else:
                        profile = user_service.repository.get(cred.user_id)
                        if profile is not None:
                            profile.role = "admin"
                            session.commit()
                        else:
                            profile = user_service.create(username, None)
                            profile.role = "admin"
                            session.commit()
                            auth_service.create_credentials(profile.id, username, expected_pass)
            except Exception:
                pass
            st.rerun()
        else:
            st.error("Invalid credentials")
    st.stop()
    return False
