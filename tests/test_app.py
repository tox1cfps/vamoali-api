def test_health_check_is_minimal(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_config_does_not_expose_secrets(client):
    response = client.get("/config")
    assert response.get_json() == {"enable_password_reset": False}


def test_openapi_spec_documents_api_and_bearer_auth(client):
    response = client.get("/openapi.json")
    spec = response.get_json()

    assert response.status_code == 200
    assert spec["openapi"] == "3.0.3"
    assert "/places/{place_id}" in spec["paths"]
    assert spec["components"]["securitySchemes"]["bearerAuth"]["scheme"] == "bearer"


def test_openapi_spec_covers_all_api_routes(client):
    from app import app

    spec = client.get("/openapi.json").get_json()
    documented_operations = {
        (path, method.upper())
        for path, operations in spec["paths"].items()
        for method in operations
        if method != "parameters"
    }
    api_operations = {
        (rule.rule.rstrip("/").replace("<", "{").replace(">", "}"), method)
        for rule in app.url_map.iter_rules()
        if not rule.rule.startswith(("/docs", "/static"))
        and not rule.rule.startswith("/internal/")
        and rule.rule not in {"/", "/<path:filename>", "/openapi.json"}
        for method in rule.methods - {"HEAD", "OPTIONS"}
    }

    assert api_operations <= documented_operations


def test_swagger_ui_is_available(client):
    response = client.get("/docs/")

    assert response.status_code == 200
    assert b"SwaggerUIBundle" in response.data
    assert b"/openapi.json" in response.data


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
