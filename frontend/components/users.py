from __future__ import annotations

from datetime import date

import streamlit as st
from sqlalchemy.orm import Session

from backend.models import UserProfile
from backend.services.user_service import DuplicateUserError, UserService
from frontend.i18n import date_input_format, error_message, format_date_value, tr


def render_user_settings(session: Session) -> UserProfile:
    service = UserService(session)
    users = service.repository.list_users()
    with st.sidebar:
        st.subheader(tr("Person", "Person"))
        if users:
            names = {user.id: user.display_name for user in users}
            available_ids = list(names)
            pending_id = st.session_state.pop("pending_active_user_id", None)
            if pending_id in available_ids:
                st.session_state["active_user_id"] = pending_id
            if st.session_state.get("active_user_id") not in available_ids:
                st.session_state["active_user_id"] = available_ids[0]
            selected_id = st.selectbox(
                tr("Ausgewählte Person", "Selected person"),
                available_ids,
                format_func=names.get,
                key="active_user_id",
            )
            profile = service.repository.get(selected_id)
            if profile is None:
                st.error(tr("Die ausgewählte Person wurde nicht gefunden.", "The selected person was not found."))
                st.stop()
            st.caption(f"{tr('Erfassungsbeginn', 'Tracking start')}: {format_date_value(profile.tracking_start_date)}")
            with st.popover(tr("Neue Person anlegen", "Add person"), icon=":material/person_add:", width="stretch"):
                _new_user_form(service, compact=True)
            return profile

        st.info(tr("Noch keine Person vorhanden. Legen Sie zuerst ein Profil an.", "No person exists yet. Create a profile first."))
        _new_user_form(service, compact=False)
    st.stop()


def selected_user(session: Session) -> UserProfile:
    service = UserService(session)
    users = service.repository.list_users()
    if not users:
        st.error(tr("Noch keine Person vorhanden.", "No person exists yet."))
        st.stop()

    available_ids = [user.id for user in users]
    selected_id = st.session_state.get("active_user_id")
    if selected_id not in available_ids:
        selected_id = available_ids[0]
        st.session_state["active_user_id"] = selected_id
    profile = service.repository.get(selected_id)
    if profile is None:
        st.error(tr("Die ausgewählte Person wurde nicht gefunden.", "The selected person was not found."))
        st.stop()
    return profile


def user_caption(user: UserProfile) -> None:
    st.caption(f"{tr('Auswertung für', 'Analysis for')}: {user.display_name}")


def _new_user_form(service: UserService, *, compact: bool) -> None:
    with st.form(f"new_user_{'compact' if compact else 'initial'}"):
        name = st.text_input(tr("Name", "Name"), placeholder=tr("Vor- und Nachname", "First and last name"))
        tracking_start = st.date_input(
            tr("Erfassungsbeginn", "Tracking start"),
            value=date.today(),
            max_value=date.today(),
            format=date_input_format(),
        )
        submitted = st.form_submit_button(tr("Person anlegen", "Add person"), type="primary", width="stretch")
    if not submitted:
        return
    try:
        profile = service.create(name, tracking_start)
        service.session.commit()
        st.session_state["pending_active_user_id"] = profile.id
        st.rerun()
    except (DuplicateUserError, ValueError) as exc:
        service.session.rollback()
        st.error(error_message(exc))
