from unittest.mock import Mock

import pytest

from services.place_service import PlaceService


@pytest.fixture
def service():
    instance = PlaceService.__new__(PlaceService)
    instance.place_repo = Mock()
    return instance


def test_create_place_validates_and_forwards_clean_values(service):
    service.place_repo.create_place.return_value = {"id": "place-1"}

    result = service.create_place(
        "user-1",
        "  Bistro  ",
        "https://maps.google.com/example",
        "Restaurante",
        "https://example.com/photo.jpg",
    )

    assert result == {"id": "place-1"}
    service.place_repo.create_place.assert_called_once_with(
        "user-1",
        "Bistro",
        "https://maps.google.com/example",
        "Restaurante",
        "https://example.com/photo.jpg",
    )


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"name": ""}, "obrigatorio"),
        ({"maps_url": "http://maps.google.com/example"}, "https"),
        ({"category": "Invalid"}, "Categoria invalida"),
    ],
)
def test_create_place_rejects_invalid_input(service, kwargs, message):
    values = {
        "user_id": "user-1",
        "name": "Bistro",
        "maps_url": "https://maps.google.com/example",
        "category": "",
    }
    values.update(kwargs)

    with pytest.raises(ValueError, match=message):
        service.create_place(**values)


def test_update_place_allows_only_boolean_visited(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1"}
    service.place_repo.update_place.return_value = {"visited": True}

    assert service.update_place("user-1", "place-1", {"visited": True}) == {"visited": True}
    service.place_repo.update_place.assert_called_once_with("place-1", {"visited": True})


@pytest.mark.parametrize("fields", [{"id": "changed"}, {"user_id": "other"}, {"visited": "true"}, None])
def test_update_place_rejects_mass_assignment_and_invalid_types(service, fields):
    with pytest.raises(ValueError):
        service.update_place("user-1", "place-1", fields)


def test_delete_place_hides_records_owned_by_another_user(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "other"}

    with pytest.raises(LookupError):
        service.delete_place("user-1", "place-1")


def test_mark_visited_updates_owned_place(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1"}

    service.mark_visited("user-1", "place-1")

    service.place_repo.update_place.assert_called_once_with("place-1", {"visited": True})


def test_add_feedback_requires_visited_place(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1", "visited": False}

    with pytest.raises(ValueError):
        service.add_feedback("user-1", "place-1", "Great")


def test_add_feedback_limits_size(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1", "visited": True}

    with pytest.raises(ValueError):
        service.add_feedback("user-1", "place-1", "x" * 1001)


def test_toggle_favorite_inverts_current_value(service):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1", "favorited": "true"}

    service.toggle_favorite("user-1", "place-1")

    service.place_repo.update_place.assert_called_once_with("place-1", {"favorited": False})


@pytest.mark.parametrize("rating", [None, "invalid", 0, 6])
def test_add_rating_rejects_invalid_values(service, rating):
    service.place_repo.find_by_id.return_value = {"id": "place-1", "user_id": "user-1"}
    with pytest.raises(ValueError):
        service.add_rating("user-1", "place-1", rating)


def test_get_random_place_ignores_visited_places(service, monkeypatch):
    available = {"id": "available", "visited": False}
    service.place_repo.find_all_by_user.return_value = [{"id": "visited", "visited": True}, available]
    monkeypatch.setattr("services.place_service.random.choice", lambda places: places[0])

    assert service.get_random_place("user-1") == available


def test_get_random_place_rejects_empty_list(service):
    service.place_repo.find_all_by_user.return_value = []
    with pytest.raises(LookupError):
        service.get_random_place("user-1")
