from flask import Blueprint, request, jsonify
from services.auth_service import AuthService

bp = Blueprint("auth", __name__, url_prefix="/auth")

auth_service = AuthService()

@bp.route("/register", methods=["POST"])
def register():
    body = request.get_json()
    result = auth_service.register_user(body["username"], body["email"], body["password"])
    return jsonify(result), 201