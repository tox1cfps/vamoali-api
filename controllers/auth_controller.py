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


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    body = request.get_json(silent=True)

    try:
        if not body:
            email = request.args.get("email")
            result = auth_service.request_reset_password(email)
            return jsonify(result), 200

        result = auth_service.reset_password(
            body.get("token"),
            body.get("answer"),
            body.get("new_password"),
            body.get("email"),
        )
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400