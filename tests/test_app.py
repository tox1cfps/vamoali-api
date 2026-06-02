def test_health_check_is_minimal(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_config_does_not_expose_secrets(client):
    response = client.get("/config")
    assert response.get_json() == {"enable_password_reset": False}


def test_security_headers_are_added(client):
    response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'self'" in response.headers["Content-Security-Policy"]


def test_large_payload_is_rejected(client):
    response = client.post("/auth/register", data="x" * (33 * 1024), content_type="application/json")
    assert response.status_code == 413


def test_unknown_route_returns_json_404(client):
    response = client.get("/missing")
    assert response.status_code == 404
    assert response.get_json()["success"] is False
