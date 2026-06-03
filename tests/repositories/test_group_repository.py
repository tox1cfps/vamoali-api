from unittest.mock import Mock

from repositories.group_repository import GroupRepository


def build_repo(monkeypatch, rows=None):
    sheet = Mock()
    sheet.get_all_records.return_value = rows or []
    monkeypatch.setattr("repositories.group_repository.get_worksheet", lambda name: sheet)

    return GroupRepository(), sheet


def test_find_by_id(monkeypatch):
    rows = [{"id": "group-1", "created_by": "user-1"}]
    repo, _ = build_repo(monkeypatch, rows)

    assert repo.find_by_id("group-1") == rows[0]
    assert repo.find_by_id("missing") is None


def test_create_group(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    created = repo.create_group("user-1")

    assert created["created_by"] == "user-1"
    assert created["id"]
    assert created["created_at"]
    sheet.append_row.assert_called_once()
    assert sheet.append_row.call_args.kwargs == {"value_input_option": "RAW"}
