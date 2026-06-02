from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from services.auth_service import AuthService


@pytest.fixture
def service():
    instance = AuthService.__new__(AuthService)
    instance.user_repo = Mock()
    AuthService._reset_tokens = {}
    return instance


def test_register_normalizes_email_hashes_password_and_returns_token(service, monkeypatch):
    service.user_repo.find_by_email.return_value = None
    service.user_repo.create_user.return_value = {"id": "user-1", "username": "Ana"}
    monkeypatch.setattr("services.auth_service.bcrypt.hashpw", lambda password, salt: b"hash")
    monkeypatch.setattr("services.auth_service.bcrypt.gensalt", lambda: b"salt")
    monkeypatch.setattr(service, "_generate_token", lambda user_id: "jwt")

    result = service.register_user(" Ana ", " ANA@EXAMPLE.COM ", "Strong1!")

    assert result == {"user": {"id": "user-1", "username": "Ana"}, "token": "jwt"}
    service.user_repo.find_by_email.assert_called_once_with("ana@example.com")
    service.user_repo.create_user.assert_called_once_with("Ana", "ana@example.com", "hash")


def test_register_rejects_duplicate_email(service):
    service.user_repo.find_by_email.return_value = {"id": "existing"}
    with pytest.raises(ValueError):
        service.register_user("Ana", "ana@example.com", "Strong1!")


@pytest.mark.parametrize("password", ["short", "lowercase1!", "NoNumber!", "NoSpecial1", "Á" * 71 + "A1!"])
def test_password_strength_rejects_invalid_values(password):
    with pytest.raises(ValueError):
        AuthService._validate_password_strength(password)


def test_login_returns_public_user_and_token(service, monkeypatch):
    service.user_repo.find_by_email.return_value = {
        "id": "user-1",
        "username": "Ana",
        "password_hash": "hash",
    }
    monkeypatch.setattr("services.auth_service.bcrypt.checkpw", lambda password, hashed: True)
    monkeypatch.setattr(service, "_generate_token", lambda user_id: "jwt")

    assert service.login_user("ANA@example.com", "Strong1!") == {
        "user": {"id": "user-1", "username": "Ana"},
        "token": "jwt",
    }


def test_login_rejects_unknown_user(service):
    service.user_repo.find_by_email.return_value = None
    with pytest.raises(ValueError):
        service.login_user("ana@example.com", "Strong1!")


def test_generate_and_decode_token(service):
    token = service._generate_token("user-1")
    payload = service.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["jti"]


def test_request_reset_sends_raw_token_but_stores_only_hash(service, monkeypatch):
    service.user_repo.find_by_email.return_value = {"id": "user-1"}
    send_email = Mock()
    monkeypatch.setattr("services.auth_service.send_password_reset_email", send_email)
    monkeypatch.setattr("services.auth_service.secrets.token_urlsafe", lambda size: "raw-token")

    result = service.request_reset_password(" ANA@example.com ")

    assert result == AuthService.RESET_REQUEST_RESPONSE
    send_email.assert_called_once_with("ana@example.com", "raw-token")
    assert "raw-token" not in service._reset_tokens
    assert AuthService._hash_reset_token("raw-token") in service._reset_tokens


def test_request_reset_returns_same_response_for_unknown_email_without_sending(service, monkeypatch):
    service.user_repo.find_by_email.return_value = None
    send_email = Mock()
    monkeypatch.setattr("services.auth_service.send_password_reset_email", send_email)

    assert service.request_reset_password("unknown@example.com") == AuthService.RESET_REQUEST_RESPONSE
    send_email.assert_not_called()


def test_request_reset_removes_token_when_email_delivery_fails(service, monkeypatch):
    service.user_repo.find_by_email.return_value = {"id": "user-1"}
    monkeypatch.setattr("services.auth_service.send_password_reset_email", Mock(side_effect=RuntimeError("smtp error")))

    with pytest.raises(RuntimeError):
        service.request_reset_password("ana@example.com")
    assert service._reset_tokens == {}


def test_reset_password_updates_hash_and_consumes_token(service, monkeypatch):
    token = "reset-token"
    token_hash = service._hash_reset_token(token)
    service._reset_tokens[token_hash] = {
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "email": "ana@example.com",
    }
    service.user_repo.update_password.return_value = True
    monkeypatch.setattr("services.auth_service.bcrypt.hashpw", lambda password, salt: b"hash")
    monkeypatch.setattr("services.auth_service.bcrypt.gensalt", lambda: b"salt")

    result = service.reset_password(token, "Strong1!")

    assert result["success"] is True
    service.user_repo.update_password.assert_called_once_with("ana@example.com", "hash")
    assert token_hash not in service._reset_tokens


def test_reset_password_rejects_expired_token(service):
    token = "expired"
    service._reset_tokens[service._hash_reset_token(token)] = {
        "expires_at": datetime.now(timezone.utc) - timedelta(seconds=1),
        "email": "ana@example.com",
    }
    with pytest.raises(ValueError):
        service.reset_password(token, "Strong1!")
