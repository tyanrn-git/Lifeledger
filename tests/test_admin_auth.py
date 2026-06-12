import pytest

from app.admin.auth import (
    create_session_payload,
    decode_session,
    encode_session,
    verify_password,
)
from app.config import settings


@pytest.fixture(autouse=True)
def admin_password(monkeypatch):
    monkeypatch.setattr(settings, "admin_password", "test-secret-admin")
    monkeypatch.setattr(settings, "telegram_bot_token", "test-bot-token")


def test_verify_password():
    assert verify_password("test-secret-admin") is True
    assert verify_password("wrong") is False


def test_session_roundtrip():
    payload = create_session_payload()
    token = encode_session(payload)
    decoded = decode_session(token)
    assert decoded is not None
    assert decoded["auth"] is True
    assert decoded["csrf"] == payload["csrf"]


def test_session_tampered():
    payload = create_session_payload()
    token = encode_session(payload) + "x"
    assert decode_session(token) is None
