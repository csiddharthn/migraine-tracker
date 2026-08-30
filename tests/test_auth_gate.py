from types import SimpleNamespace

import pytest
from pydantic import SecretStr

import frontend.components.auth_gate as auth_gate


class _RerunSignal(Exception):
    pass


class _FakeStreamlit:
    def __init__(self, *, username: str = "admin", password: str = "migraine") -> None:
        self.session_state: dict[str, object] = {}
        self._username = username
        self._password = password
        self.errors: list[str] = []
        self.titles: list[str] = []
        self.images: list[str] = []
        self.captions: list[str] = []

    def image(self, image: str, **_kwargs) -> None:
        self.images.append(str(image))

    def title(self, label: str) -> None:
        self.titles.append(label)

    def caption(self, label: str) -> None:
        self.captions.append(label)

    def text_input(self, _label: str, *, type: str | None = None) -> str:
        return self._password if type == "password" else self._username

    def button(self, _label: str, **_kwargs) -> bool:
        return True

    def rerun(self) -> None:
        raise _RerunSignal

    def error(self, message: str) -> None:
        self.errors.append(message)

    def stop(self) -> None:
        raise AssertionError("st.stop() should not be reached in this test")


def _settings():
    return SimpleNamespace(auth_username="admin", auth_password=SecretStr("migraine"))


def test_admin_login_sets_admin_session_state(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(auth_gate, "st", fake_st)
    monkeypatch.setattr(auth_gate, "get_settings", _settings)

    with pytest.raises(_RerunSignal):
        auth_gate.render_auth_gate()

    assert fake_st.session_state["authenticated"] is True
    assert fake_st.session_state["is_admin"] is True
    assert "user_credential_username" not in fake_st.session_state
    assert "active_user_id" not in fake_st.session_state
    assert fake_st.titles == ["Migraine Tracker"]
    assert fake_st.images and fake_st.images[0].endswith("migraine_login_hero.svg")


def test_database_user_login_sets_linked_profile_session(monkeypatch) -> None:
    fake_st = _FakeStreamlit(username="csiddharthn", password="migraine")
    monkeypatch.setattr(auth_gate, "st", fake_st)
    monkeypatch.setattr(auth_gate, "get_settings", _settings)
    monkeypatch.setattr(auth_gate, "_database_user_identity", lambda username, password: ("profile-id", False))

    with pytest.raises(_RerunSignal):
        auth_gate.render_auth_gate()

    assert fake_st.session_state["authenticated"] is True
    assert fake_st.session_state["is_admin"] is False
    assert fake_st.session_state["user_credential_username"] == "csiddharthn"
    assert fake_st.session_state["active_user_id"] == "profile-id"


def test_database_admin_login_keeps_admin_role(monkeypatch) -> None:
    fake_st = _FakeStreamlit(username="database-admin", password="secret")
    monkeypatch.setattr(auth_gate, "st", fake_st)
    monkeypatch.setattr(auth_gate, "get_settings", _settings)
    monkeypatch.setattr(auth_gate, "_database_user_identity", lambda username, password: ("admin-profile-id", True))

    with pytest.raises(_RerunSignal):
        auth_gate.render_auth_gate()

    assert fake_st.session_state["authenticated"] is True
    assert fake_st.session_state["is_admin"] is True
    assert fake_st.session_state["user_credential_username"] == "database-admin"
    assert fake_st.session_state["active_user_id"] == "admin-profile-id"


def test_existing_admin_session_is_repaired(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state["authenticated"] = True
    monkeypatch.setattr(auth_gate, "st", fake_st)
    monkeypatch.setattr(auth_gate, "get_settings", _settings)

    assert auth_gate.render_auth_gate() is True
    assert fake_st.session_state["is_admin"] is True


def test_existing_per_user_session_is_not_promoted(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state.update(
        authenticated=True,
        is_admin=False,
        user_credential_username="regular-user",
    )
    monkeypatch.setattr(auth_gate, "st", fake_st)
    monkeypatch.setattr(auth_gate, "get_settings", _settings)

    assert auth_gate.render_auth_gate() is True
    assert fake_st.session_state["is_admin"] is False


def test_logout_clears_authentication_and_selected_user(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    fake_st.session_state.update(
        authenticated=True,
        is_admin=True,
        user_credential_username="admin-user",
        active_user_id="profile-id",
        pending_active_user_id="pending-id",
        app_language="en",
    )
    monkeypatch.setattr(auth_gate, "st", fake_st)

    with pytest.raises(_RerunSignal):
        auth_gate.render_logout_button()

    for key in auth_gate._AUTH_SESSION_KEYS:
        assert key not in fake_st.session_state
    assert fake_st.session_state["app_language"] == "en"
