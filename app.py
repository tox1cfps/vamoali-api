from flask import Flask, jsonify
from controllers.auth_controller import bp as auth_bp
from controllers.place_controller import bp as places_bp

app = Flask(__name__)

app.register_blueprint(auth_bp)
app.register_blueprint(places_bp)

@app.errorhandler(404)
def not_found(e):
    return jsonify({"success": False, "message": "Rota não encontrada"}), 404

@app.errorhandler(500)
def internal_error(e):
    return jsonify({"success": False, "message": "Erro interno do servidor"}), 500

@app.route("/")
def ping():
    return "Pong" 


if __name__ == "__main__":
    app.run()