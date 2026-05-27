from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from controllers.auth_controller import bp as auth_bp
from controllers.place_controller import bp as places_bp

app = Flask(__name__)
app.url_map.strict_slashes = False
CORS(app)

app.register_blueprint(auth_bp)
app.register_blueprint(places_bp)

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