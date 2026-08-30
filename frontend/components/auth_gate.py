from __future__ import annotations

"""Purpose: App-level and per-user username/password access control.

Usage: Renders login and self-service sign-up screens before the Streamlit app
loads. The credentials configured via .env (AUTH_USERNAME / AUTH_PASSWORD) are
the app-level admin credentials. Other usernames are verified against the
database-backed user_credentials table and are linked to their corresponding
user profile.
"""

from datetime import date
from pathlib import Path
import re

import streamlit as st
from sqlalchemy.exc import OperationalError

from backend.config.settings import get_settings
from backend.services.auth_service import AuthService
from backend.services.user_service import DuplicateUserError, UserService
from frontend.components.state import database_session
from frontend.config.name_space import cfg
from frontend.i18n import tr


ROOT = Path(__file__).resolve().parents[2]
LOGIN_HERO = ROOT / "assets" / "migraine_login_hero.svg"
_AUTH_SESSION_KEYS = (
    "authenticated",
    "is_admin",
    "user_credential_username",
    "active_user_id",
    "pending_active_user_id",
    "auth_mode",
)


def _t(german: str, english: str) -> str:
    language = st.session_state.get("app_language", "de")
    return tr(cfg, german, english, lang=language)


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


def _validate_registration(
    display_name: str,
    username: str,
    password: str,
    password_confirmation: str,
    *,
    admin_username: str,
) -> tuple[str, str]:
    """Validate sign-up input and return cleaned name and username."""
    cleaned_name = " ".join(display_name.split())
    cleaned_username = username.strip().lower()

    if len(cleaned_name) < 2:
        raise ValueError(_t("Bitte geben Sie Ihren Namen ein.", "Please enter your name."))
    if len(cleaned_username) < 3:
        raise ValueError(_t("Der Benutzername muss mindestens 3 Zeichen lang sein.", "The username must be at least 3 characters long."))
    if len(cleaned_username) > 80:
        raise ValueError(_t("Der Benutzername darf höchstens 80 Zeichen lang sein.", "The username may contain at most 80 characters."))
    if not re.fullmatch(r"[a-z0-9._-]+", cleaned_username):
        raise ValueError(
            _t(
                "Der Benutzername darf nur Buchstaben, Zahlen, Punkt, Unterstrich und Bindestrich enthalten.",
                "The username may contain only letters, numbers, dots, underscores and hyphens.",
            )
        )
    if cleaned_username == admin_username.strip().lower():
        raise ValueError(_t("Dieser Benutzername ist reserviert.", "This username is reserved."))
    if len(password) < 8:
        raise ValueError(_t("Das Passwort muss mindestens 8 Zeichen lang sein.", "The password must be at least 8 characters long."))
    if password != password_confirmation:
        raise ValueError(_t("Die Passwörter stimmen nicht überein.", "The passwords do not match."))

    return cleaned_name, cleaned_username


def _register_user(
    display_name: str,
    username: str,
    password: str,
    password_confirmation: str,
    *,
    admin_username: str,
):
    """Create a regular user profile and linked credential atomically."""
    cleaned_name, cleaned_username = _validate_registration(
        display_name,
        username,
        password,
        password_confirmation,
        admin_username=admin_username,
    )

    with database_session() as session:
        user_service = UserService(session)
        auth_service = AuthService(session)
        try:
            profile = user_service.create(cleaned_name, date.today())
            profile.role = "user"
            auth_service.create_credentials(profile.id, cleaned_username, password)
            session.commit()
            return profile.id, cleaned_username
        except Exception:
            session.rollback()
            raise


def _clear_auth_session() -> None:
    for key in _AUTH_SESSION_KEYS:
        st.session_state.pop(key, None)


def render_logout_button() -> None:
    """Render a sidebar logout action for authenticated sessions."""
    if not st.session_state.get("authenticated"):
        return
    if st.button(
        _t("Abmelden", "Logout"),
        icon=":material/logout:",
        width="stretch",
        key="logout_button",
    ):
        _clear_auth_session()
        st.rerun()


def _render_signup(settings) -> None:
    st.subheader(_t("Konto erstellen", "Create account"))
    st.caption(
        _t(
            "Erstellen Sie ein persönliches Konto. Ihre Einträge bleiben Ihrem Profil zugeordnet.",
            "Create a personal account. Your entries remain linked to your profile.",
        )
    )

    display_name = st.text_input(_t("Name", "Name"), key="signup_display_name")
    username = st.text_input(_t("Benutzername", "Username"), key="signup_username")
    password = st.text_input(_t("Passwort", "Password"), type="password", key="signup_password")
    password_confirmation = st.text_input(
        _t("Passwort bestätigen", "Confirm password"),
        type="password",
        key="signup_password_confirmation",
    )

    back_column, create_column = st.columns(2)
    with back_column:
        if st.button(_t("Zurück zur Anmeldung", "Back to login"), width="stretch"):
            st.session_state["auth_mode"] = "login"
            st.rerun()
    with create_column:
        if st.button(_t("Registrieren", "Sign up"), type="primary", width="stretch"):
            try:
                user_id, cleaned_username = _register_user(
                    display_name,
                    username,
                    password,
                    password_confirmation,
                    admin_username=settings.auth_username,
                )
            except OperationalError:
                st.error(
                    _t(
                        "Die lokale PostgreSQL-Datenbank ist momentan nicht erreichbar. Bitte den Tracker neu starten und erneut versuchen.",
                        "The local PostgreSQL database is currently unavailable. Please restart the tracker and try again.",
                    )
                )
                return
            except (DuplicateUserError, ValueError) as exc:
                message = str(exc)
                if message == "Username already exists.":
                    message = _t("Dieser Benutzername ist bereits vergeben.", "This username is already taken.")
                st.error(message)
                return

            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = False
            st.session_state["user_credential_username"] = cleaned_username
            st.session_state["active_user_id"] = user_id
            st.session_state.pop("auth_mode", None)
            st.rerun()


def render_auth_gate() -> bool:
    settings = get_settings()
    if st.session_state.get("authenticated"):
        # Repair sessions created by the older gate, which marked the user as
        # authenticated but never set the role. App-level credentials are the
        # admin credentials; per-user sessions carry user_credential_username.
        if not st.session_state.get("user_credential_username"):
            st.session_state["is_admin"] = True
        return True

    st.image(str(LOGIN_HERO), width="stretch")
    st.title("Migraine Tracker")
    st.caption(
        _t(
            "Persönliches Kopfschmerz- und Migränetagebuch mit Auswertungen und Datenexport.",
            "Personal headache and migraine diary with analytics and data export.",
        )
    )

    if st.session_state.get("auth_mode") == "signup":
        _render_signup(settings)
        st.stop()
        return False

    username = st.text_input(_t("Benutzername", "Username"))
    password = st.text_input(_t("Passwort", "Password"), type="password")
    if st.button(_t("Anmelden", "Login"), type="primary", width="stretch"):
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
        try:
            identity = _database_user_identity(username, password)
        except OperationalError:
            st.error(
                _t(
                    "Die lokale PostgreSQL-Datenbank ist momentan nicht erreichbar. "
                    "Bitte den Tracker über „Kopfschmerz-Tracker starten.cmd“ starten und anschließend erneut anmelden.",
                    "The local PostgreSQL database is currently unavailable. "
                    "Please start the tracker with ‘Kopfschmerz-Tracker starten.cmd’ and then try logging in again.",
                )
            )
            st.stop()

        if identity is not None:
            user_id, is_admin = identity
            st.session_state["authenticated"] = True
            st.session_state["is_admin"] = is_admin
            st.session_state["user_credential_username"] = username
            st.session_state["active_user_id"] = user_id
            st.rerun()

        st.error(_t("Benutzername oder Passwort ist ungültig.", "Invalid username or password."))

    st.caption(_t("Noch kein Konto?", "Don't have an account yet?"))
    if st.button(_t("Registrieren", "Sign up"), width="stretch", icon=":material/person_add:"):
        st.session_state["auth_mode"] = "signup"
        st.rerun()

    st.stop()
    return False
