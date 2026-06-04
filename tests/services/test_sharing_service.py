from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from services.sharing_service import SharingService


@pytest.fixture
def service():
    instance = SharingService.__new__(SharingService)
    instance.group_repo = Mock()
    instance.member_repo = Mock()
    instance.invite_repo = Mock()
    instance.user_repo = Mock()
    return instance


def test_create_invite_creates_group_for_user_without_membership(
    service,
    monkeypatch,
):
    service.member_repo.find_active_by_user.return_value = None
    service.group_repo.create_group.return_value = {"id": "group-1"}
    service.invite_repo.create_invite.return_value = {
        "id": "invite-1",
        "expires_at": "expires",
    }

    monkeypatch.setattr(service, "_generate_code", lambda: "VAMO-ABC123")
    monkeypatch.setattr(
        "services.sharing_service.secrets.token_urlsafe",
        lambda size: "raw-token",
    )

    result = service.create_invite("user-1")

    assert result["code"] == "VAMO-ABC123"
    assert result["token"] == "raw-token"

    service.group_repo.create_group.assert_called_once_with("user-1")
    service.member_repo.create_member.assert_called_once_with(
        "group-1",
        "user-1",
    )

    args = service.invite_repo.create_invite.call_args.args
    assert args[0] == "group-1"
    assert args[1] == "user-1"
    assert args[2] != "VAMO-ABC123"
    assert args[3] != "raw-token"


def test_create_invite_reuses_existing_group(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.invite_repo.create_invite.return_value = {
        "id": "invite-1",
        "expires_at": "expires",
    }

    service.create_invite("user-1")

    service.group_repo.create_group.assert_not_called()
    service.member_repo.create_member.assert_not_called()


def test_create_invite_rejects_missing_group(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "missing"}
    service.group_repo.find_by_id.return_value = None

    with pytest.raises(LookupError, match="Grupo nao encontrado"):
        service.create_invite("user-1")


def test_hash_secret_is_deterministic_and_hides_value():
    first = SharingService._hash_secret("VAMO-ABC123")
    second = SharingService._hash_secret("VAMO-ABC123")

    assert first == second
    assert first != "VAMO-ABC123"


def valid_invite(**overrides):
    invite = {
        "id": "invite-1",
        "group_id": "group-1",
        "created_by": "user-1",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
        "accepted_at": "",
        "accepted_by": "",
        "revoked_at": "",
    }
    return {**invite, **overrides}


def test_accept_invite_by_code(service):
    invite = valid_invite()
    service.invite_repo.find_by_code_hash.return_value = invite
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_user.return_value = None
    service.member_repo.create_member.return_value = {
        "group_id": "group-1",
        "user_id": "user-2",
    }
    service.invite_repo.update_invite.return_value = {
        **invite,
        "accepted_at": "accepted",
        "accepted_by": "user-2",
    }

    result = service.accept_invite("user-2", code="  vamo-abc123  ")

    assert result["group_id"] == "group-1"
    service.member_repo.create_member.assert_called_once_with("group-1", "user-2")
    update_fields = service.invite_repo.update_invite.call_args.args[1]
    assert update_fields["accepted_by"] == "user-2"
    assert update_fields["accepted_at"]


def test_accept_invite_by_token(service):
    invite = valid_invite()
    service.invite_repo.find_by_token_hash.return_value = invite
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_user.return_value = None
    service.member_repo.create_member.return_value = {"id": "member-1"}
    service.invite_repo.update_invite.return_value = {
        **invite,
        "accepted_at": "accepted",
        "accepted_by": "user-2",
    }

    service.accept_invite("user-2", token="raw-token")

    service.invite_repo.find_by_token_hash.assert_called_once()


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"accepted_at": "accepted"}, "ja utilizado"),
        ({"revoked_at": "revoked"}, "revogado"),
        (
            {"expires_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()},
            "expirado",
        ),
    ],
)
def test_accept_invite_rejects_unavailable_invite(service, changes, message):
    service.invite_repo.find_by_code_hash.return_value = valid_invite(**changes)

    with pytest.raises(ValueError, match=message):
        service.accept_invite("user-2", code="VAMO-ABC123")

    service.member_repo.create_member.assert_not_called()


def test_accept_invite_rejects_own_invite(service):
    service.invite_repo.find_by_code_hash.return_value = valid_invite()

    with pytest.raises(ValueError, match="proprio convite"):
        service.accept_invite("user-1", code="VAMO-ABC123")


def test_accept_invite_rejects_existing_membership(service):
    service.invite_repo.find_by_code_hash.return_value = valid_invite()
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_user.return_value = {"group_id": "other-group"}

    with pytest.raises(ValueError, match="outro grupo"):
        service.accept_invite("user-2", code="VAMO-ABC123")


@pytest.mark.parametrize(
    ("code", "token"),
    [
        (None, None),
        ("VAMO-ABC123", "raw-token"),
    ],
)
def test_accept_invite_requires_exactly_one_identifier(service, code, token):
    with pytest.raises(ValueError, match="somente codigo ou token"):
        service.accept_invite("user-2", code=code, token=token)


def test_accept_invite_detects_failed_invite_update(service):
    service.invite_repo.find_by_code_hash.return_value = valid_invite()
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_user.return_value = None
    service.member_repo.create_member.return_value = {"id": "member-1"}
    service.invite_repo.update_invite.return_value = None

    with pytest.raises(LookupError, match="Convite nao encontrado"):
        service.accept_invite("user-2", code="VAMO-ABC123")


def test_get_visible_user_ids_returns_only_user_without_group(service):
    service.member_repo.find_active_by_user.return_value = None

    assert service.get_visible_user_ids("user-1") == ["user-1"]


def test_get_visible_user_ids_returns_active_group_members(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1"},
        {"user_id": "user-2"},
    ]

    result = service.get_visible_user_ids("user-1")

    assert result == ["user-1", "user-2"]


def test_get_visible_user_ids_rejects_missing_group(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "missing"}
    service.group_repo.find_by_id.return_value = None

    with pytest.raises(LookupError, match="Grupo nao encontrado"):
        service.get_visible_user_ids("user-1")


def test_get_visible_user_ids_requires_current_user_in_group(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1"}
    service.member_repo.find_active_by_group.return_value = [{"user_id": "user-2"}]

    with pytest.raises(LookupError, match="Participacao"):
        service.get_visible_user_ids("user-1")


def test_get_group_returns_public_member_data(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {
        "id": "group-1",
        "created_by": "user-1",
        "created_at": "created",
    }
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1", "joined_at": "joined-1"},
        {"user_id": "user-2", "joined_at": "joined-2"},
    ]
    service.user_repo.find_by_ids.return_value = {
        "user-1": {"id": "user-1", "username": "Ana", "email": "ana@example.com", "password_hash": "secret"},
        "user-2": {"id": "user-2", "username": "Bia", "email": "bia@example.com", "password_hash": "secret"},
    }

    result = service.get_group("user-1")

    assert result["id"] == "group-1"
    assert result["members"] == [
        {
            "id": "user-1",
            "username": "Ana",
            "joined_at": "joined-1",
            "is_current_user": True,
            "is_creator": True,
        },
        {
            "id": "user-2",
            "username": "Bia",
            "joined_at": "joined-2",
            "is_current_user": False,
            "is_creator": False,
        },
    ]
    assert "email" not in result["members"][0]
    assert "password_hash" not in result["members"][0]
    service.user_repo.find_by_ids.assert_called_once()


def test_get_group_rejects_user_without_group(service):
    service.member_repo.find_active_by_user.return_value = None

    with pytest.raises(LookupError, match="Grupo nao encontrado"):
        service.get_group("user-1")


def test_get_group_rejects_missing_member_user(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {
        "id": "group-1",
        "created_by": "user-1",
    }
    service.member_repo.find_active_by_group.return_value = [{"user_id": "user-1"}]
    service.user_repo.find_by_ids.return_value = {}

    with pytest.raises(LookupError, match="Usuario do grupo"):
        service.get_group("user-1")


def test_get_group_requires_current_user_in_active_members(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {
        "id": "group-1",
        "created_by": "user-2",
    }
    service.member_repo.find_active_by_group.return_value = [{"user_id": "user-2"}]
    service.user_repo.find_by_ids.return_value = {"user-2": {"id": "user-2", "username": "Bia"}}

    with pytest.raises(LookupError, match="Participacao"):
        service.get_group("user-1")


def test_remove_member_allows_member_to_leave(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1"},
        {"user_id": "user-2"},
    ]
    service.member_repo.deactivate_member.return_value = {"user_id": "user-2"}

    result = service.remove_member("user-2", "user-2")

    assert result["removed_user_id"] == "user-2"
    service.member_repo.deactivate_member.assert_called_once_with("group-1", "user-2")


def test_remove_member_allows_creator_to_remove_other_member(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1"},
        {"user_id": "user-2"},
    ]
    service.member_repo.deactivate_member.return_value = {"user_id": "user-2"}

    service.remove_member("user-1", "user-2")

    service.member_repo.deactivate_member.assert_called_once_with("group-1", "user-2")


def test_remove_member_rejects_non_creator_removing_other_member(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1"},
        {"user_id": "user-2"},
        {"user_id": "user-3"},
    ]

    with pytest.raises(PermissionError, match="Somente o criador"):
        service.remove_member("user-2", "user-3")


def test_remove_member_requires_creator_to_remove_others_before_leaving(service):
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.member_repo.find_active_by_group.return_value = [
        {"user_id": "user-1"},
        {"user_id": "user-2"},
    ]

    with pytest.raises(ValueError, match="Remova os outros membros"):
        service.remove_member("user-1", "user-1")


def test_revoke_invite_allows_invite_creator(service):
    invite = valid_invite()
    service.invite_repo.find_by_id.return_value = invite
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.invite_repo.update_invite.return_value = {**invite, "revoked_at": "revoked"}

    result = service.revoke_invite("user-1", "invite-1")

    assert result["invite_id"] == "invite-1"
    assert result["revoked_at"]


def test_revoke_invite_allows_group_creator(service):
    invite = valid_invite(created_by="user-2")
    service.invite_repo.find_by_id.return_value = invite
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}
    service.invite_repo.update_invite.return_value = {**invite, "revoked_at": "revoked"}

    service.revoke_invite("user-1", "invite-1")

    service.invite_repo.update_invite.assert_called_once()


def test_revoke_invite_rejects_member_without_permission(service):
    invite = valid_invite(created_by="user-2")
    service.invite_repo.find_by_id.return_value = invite
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}

    with pytest.raises(PermissionError, match="Sem permissao"):
        service.revoke_invite("user-3", "invite-1")


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"accepted_at": "accepted"}, "ja utilizado"),
        ({"revoked_at": "revoked"}, "ja revogado"),
    ],
)
def test_revoke_invite_rejects_unavailable_invite(service, changes, message):
    service.invite_repo.find_by_id.return_value = valid_invite(**changes)
    service.member_repo.find_active_by_user.return_value = {"group_id": "group-1"}
    service.group_repo.find_by_id.return_value = {"id": "group-1", "created_by": "user-1"}

    with pytest.raises(ValueError, match=message):
        service.revoke_invite("user-1", "invite-1")
