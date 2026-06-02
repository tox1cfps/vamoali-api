import jwt
import pytest
from flask import Flask, g, jsonify

from middleware.auth_middleware import jwt_required


@pytest.fixture
def client():
    app = Flask(__name__)

    @app.get("/protected")
    @jwt_required
    def protected():
        return jsonify({"user_id": g.user_id})

    return app.test_client()


def test_missing_token_returns_401(client):
    assert client.get("/protected").status_code == 401


def test_valid_token_sets_current_user(client, monkeypatch):
    monkeypatch.setattr("middleware.auth_middleware.AuthService.decode_token", lambda token: {"sub": "user-1"})
    response = client.get("/protected", headers={"Authorization": "Bearer valid"})
    assert response.get_json() == {"user_id": "user-1"}


@pytest.mark.parametrize("error", [jwt.InvalidTokenError(), jwt.ExpiredSignatureError()])
def test_invalid_or_expired_token_returns_401(client, monkeypatch, error):
    def fail(token):
        raise error

    monkeypatch.setattr("middleware.auth_middleware.AuthService.decode_token", fail)
    assert client.get("/protected", headers={"Authorization": "Bearer invalid"}).status_code == 401
