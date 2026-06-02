from flask import Flask, jsonify, send_from_directory

from config.settings import ENABLE_PASSWORD_RESET, validate_settings
from controllers.auth_controller import bp as auth_bp
from controllers.place_controller import bp as places_bp

validate_settings()

app = Flask(__name__)
app.url_map.strict_slashes = False
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024

app.register_blueprint(auth_bp)
app.register_blueprint(places_bp)


@app.get("/health")
def health():
    return jsonify({"status": "ok"}), 200


@app.get("/config")
def public_config():
    return jsonify({"enable_password_reset": ENABLE_PASSWORD_RESET}), 200


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
