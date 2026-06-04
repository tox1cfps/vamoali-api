from sqlalchemy import select

from database import session_scope
from models import Place
from repositories.base import model_to_dict


class PlaceRepository:
    COLUMNS = [
        "id",
        "user_id",
        "name",
        "maps_url",
        "visited",
        "feedback",
        "created_at",
        "updated_at",
        "photo_url",
        "category",
        "favorited",
        "rating",
    ]

    def _serialize(self, place):
        return model_to_dict(place, self.COLUMNS)

    def find_by_id(self, id):
        with session_scope() as session:
            place = session.get(Place, id)
            return self._serialize(place) if place else None

    def find_all_by_user(self, user_id):
        return self.find_all_by_users([user_id])

    def find_all_by_users(self, user_ids):
        with session_scope() as session:
            places = session.scalars(select(Place).where(Place.user_id.in_(set(user_ids)))).all()
            return [self._serialize(place) for place in places]

    def create_place(self, user_id, name, maps_url, category, photo_url=""):
        with session_scope() as session:
            place = Place(user_id=user_id, name=name, maps_url=maps_url, category=category, photo_url=photo_url)
            session.add(place)
            session.flush()
            return self._serialize(place)

    def delete_place(self, place_id):
        with session_scope() as session:
            place = session.get(Place, place_id)
            if place is None:
                return False
            session.delete(place)
            return True

    def update_place(self, place_id, fields):
        with session_scope() as session:
            place = session.get(Place, place_id)
            if place is None:
                return None
            for name, value in fields.items():
                setattr(place, name, value)
            session.flush()
            return self._serialize(place)
