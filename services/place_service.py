from repositories.place_repository import PlaceRepository
import random

class PlaceService:
    def __init__(self):
        self.place_repo = PlaceRepository()

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
        return self.place_repo.find_all_by_user(user_id)


    def create_place(self, user_id, name, maps_url, category, photo_url=""):
        if not name:
            raise ValueError("O nome do lugar é obrigatório")
        
        return self.place_repo.create_place(user_id, name, maps_url, category, photo_url)
    
    def delete_place(self, user_id, place_id):
        place = self.place_repo.find_by_id(place_id)
        
        if place is None:
            raise LookupError("Lugar não encontrado ")
        
        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")
        
        return self.place_repo.delete_place(place_id)

    def update_place(self, user_id, place_id, fields):
        place = self.place_repo.find_by_id(place_id)

        if place is None:
            raise LookupError("Lugar não encontrado ")
        
        if place["user_id"] != user_id:
            raise LookupError("Lugar não encontrado")
        
        return self.place_repo.update_place(place_id, fields)
    
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


        if not feedback:
            raise ValueError("Não esqueça o feedback!")
        
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
        places = self.place_repo.find_all_by_user(user_id)
        available_places = [place for place in places if not self._is_truthy(place.get("visited"))]

        if not available_places:
            raise LookupError("Sem lugares na lista para sortear. Adicione um primeiro e tente de novo!")

        return random.choice(available_places)