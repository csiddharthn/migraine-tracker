from __future__ import annotations

"""Purpose: App-level username/password access control gate.

Usage: Renders a login form before the Streamlit app loads. Validates
credentials against .env settings (AUTH_USERNAME / AUTH_PASSWORD) for admin,
or against user_credentials for regular users. Provides self-registration.
"""

import streamlit as st

from backend.config.settings import get_settings
from backend.services.auth_service import AuthService
from frontend.components.state import database_session
from frontend.config.name_space import cfg
from frontend.i18n import tr


def render_auth_gate() -> bool:
    settings = get_settings()
    if st.session_state.get("authenticated"):
        return True

    st.title(tr(cfg, "Zugangskontrolle", "Access Control"))

    tab_login, tab_register = st.tabs([
        tr(cfg, "Anmelden", "Login"),
        tr(cfg, "Neu registrieren", "Register new user"),
    ])

    with tab_login:
        username = st.text_input(tr(cfg, "Benutzername", "Username"))
        password = st.text_input(tr(cfg, "Passwort", "Password"), type="password")
        if st.button(tr(cfg, "Anmelden", "Login"), type="primary"):
            expected_user = settings.auth_username
            expected_pass = settings.auth_password.get_secret_value() if settings.auth_password else ""
            if username == expected_user and password == expected_pass:
                st.session_state["authenticated"] = True
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                with database_session() as session:
                    auth_service = AuthService(session)
                    if auth_service.verify_credentials(username, password):
                        cred = auth_service.repository.get_by_username(username)
                        if cred is not None:
                            st.session_state["authenticated"] = True
                            st.session_state["is_admin"] = False
                            st.session_state["user_credential_id"] = cred.id
                            st.session_state["user_credential_username"] = username
                            st.rerun()
                        else:
                            st.error(tr(cfg, "Ungültige Anmeldedaten.", "Invalid credentials."))
                    else:
                        st.error(tr(cfg, "Ungültige Anmeldedaten.", "Invalid credentials."))

    with tab_register:
        st.info(tr(cfg, "Neue Benutzer können sich hier registrieren und anschließend einen vollständigen Namen eingeben.", "New users can register here and then enter a full name."))
        reg_username = st.text_input(tr(cfg, "Benutzername wählen", "Choose username"), key="reg_username")
        reg_password = st.text_input(tr(cfg, "Passwort wählen", "Choose password"), type="password", key="reg_password")
        reg_full_name = st.text_input(tr(cfg, "Vollständiger Name", "Full name"), key="reg_full_name")
        if st.button(tr(cfg, "Registrieren", "Register"), type="primary", key="reg_btn"):
            if not reg_username or not reg_password or not reg_full_name:
                st.error(tr(cfg, "Bitte alle Felder ausfüllen.", "Please fill in all fields."))
            else:
                with database_session() as session:
                    from backend.services.user_service import UserService
                    user_service = UserService(session)
                    try:
                        profile = user_service.create(reg_full_name)
                        auth_service = AuthService(session)
                        auth_service.create_credentials(profile.id, reg_username, reg_password)
                        profile.role = "user"
                        session.commit()
                        st.success(tr(cfg, "Registrierung erfolgreich. Bitte anmelden.", "Registration successful. Please log in."))
                    except Exception as exc:
                        session.rollback()
                        st.error(str(exc))

    st.stop()
    return False
