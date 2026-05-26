from flask import Blueprint, request, jsonify
from services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_service = AuthService()

@bp.route("/register", methods=["POST"])
def register():
    body = request.get_json()

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400
    try:
        result = auth_service.register_user(body.get("username"), body.get("email"), body.get("password"))
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400

@bp.route("/login", methods=["POST"])
def login():
    body = request.get_json()

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400
    try:
        result = auth_service.login_user(body.get("email"), body.get("password"))
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400