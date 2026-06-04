from unittest.mock import Mock

import pytest

from services.auth_service import AuthService


@pytest.fixture
def service():
    instance = AuthService.__new__(AuthService)
    instance.user_repo = Mock()
    instance.reset_repo = Mock()
    instance.email_job_repo = Mock()
    instance.login_cache = Mock()
    instance.login_cache.get.return_value = None
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
    service.email_job_repo.enqueue.assert_called_once()


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
    service.login_cache.get.assert_called_once_with("login:user:ana@example.com")
    service.login_cache.set.assert_called_once_with(
        "login:user:ana@example.com",
        {
            "id": "user-1",
            "username": "Ana",
            "password_hash": "hash",
        },
        900,
    )


def test_login_uses_cached_user_without_repository_lookup(service, monkeypatch):
    service.login_cache.get.return_value = {
        "id": "user-1",
        "username": "Ana",
        "password_hash": "hash",
    }
    monkeypatch.setattr("services.auth_service.bcrypt.checkpw", lambda password, hashed: True)
    monkeypatch.setattr(service, "_generate_token", lambda user_id: "jwt")

    result = service.login_user("ana@example.com", "Strong1!")

    assert result == {"user": {"id": "user-1", "username": "Ana"}, "token": "jwt"}
    service.user_repo.find_by_email.assert_not_called()
    service.login_cache.set.assert_not_called()


def test_login_rejects_unknown_user(service):
    service.user_repo.find_by_email.return_value = None
    with pytest.raises(ValueError):
        service.login_user("ana@example.com", "Strong1!")


def test_generate_and_decode_token(service):
    token = service._generate_token("user-1")
    payload = service.decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["jti"]


def test_request_reset_queues_raw_token_but_persists_only_hash(service, monkeypatch):
    service.user_repo.find_by_email.return_value = {"id": "user-1", "email": "ana@example.com"}
    monkeypatch.setattr("services.auth_service.secrets.token_urlsafe", lambda size: "raw-token")

    result = service.request_reset_password(" ANA@example.com ")

    assert result == AuthService.RESET_REQUEST_RESPONSE
    service.reset_repo.create.assert_called_once()
    assert service.reset_repo.create.call_args.args[0] != "raw-token"
    service.email_job_repo.enqueue.assert_called_once_with("password_reset", "ana@example.com", {"token": "raw-token"})


def test_request_reset_returns_same_response_for_unknown_email_without_sending(service, monkeypatch):
    service.user_repo.find_by_email.return_value = None
    assert service.request_reset_password("unknown@example.com") == AuthService.RESET_REQUEST_RESPONSE
    service.email_job_repo.enqueue.assert_not_called()


def test_reset_password_updates_hash_and_consumes_token(service, monkeypatch):
    token = "reset-token"
    token_hash = service._hash_reset_token(token)
    service.reset_repo.find_valid.return_value = {"user_id": "user-1"}
    service.user_repo.find_by_id.return_value = {"id": "user-1", "email": "ana@example.com"}
    service.user_repo.update_password.return_value = True
    monkeypatch.setattr("services.auth_service.bcrypt.hashpw", lambda password, salt: b"hash")
    monkeypatch.setattr("services.auth_service.bcrypt.gensalt", lambda: b"salt")

    result = service.reset_password(token, "Strong1!")

    assert result["success"] is True
    service.user_repo.update_password.assert_called_once_with("ana@example.com", "hash")
    service.login_cache.delete.assert_called_once_with("login:user:ana@example.com")
    service.reset_repo.consume.assert_called_once_with(token_hash)


def test_reset_password_rejects_expired_token(service):
    token = "expired"
    service.reset_repo.find_valid.return_value = None
    with pytest.raises(ValueError):
        service.reset_password(token, "Strong1!")
