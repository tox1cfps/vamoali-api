from repositories.place_repository import PlaceRepository

class PlaceService:
    def __init__(self):
        self.place_repo = PlaceRepository()

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

        is_visited = place["visited"] is True or str(place["visited"]).upper() == "TRUE"
        
        if not is_visited:
            raise ValueError("Só é possível adicionar feedback após marcar o lugar como visitado")


        if not feedback:
            raise ValueError("Não esqueça o feedback!")
        
        return self.place_repo.update_place(place_id, {"feedback": feedback})