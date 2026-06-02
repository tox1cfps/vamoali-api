from unittest.mock import Mock

import controllers.auth_controller as controller


def test_register_returns_created_payload(client, monkeypatch):
    service = Mock()
    service.register_user.return_value = {"user": {"id": "user-1"}, "token": "jwt"}
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post(
        "/auth/register", json={"username": "Ana", "email": "ana@example.com", "password": "Strong1!"}
    )

    assert response.status_code == 201
    assert response.get_json()["token"] == "jwt"


def test_login_rejects_missing_body(client):
    response = client.post("/auth/login", json=None)
    assert response.status_code == 400


def test_login_converts_service_validation_error_to_400(client, monkeypatch):
    service = Mock()
    service.login_user.side_effect = ValueError("invalid")
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "wrong"})

    assert response.status_code == 400
    assert response.get_json()["message"] == "invalid"


def test_login_returns_service_payload(client, monkeypatch):
    service = Mock()
    service.login_user.return_value = {"user": {"id": "user-1"}, "token": "jwt"}
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post("/auth/login", json={"email": "ana@example.com", "password": "Strong1!"})

    assert response.status_code == 200
    assert response.get_json()["token"] == "jwt"


def test_reset_is_hidden_when_password_reset_is_disabled(client):
    assert client.post("/auth/reset-password?email=ana@example.com").status_code == 404


def test_reset_request_sends_generic_response(client, monkeypatch):
    service = Mock()
    service.request_reset_password.return_value = {"success": True, "message": "generic"}
    monkeypatch.setattr(controller, "ENABLE_PASSWORD_RESET", True)
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post("/auth/reset-password", json={"email": "ana@example.com"})

    assert response.status_code == 200
    assert response.get_json() == {"success": True, "message": "generic"}
    service.request_reset_password.assert_called_once_with("ana@example.com")


def test_reset_confirmation_uses_token_and_new_password(client, monkeypatch):
    service = Mock()
    service.reset_password.return_value = {"success": True}
    monkeypatch.setattr(controller, "ENABLE_PASSWORD_RESET", True)
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post(
        "/auth/reset-password",
        json={"token": "reset", "new_password": "Strong1!"},
    )

    assert response.status_code == 200
    assert response.get_json() == {"success": True}
    service.reset_password.assert_called_once_with("reset", "Strong1!")


def test_reset_request_returns_503_when_email_delivery_fails(client, monkeypatch):
    service = Mock()
    service.request_reset_password.side_effect = RuntimeError("smtp unavailable")
    monkeypatch.setattr(controller, "ENABLE_PASSWORD_RESET", True)
    monkeypatch.setattr(controller, "auth_service", service)

    response = client.post("/auth/reset-password", json={"email": "ana@example.com"})

    assert response.status_code == 503
