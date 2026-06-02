from unittest.mock import Mock

from repositories.place_repository import PlaceRepository


def build_repo(monkeypatch, rows=None):
    sheet = Mock()
    sheet.get_all_records.return_value = rows or []
    monkeypatch.setattr("repositories.place_repository.get_worksheet", lambda name: sheet)
    return PlaceRepository(), sheet


def test_find_methods_filter_rows(monkeypatch):
    rows = [{"id": "place-1", "user_id": "user-1"}, {"id": "place-2", "user_id": "user-2"}]
    repo, _ = build_repo(monkeypatch, rows)

    assert repo.find_by_id("place-1") == rows[0]
    assert repo.find_by_id("missing") is None
    assert repo.find_all_by_user("user-2") == [rows[1]]


def test_create_place_appends_raw_row(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    created = repo.create_place("user-1", "Bistro", "https://maps.google.com/example", "Restaurante")

    assert created["user_id"] == "user-1"
    sheet.append_row.assert_called_once()
    assert sheet.append_row.call_args.kwargs == {"value_input_option": "RAW"}


def test_delete_place_removes_existing_row(monkeypatch):
    repo, sheet = build_repo(monkeypatch, [{"id": "place-1"}])

    assert repo.delete_place("place-1") is True
    sheet.delete_rows.assert_called_once_with(2)
    assert repo.delete_place("missing") is False


def test_update_place_writes_raw_row_without_mutating_input(monkeypatch):
    rows = [{"id": "place-1", "user_id": "user-1", "visited": False}]
    repo, sheet = build_repo(monkeypatch, rows)
    fields = {"visited": True}

    updated = repo.update_place("place-1", fields)

    assert updated["visited"] is True
    assert "updated_at" not in fields
    assert sheet.update.call_args.args[1] == "A2"
    assert sheet.update.call_args.kwargs == {"raw": True}
    assert repo.update_place("missing", fields) is None
