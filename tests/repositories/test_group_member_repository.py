from unittest.mock import Mock

from repositories.group_member_repository import GroupMemberRepository


def build_repo(monkeypatch, rows=None):
    sheet = Mock()
    sheet.get_all_records.return_value = rows or []
    monkeypatch.setattr(
        "repositories.group_member_repository.get_worksheet",
        lambda name: sheet,
    )
    return GroupMemberRepository(), sheet


def test_create_member(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    created = repo.create_member("group-1", "user-1")

    assert created["group_id"] == "group-1"
    assert created["user_id"] == "user-1"
    assert created["left_at"] == ""
    sheet.append_row.assert_called_once()
    assert sheet.append_row.call_args.kwargs == {"value_input_option": "RAW"}


def test_find_active_by_user_ignores_inactive_member(monkeypatch):
    rows = [
        {"group_id": "old-group", "user_id": "user-1", "left_at": "2026-01-01"},
        {"group_id": "group-1", "user_id": "user-1", "left_at": ""},
    ]
    repo, _ = build_repo(monkeypatch, rows)

    assert repo.find_active_by_user("user-1") == rows[1]
    assert repo.find_active_by_user("missing") is None


def test_find_active_by_group(monkeypatch):
    rows = [
        {"group_id": "group-1", "user_id": "user-1", "left_at": ""},
        {"group_id": "group-1", "user_id": "user-2", "left_at": "2026-01-01"},
        {"group_id": "group-2", "user_id": "user-3", "left_at": ""},
    ]
    repo, _ = build_repo(monkeypatch, rows)

    assert repo.find_active_by_group("group-1") == [rows[0]]


def test_deactivate_member(monkeypatch):
    rows = [
        {"group_id": "group-1", "user_id": "user-1", "left_at": ""},
    ]
    repo, sheet = build_repo(monkeypatch, rows)

    result = repo.deactivate_member("group-1", "user-1")

    assert result["left_at"]
    sheet.update_cell.assert_called_once()
    assert sheet.update_cell.call_args.args[:2] == (2, 5)


def test_deactivate_member_returns_none_when_not_active(monkeypatch):
    rows = [
        {"group_id": "group-1", "user_id": "user-1", "left_at": "2026-01-01"},
    ]
    repo, sheet = build_repo(monkeypatch, rows)

    assert repo.deactivate_member("group-1", "user-1") is None
    sheet.update_cell.assert_not_called()
