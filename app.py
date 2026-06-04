import json
from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint

from config.settings import ENABLE_PASSWORD_RESET, validate_settings
from controllers.auth_controller import bp as auth_bp
from controllers.internal_jobs_controller import bp as internal_jobs_bp
from controllers.place_controller import bp as places_bp
from controllers.sharing_controller import bp as sharing_bp

validate_settings()

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

app.register_blueprint(auth_bp)
app.register_blueprint(places_bp)
app.register_blueprint(sharing_bp)
app.register_blueprint(internal_jobs_bp)
app.register_blueprint(
    get_swaggerui_blueprint(
        "/docs",
        "/openapi.json",
        config={
            "app_name": "VamoAli API",
            "deepLinking": True,
            "displayRequestDuration": True,
            "persistAuthorization": True,
        },
    ),
    url_prefix="/docs",
)

OPENAPI_SPEC = Path(__file__).with_name("docs") / "openapi.json"


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/migration-health")
def migration_health():
    try:
        from scripts.import_sheets_to_postgres import migration_status

        return jsonify({"matches": migration_status()["matches"]}), 200
    except Exception as exc:
        return jsonify({"matches": False, "error": type(exc).__name__}), 503


@app.get("/config")
def public_config():
    return jsonify({"enable_password_reset": ENABLE_PASSWORD_RESET}), 200


@app.get("/openapi.json")
def openapi_spec():
    with OPENAPI_SPEC.open(encoding="utf-8") as spec_file:
        return jsonify(json.load(spec_file)), 200


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self'; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' https: data:; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "script-src 'self' 'unsafe-inline'; "
        "object-src 'none'; "
        "base-uri 'none'"
    )
    return response


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)


@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Rota não encontrada"}), 404


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "message": "Erro interno do servidor"}), 500


if __name__ == "__main__":
    app.run()
