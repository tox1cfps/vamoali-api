import os

import pytest

os.environ["SHEET_NAME"] = "test-sheet"
os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-characters"
os.environ["FERNET_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["GOOGLE_CREDENTIALS_JSON"] = '{"type": "service_account"}'
os.environ["ENABLE_PASSWORD_RESET"] = "false"


@pytest.fixture
def client():
    from app import app

    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def authenticated_client(client, monkeypatch):
    monkeypatch.setattr("middleware.auth_middleware.AuthService.decode_token", lambda token: {"sub": "user-1"})
    client.environ_base["HTTP_AUTHORIZATION"] = "Bearer valid"
    return client
