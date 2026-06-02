from unittest.mock import Mock

import controllers.place_controller as controller


def test_list_places_requires_authentication(client):
    assert client.get("/places").status_code == 401


def test_list_places_returns_service_payload(authenticated_client, monkeypatch):
    service = Mock()
    service.get_places.return_value = [{"id": "place-1"}]
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.get("/places")

    assert response.status_code == 200
    assert response.get_json() == [{"id": "place-1"}]


def test_create_place_returns_201(authenticated_client, monkeypatch):
    service = Mock()
    service.create_place.return_value = {"id": "place-1"}
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.post(
        "/places",
        json={"name": "Bistro", "maps_url": "https://maps.google.com/example", "category": ""},
    )

    assert response.status_code == 201
    assert response.get_json() == {"id": "place-1"}


def test_update_place_converts_mass_assignment_error_to_400(authenticated_client, monkeypatch):
    service = Mock()
    service.update_place.side_effect = ValueError("Campos nao permitidos")
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.patch("/places/place-1", json={"user_id": "other"})

    assert response.status_code == 400


def test_delete_place_converts_missing_record_to_404(authenticated_client, monkeypatch):
    service = Mock()
    service.delete_place.side_effect = LookupError("missing")
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.delete("/places/place-1")

    assert response.status_code == 404


def test_toggle_favorite_returns_updated_place(authenticated_client, monkeypatch):
    service = Mock()
    service.toggle_favorite.return_value = {"id": "place-1", "favorited": True}
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.patch("/places/place-1/favorite")

    assert response.status_code == 200
    assert response.get_json()["favorited"] is True


def test_random_place_converts_empty_list_to_404(authenticated_client, monkeypatch):
    service = Mock()
    service.get_random_place.side_effect = LookupError("empty")
    monkeypatch.setattr(controller, "place_service", service)

    assert authenticated_client.get("/places/random").status_code == 404


def test_mark_visited_returns_updated_place(authenticated_client, monkeypatch):
    service = Mock()
    service.mark_visited.return_value = {"id": "place-1", "visited": True}
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.patch("/places/place-1/visited")

    assert response.status_code == 200
    assert response.get_json()["visited"] is True


def test_feedback_requires_json_body(authenticated_client):
    assert authenticated_client.patch("/places/place-1/feedback").status_code == 400


def test_rating_converts_validation_error_to_400(authenticated_client, monkeypatch):
    service = Mock()
    service.add_rating.side_effect = ValueError("invalid")
    monkeypatch.setattr(controller, "place_service", service)

    response = authenticated_client.patch("/places/place-1/rating", json={"rating": 6})

    assert response.status_code == 400
