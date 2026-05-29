from flask import Blueprint, request, jsonify, g
from services.place_service import PlaceService
from middleware.auth_middleware import jwt_required

bp = Blueprint("places", __name__, url_prefix="/places")

place_service = PlaceService()

@bp.route("/", methods=["GET"])
@jwt_required
def get_places():
    user_id = g.user_id

    places = place_service.get_places(user_id)

    return jsonify(places), 200

@bp.route("/", methods=["POST"])
@jwt_required
def create_place():
    user_id = g.user_id
    body = request.get_json()
    
    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400

    try:
        result = place_service.create_place(user_id, body.get("name"), body.get("maps_url"), body.get("category"), body.get("photo_url", ""))
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"success":False, "message": str(e)}), 400
    
@bp.route("/<place_id>", methods=["DELETE"])
@jwt_required
def delete_place(place_id):
    user_id = g.user_id

    try:
        place_service.delete_place(user_id, place_id)
        return jsonify({"success": True, "message": "Lugar removido"}), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    
@bp.route("/<place_id>", methods=["PATCH"])
@jwt_required
def update_place(place_id):
    user_id = g.user_id
    body = request.get_json()

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400

    try:
        result = place_service.update_place(user_id, place_id, body)
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400
    
@bp.route("/<place_id>/visited", methods=["PATCH"])
@jwt_required
def mark_visited(place_id):
    user_id = g.user_id

    try:
        result = place_service.mark_visited(user_id, place_id)
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404

@bp.route("/<place_id>/feedback", methods=["PATCH"])
@jwt_required
def add_feedback(place_id):
    user_id = g.user_id
    body = request.get_json()

    if not body:
        return jsonify({"success": False, "message": "Body JSON é obrigatório"}), 400

    try:
        result = place_service.add_feedback(user_id, place_id, body.get("feedback"))
        return jsonify(result), 200
    except LookupError as e:
        return jsonify({"success": False, "message": str(e)}), 404
    except ValueError as e:
        return jsonify({"success": False, "message": str(e)}), 400