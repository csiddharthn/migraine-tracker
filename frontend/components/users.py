from __future__ import annotations

"""Purpose: User settings component for user selection.

Usage: Renders sidebar user selection and settings. Admin sees all users;
regular users see only themselves. Only admin can create new persons.
"""

from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from backend.models import UserProfile
from backend.services.user_service import DuplicateUserError, UserService
from frontend.config.name_space import cfg
from frontend.i18n import date_input_format, error_message, format_date_value, tr


def render_user_settings(session: Session) -> UserProfile:
    service = UserService(session)
    is_admin = st.session_state.get("is_admin", False)

    with st.sidebar:
        st.subheader(tr(cfg, "Person", "Person"))
        if is_admin:
            users = service.repository.list_users()
            if users:
                names = {user.id: user.display_name for user in users}
                available_ids = list(names)
                pending_id = st.session_state.pop("pending_active_user_id", None)
                if pending_id in available_ids:
                    st.session_state["active_user_id"] = pending_id
                if st.session_state.get("active_user_id") not in available_ids:
                    st.session_state["active_user_id"] = available_ids[0]
                selected_id = st.selectbox(
                    tr(cfg, "Ausgewählte Person", "Selected person"),
                    available_ids,
                    format_func=names.get,
                    key="active_user_id",
                )
                profile = service.repository.get(selected_id)
                if profile is None:
                    st.error(tr(cfg, "Die ausgewählte Person wurde nicht gefunden.", "The selected person was not found."))
                    st.stop()
                st.caption(f"{tr(cfg, 'Erfassungsbeginn', 'Tracking start')}: {format_date_value(cfg, profile.tracking_start_date)}")
                # Admin profile editing
                with st.expander(tr(cfg, "Profil bearbeiten (Admin)", "Edit profile (Admin)")):
                    admin_name = st.text_input(tr(cfg, "Name", "Name"), value=profile.display_name, key="admin_edit_name")
                    admin_role = st.selectbox(tr(cfg, "Rolle", "Role"), ["user", "admin"], index=0 if profile.role == "user" else 1, key="admin_edit_role")
                    if st.button(tr(cfg, "Als Admin speichern", "Save as admin")):
                        profile.display_name = admin_name
                        profile.role = admin_role
                        session.commit()
                        st.success(tr(cfg, "Profil aktualisiert.", "Profile updated."))
                with st.popover(tr(cfg, "Neue Person anlegen", "Add person"), icon=":material/person_add:", width="stretch"):
                    _new_user_form(service, compact=True)
                return profile
            else:
                st.info(tr(cfg, "Noch keine Person vorhanden. Legen Sie zuerst ein Profil an.", "No person exists yet. Create a profile first."))
                _new_user_form(service, compact=False)
                st.stop()
        else:
            # Regular user: find their profile via credential
            from backend.services.auth_service import AuthService
            auth_service = AuthService(session)
            username = st.session_state.get("user_credential_username")
            if username:
                cred = auth_service.repository.get_by_username(username)
                if cred is not None:
                    profile = service.repository.get(cred.user_id)
                    if profile is None:
                        # Create profile if missing (e.g. after sign-up)
                        profile = service.create(username, date.today())
                        profile.role = "user"
                        session.commit()
                    if profile is not None:
                        st.caption(f"{tr(cfg, 'Auswertung für', 'Analysis for')}: {profile.display_name}")
                        # Allow regular user to update their own full name
                        with st.expander(tr(cfg, "Mein Profil bearbeiten", "Edit my profile")):
                            new_name = st.text_input(tr(cfg, "Name", "Name"), value=profile.display_name)
                            if st.button(tr(cfg, "Speichern", "Save")):
                                profile.display_name = new_name
                                session.commit()
                                st.success(tr(cfg, "Profil aktualisiert.", "Profile updated."))
                        return profile
            st.error(tr(cfg, "Benutzerprofil nicht gefunden.", "User profile not found."))
            st.stop()


def selected_user(session: Session) -> UserProfile:
    service = UserService(session)
    is_admin = st.session_state.get("is_admin", False)
    if is_admin:
        users = service.repository.list_users()
        if not users:
            st.error(tr(cfg, "Noch keine Person vorhanden.", "No person exists yet."))
            st.stop()
        available_ids = [user.id for user in users]
        selected_id = st.session_state.get("active_user_id")
        if selected_id not in available_ids:
            selected_id = available_ids[0]
            st.session_state["active_user_id"] = selected_id
        profile = service.repository.get(selected_id)
        if profile is None:
            st.error(tr(cfg, "Die ausgewählte Person wurde nicht gefunden.", "The selected person was not found."))
            st.stop()
        return profile
    else:
        from backend.services.auth_service import AuthService
        auth_service = AuthService(session)
        username = st.session_state.get("user_credential_username")
        if username:
            cred = auth_service.repository.get_by_username(username)
            if cred is not None:
                profile = service.repository.get(cred.user_id)
                if profile is None:
                    profile = service.create(username, date.today())
                    profile.role = "user"
                    session.commit()
                if profile is not None:
                    return profile
        st.error(tr(cfg, "Benutzerprofil nicht gefunden.", "User profile not found."))
        st.stop()


def user_caption(user: UserProfile) -> None:
    st.caption(f"{tr(cfg, 'Auswertung für', 'Analysis for')}: {user.display_name}")


def _new_user_form(service: UserService, *, compact: bool) -> None:
    with st.form(f"new_user_{'compact' if compact else 'initial'}"):
        name = st.text_input(tr(cfg, "Name", "Name"), placeholder=tr(cfg, "Vor- und Nachname", "First and last name"))
        tracking_start = st.date_input(
            tr(cfg, "Erfassungsbeginn", "Tracking start"),
            value=date.today(),
            max_value=date.today(),
            format=date_input_format(cfg, ),
        )
        submitted = st.form_submit_button(tr(cfg, "Person anlegen", "Add person"), type="primary", width="stretch")
    if not submitted:
        return
    try:
        profile = service.create(name, tracking_start)
        profile.role = "user"
        service.session.commit()
        st.session_state["pending_active_user_id"] = profile.id
        st.rerun()
    except (DuplicateUserError, ValueError) as exc:
        service.session.rollback()
        st.error(error_message(cfg, exc))
