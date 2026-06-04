from datetime import datetime, timedelta, timezone

import pytest

from repositories.group_invite_repository import GroupInviteRepository
from repositories.group_repository import GroupRepository
from repositories.user_repository import UserRepository


def test_group_invite_repository_crud():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    group = GroupRepository().create_group(user["id"])
    repo = GroupInviteRepository()
    invite = repo.create_invite(
        group["id"],
        user["id"],
        "code-hash",
        "token-hash",
        (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
    )

    assert repo.find_by_id(invite["id"])["code_hash"] == "code-hash"
    assert repo.find_by_code_hash("code-hash")["id"] == invite["id"]
    assert repo.find_by_token_hash("token-hash")["id"] == invite["id"]
    assert repo.update_invite(invite["id"], {"revoked_at": datetime.now(timezone.utc).isoformat()})["revoked_at"]
    with pytest.raises(ValueError, match="Campos nao permitidos"):
        repo.update_invite(invite["id"], {"group_id": "other"})
