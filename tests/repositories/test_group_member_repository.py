from repositories.group_member_repository import GroupMemberRepository
from repositories.group_repository import GroupRepository
from repositories.user_repository import UserRepository


def test_group_member_repository_crud():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    group = GroupRepository().create_group(user["id"])
    repo = GroupMemberRepository()
    member = repo.create_member(group["id"], user["id"])

    assert repo.find_active_by_user(user["id"])["id"] == member["id"]
    assert repo.find_active_by_group(group["id"])[0]["id"] == member["id"]
    assert repo.deactivate_member(group["id"], user["id"])["left_at"]
    assert repo.find_active_by_user(user["id"]) is None
