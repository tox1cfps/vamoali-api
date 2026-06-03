import random

from repositories.place_repository import PlaceRepository
from services.sharing_service import SharingService
from utils.validation import validate_category, validate_https_url, validate_string


class PlaceService:
    ALLOWED_PATCH_FIELDS = {"visited"}

    def __init__(self):
        self.place_repo = PlaceRepository()
        self.sharing_service = SharingService()

    @staticmethod
    def _is_truthy(value):
        return value is True or str(value).strip().lower() == "true"

    @staticmethod
    def _normalize_rating(rating):
        try:
            rating_int = int(rating)
        except (TypeError, ValueError):
            raise ValueError("A avaliação precisa ser um número inteiro entre 1 e 5")

        if rating_int < 1 or rating_int > 5:
            raise ValueError("A avaliação precisa ser um número inteiro entre 1 e 5")

        return rating_int

    def get_places(self, user_id):
        visible_user_ids = self.sharing_service.get_visible_user_ids(user_id)
        places = self.place_repo.find_all_by_users(visible_user_ids)

        return [
            {
                **place,
                "is_owner": place["user_id"] == user_id,
                "permissions": {
                    "can_edit": place["user_id"] == user_id,
                    "can_delete": place["user_id"] == user_id,
                },
            }
            for place in places
        ]

    def create_place(self, user_id, name, maps_url, category, photo_url=""):
        name = validate_string(name, "Nome do lugar", required=True, max_length=120)
        maps_url = validate_https_url(maps_url, "Link do Maps", required=True)
        category = validate_category(category)
        photo_url = validate_https_url(photo_url, "URL da foto")

        return self.place_repo.create_place(user_id, name, maps_url, category, photo_url)

    def delete_place(self, user_id, place_id):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado ")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        return self.place_repo.delete_place(place_id)

    def update_place(self, user_id, place_id, fields):
        if not isinstance(fields, dict):
            raise ValueError("Campos invalidos")

        unexpected_fields = set(fields) - self.ALLOWED_PATCH_FIELDS
        if unexpected_fields:
            raise ValueError("Campos nao permitidos")
        if "visited" not in fields or not isinstance(fields["visited"], bool):
            raise ValueError("visited deve ser booleano")

        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado ")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        return self.place_repo.update_place(place_id, {"visited": fields["visited"]})

    def mark_visited(self, user_id, place_id):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        return self.place_repo.update_place(place_id, {"visited": True})

    def add_feedback(self, user_id, place_id, feedback):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        is_visited = self._is_truthy(place.get("visited"))

        if not is_visited:
            raise ValueError("Só é possível adicionar feedback após marcar o lugar como visitado")

        feedback = validate_string(feedback, "Feedback", required=True, max_length=1000)

        return self.place_repo.update_place(place_id, {"feedback": feedback})

    def toggle_favorite(self, user_id, place_id):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        favorited = not self._is_truthy(place.get("favorited"))
        return self.place_repo.update_place(place_id, {"favorited": favorited})

    def add_rating(self, user_id, place_id, rating):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado")

        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")

        rating_value = self._normalize_rating(rating)
        return self.place_repo.update_place(place_id, {"rating": rating_value})

    def get_random_place(self, user_id):
        places = self.get_places(user_id)
        available_places = [place for place in places if not self._is_truthy(place.get("visited"))]

        if not available_places:
            raise LookupError("Sem lugares na lista para sortear. Adicione um primeiro e tente de novo!")

        return random.choice(available_places)
