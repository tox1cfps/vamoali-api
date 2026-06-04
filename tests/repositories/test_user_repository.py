from repositories.user_repository import UserRepository


def test_user_repository_crud():
    repo = UserRepository()
    created = repo.create_user("Ana", "ana@example.com", "hash")

    assert repo.find_by_email("ana@example.com")["username"] == "Ana"
    assert repo.find_by_id(created["id"])["email"] == "ana@example.com"
    assert repo.find_by_ids([created["id"]])[created["id"]]["username"] == "Ana"
    assert repo.update_password("ana@example.com", "new-hash") is True
    assert repo.find_by_email("ana@example.com")["password_hash"] == "new-hash"
    assert repo.update_password("missing@example.com", "hash") is False
