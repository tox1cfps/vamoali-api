from repositories.group_repository import GroupRepository
from repositories.user_repository import UserRepository


def test_group_repository_crud():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    repo = GroupRepository()
    group = repo.create_group(user["id"])

    assert repo.find_by_id(group["id"])["created_by"] == user["id"]
    assert repo.find_by_id("missing") is None
