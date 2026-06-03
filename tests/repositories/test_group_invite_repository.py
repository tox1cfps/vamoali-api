from unittest.mock import Mock

import pytest

from repositories.group_invite_repository import GroupInviteRepository


def build_repo(monkeypatch, rows=None):
    sheet = Mock()
    sheet.get_all_records.return_value = rows or []
    monkeypatch.setattr(
        "repositories.group_invite_repository.get_worksheet",
        lambda name: sheet,
    )
    return GroupInviteRepository(), sheet


def test_find_methods(monkeypatch):
    invite = {
        "id": "invite-1",
        "code_hash": "code-hash",
        "token_hash": "token-hash",
    }
    repo, _ = build_repo(monkeypatch, [invite])

    assert repo.find_by_id("invite-1") == invite
    assert repo.find_by_code_hash("code-hash") == invite
    assert repo.find_by_token_hash("token-hash") == invite
    assert repo.find_by_id("missing") is None


def test_create_invite(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    created = repo.create_invite(
        "group-1",
        "user-1",
        "code-hash",
        "token-hash",
        "2026-06-04T18:00:00+00:00",
    )

    assert created["group_id"] == "group-1"
    assert created["accepted_at"] == ""
    assert created["revoked_at"] == ""
    sheet.append_row.assert_called_once()
    assert sheet.append_row.call_args.kwargs == {"value_input_option": "RAW"}


def test_update_invite(monkeypatch):
    invite = {
        "id": "invite-1",
        "group_id": "group-1",
        "created_by": "user-1",
        "code_hash": "code-hash",
        "token_hash": "token-hash",
        "created_at": "created",
        "expires_at": "expires",
        "accepted_at": "",
        "accepted_by": "",
        "revoked_at": "",
    }
    repo, sheet = build_repo(monkeypatch, [invite])

    updated = repo.update_invite(
        "invite-1",
        {
            "accepted_at": "accepted",
            "accepted_by": "user-2",
        },
    )

    assert updated["accepted_by"] == "user-2"
    assert invite["accepted_by"] == ""
    assert sheet.update.call_args.args[1] == "A2"
    assert sheet.update.call_args.kwargs == {"raw": True}


def test_update_invite_rejects_unexpected_fields(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    with pytest.raises(ValueError, match="Campos nao permitidos"):
        repo.update_invite("invite-1", {"group_id": "other-group"})

    sheet.update.assert_not_called()


def test_update_invite_returns_none_when_missing(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    assert (
        repo.update_invite(
            "missing",
            {"revoked_at": "revoked"},
        )
        is None
    )
    sheet.update.assert_not_called()
