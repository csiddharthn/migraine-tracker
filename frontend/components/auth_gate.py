from __future__ import annotations

"""Purpose: App-level username/password access control gate.

Usage: Renders a login form before the Streamlit app loads. Uses the same
username/password fields for both login and sign-up.
"""

import streamlit as st

from backend.config.settings import get_settings
from backend.database.session import create_session_factory
from frontend.config.name_space import cfg
from frontend.i18n import tr


def render_auth_gate() -> bool:
    settings = get_settings()
    if st.session_state.get("authenticated"):
        return True

    st.title("Access Control")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Login"):
            expected_user = settings.auth_username
            expected_pass = settings.auth_password.get_secret_value() if settings.auth_password else ""
            valid = False
            is_admin_login = False
            if username == expected_user and password == expected_pass:
                valid = True
                is_admin_login = True
            else:
                try:
                    factory = create_session_factory(get_settings().database_url)
                    with factory() as session:
                        from backend.services.auth_service import AuthService
                        auth_service = AuthService(session)
                        cred = auth_service.repository.get_by_username(username)
                        if cred is not None and auth_service.verify_password(password, cred.password_hash):
                            valid = True
                            is_admin_login = False
                except Exception:
                    pass
            if valid:
                st.session_state["authenticated"] = True
                st.session_state["is_admin"] = is_admin_login
                st.session_state["user_credential_username"] = username
                try:
                    factory = create_session_factory(get_settings().database_url)
                    with factory() as session:
                        from backend.services.auth_service import AuthService
                        from backend.services.user_service import UserService
                        auth_service = AuthService(session)
                        user_service = UserService(session)
                        if is_admin_login:
                            cred = auth_service.repository.get_by_username(username)
                            if cred is None:
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

    with col2:
        if st.button("Sign up"):
            try:
                factory = create_session_factory(get_settings().database_url)
                with factory() as session:
                    from backend.services.auth_service import AuthService
                    from backend.services.user_service import UserService
                    auth_service = AuthService(session)
                    user_service = UserService(session)
                    if auth_service.repository.get_by_username(username):
                        st.error(tr(cfg, "Benutzername existiert bereits.", "Username already exists."))
                    else:
                        profile = user_service.create(username, None)
                        profile.role = "user"
                        session.commit()
                        auth_service.create_credentials(profile.id, username, password)
                        st.session_state["authenticated"] = True
                        st.session_state["is_admin"] = False
                        st.session_state["user_credential_username"] = username
                        st.rerun()
            except Exception as exc:
                st.error(str(exc))

    st.stop()
    return False
