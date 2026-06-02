from functools import wraps

import jwt
from flask import g, jsonify, request

from services.auth_service import AuthService


def jwt_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Token não fornecido"}), 401

        token = auth_header.split(" ")[1]

        try:
            payload = AuthService.decode_token(token)
            g.user_id = payload["sub"]
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token Expirado"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Token Inválido"}), 401

        return f(*args, **kwargs)

    return decorated
