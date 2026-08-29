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

    def title(self, _label: str) -> None:
        pass

    def text_input(self, label: str, *, type: str | None = None) -> str:
        del type
        return self._username if label == "Username" else self._password

    def button(self, _label: str) -> bool:
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
