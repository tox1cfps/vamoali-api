from repositories.place_repository import PlaceRepository
from repositories.user_repository import UserRepository


def test_place_repository_crud():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    repo = PlaceRepository()
    place = repo.create_place(user["id"], "Bistro", "https://maps.google.com/example", "Restaurante")

    assert repo.find_by_id(place["id"])["name"] == "Bistro"
    assert repo.find_all_by_user(user["id"])[0]["id"] == place["id"]
    assert repo.find_all_by_users([user["id"]])[0]["id"] == place["id"]
    assert repo.update_place(place["id"], {"visited": True})["visited"] is True
    assert repo.delete_place(place["id"]) is True
    assert repo.delete_place("missing") is False
