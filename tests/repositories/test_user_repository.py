from unittest.mock import Mock

from repositories.user_repository import UserRepository, _maybe_decrypt


def build_repo(monkeypatch, rows=None):
    sheet = Mock()
    sheet.get_all_records.return_value = rows or []
    monkeypatch.setattr("repositories.user_repository.get_worksheet", lambda name: sheet)
    monkeypatch.setattr("repositories.user_repository.encrypt", lambda value: f"encrypted:{value}")
    monkeypatch.setattr("repositories.user_repository.decrypt", lambda value: value.removeprefix("encrypted:"))
    return UserRepository(), sheet


def test_maybe_decrypt_preserves_plaintext_and_empty_values():
    assert _maybe_decrypt("") == ""
    assert _maybe_decrypt("plain") == "plain"


def test_find_by_email_and_id_decrypt_public_fields(monkeypatch):
    rows = [{"id": "user-1", "email": "encrypted:ana@example.com", "username": "encrypted:Ana"}]
    repo, _ = build_repo(monkeypatch, rows)

    assert repo.find_by_email("ana@example.com")["username"] == "Ana"
    assert repo.find_by_email("missing@example.com") is None
    assert repo.find_by_id("user-1")["email"] == "ana@example.com"
    assert repo.find_by_id("missing") is None


def test_find_by_ids_reads_users_once(monkeypatch):
    rows = [
        {"id": "user-1", "email": "encrypted:ana@example.com", "username": "encrypted:Ana"},
        {"id": "user-2", "email": "encrypted:bia@example.com", "username": "encrypted:Bia"},
        {"id": "user-3", "email": "encrypted:caio@example.com", "username": "encrypted:Caio"},
    ]
    repo, sheet = build_repo(monkeypatch, rows)

    users = repo.find_by_ids(["user-1", "user-2"])

    assert set(users) == {"user-1", "user-2"}
    assert users["user-2"]["username"] == "Bia"
    sheet.get_all_records.assert_called_once()


def test_create_user_appends_raw_encrypted_row(monkeypatch):
    repo, sheet = build_repo(monkeypatch)

    created = repo.create_user("Ana", "ana@example.com", "hash")

    assert created["username"] == "Ana"
    assert sheet.append_row.call_args.args[0][1:] == ["encrypted:Ana", "encrypted:ana@example.com", "hash"]
    assert sheet.append_row.call_args.kwargs == {"value_input_option": "RAW"}


def test_update_password_updates_matching_row(monkeypatch):
    repo, sheet = build_repo(
        monkeypatch,
        [{"id": "user-1", "email": "encrypted:ana@example.com", "username": "encrypted:Ana"}],
    )

    assert repo.update_password("ana@example.com", "new-hash") is True
    sheet.update_cell.assert_called_once_with(2, 4, "new-hash")
    assert repo.update_password("missing@example.com", "new-hash") is False
