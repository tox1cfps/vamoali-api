from flask import Blueprint, g, jsonify, request

from middleware.auth_middleware import jwt_required
from services.sharing_service import SharingService

bp = Blueprint("sharing", __name__, url_prefix="/sharing")

sharing_service = None


def _get_sharing_service():
    return sharing_service or SharingService()


@bp.route("/group", methods=["GET"])
@jwt_required
def get_group():
    try:
        result = _get_sharing_service().get_group(g.user_id)
        return jsonify(result), 200
    except LookupError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            404,
        )


@bp.route("/group/members/<member_user_id>", methods=["DELETE"])
@jwt_required
def remove_member(member_user_id):
    try:
        result = _get_sharing_service().remove_member(g.user_id, member_user_id)
        return jsonify(result), 200
    except LookupError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            404,
        )
    except PermissionError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            403,
        )
    except ValueError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            400,
        )


@bp.route("/invites", methods=["POST"])
@jwt_required
def create_invite():
    try:
        result = _get_sharing_service().create_invite(g.user_id)
        return jsonify(result), 201
    except LookupError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            404,
        )


@bp.route("/invites/accept", methods=["POST"])
@jwt_required
def accept_invite():
    body = request.get_json(silent=True)

    if not body:
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Body JSON e obrigatorio",
                }
            ),
            400,
        )

    try:
        result = _get_sharing_service().accept_invite(
            g.user_id,
            code=body.get("code"),
            token=body.get("token"),
        )
        return jsonify(result), 200
    except LookupError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            404,
        )
    except ValueError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            400,
        )


@bp.route("/invites/<invite_id>", methods=["DELETE"])
@jwt_required
def revoke_invite(invite_id):
    try:
        result = _get_sharing_service().revoke_invite(g.user_id, invite_id)
        return jsonify(result), 200
    except LookupError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            404,
        )
    except PermissionError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            403,
        )
    except ValueError as error:
        return (
            jsonify(
                {
                    "success": False,
                    "message": str(error),
                }
            ),
            400,
        )
