from flask import Blueprint, jsonify, request

from config.settings import ENABLE_PASSWORD_RESET
from services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_service = None


def _get_auth_service():
    return auth_service or AuthService()


@bp.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400
    try:
        result = _get_auth_service().register_user(body.get("username"), body.get("email"), body.get("password"))
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True)

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400
    try:
        result = _get_auth_service().login_user(body.get("email"), body.get("password"))
        return jsonify(result), 200
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400


@bp.route("/reset-password", methods=["POST"])
def reset_password():
    if not ENABLE_PASSWORD_RESET:
        return jsonify({"success": False, "message": "Recuperacao de senha indisponivel"}), 404

    body = request.get_json(silent=True) or {}

    try:
        if "token" not in body:
            result = _get_auth_service().request_reset_password(body.get("email") or request.args.get("email"))
            return jsonify(result), 200

        result = _get_auth_service().reset_password(body.get("token"), body.get("new_password"))
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"success": False, "message": str(e)}), 503
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
