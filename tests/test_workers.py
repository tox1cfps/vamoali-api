import io
import zipfile
from datetime import datetime, timezone
from unittest.mock import Mock

from cryptography.fernet import Fernet
from gspread.exceptions import WorksheetNotFound

from repositories.place_repository import PlaceRepository
from repositories.user_repository import UserRepository
from scripts import import_sheets_to_postgres
from workers import backup_database, email_worker, schedule_unvisited_reminders, sync_sheets_report


def test_email_worker_delivers_supported_messages(monkeypatch):
    send_email = Mock()
    send_reset = Mock()
    send_welcome = Mock()
    monkeypatch.setattr(email_worker, "send_email", send_email)
    monkeypatch.setattr(email_worker, "send_password_reset_email", send_reset)
    monkeypatch.setattr(email_worker, "send_welcome_email", send_welcome)

    email_worker.deliver({"kind": "welcome", "recipient": "a@example.com", "payload": {"username": "Ana"}})
    email_worker.deliver(
        {
            "kind": "unvisited_reminder",
            "recipient": "a@example.com",
            "payload": {"count": 2, "suggestion": "Bistro"},
        }
    )
    email_worker.deliver({"kind": "password_reset", "recipient": "a@example.com", "payload": {"token": "raw"}})

    assert send_email.call_count == 1
    send_welcome.assert_called_once_with("a@example.com", "Ana")
    send_reset.assert_called_once_with("a@example.com", "raw")


def test_email_worker_processes_success_failure_and_empty(monkeypatch):
    repo = Mock()
    repo.claim_next.side_effect = [
        {"id": "1", "kind": "welcome", "recipient": "a@example.com", "payload": {"username": "Ana"}},
        {"id": "2", "kind": "unknown", "recipient": "a@example.com", "payload": {}},
        None,
    ]
    monkeypatch.setattr(email_worker, "send_email", Mock())
    monkeypatch.setattr(email_worker, "send_welcome_email", Mock())

    assert email_worker.process_one(repo) is True
    repo.mark_sent.assert_called_once_with("1")
    assert email_worker.process_one(repo) is True
    repo.mark_failed.assert_called_once()
    assert email_worker.process_one(repo) is False


def test_email_worker_processes_pending_batch(monkeypatch):
    process_one = Mock(side_effect=[True, True, False])
    monkeypatch.setattr(email_worker, "process_one", process_one)

    assert email_worker.process_pending(10) == 2


def test_schedule_unvisited_reminders(monkeypatch):
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    PlaceRepository().create_place(user["id"], "Bistro", "https://maps.example/x", "Restaurante")
    enqueue = Mock(return_value="job-1")
    monkeypatch.setattr(schedule_unvisited_reminders.EmailJobRepository, "enqueue", enqueue)

    assert schedule_unvisited_reminders.schedule_reminders() == 1
    assert enqueue.call_args.args[0] == "unvisited_reminder"


def test_build_and_send_encrypted_backup(monkeypatch):
    UserRepository().create_user("Ana", "ana@example.com", "hash")
    raw = backup_database.build_backup()
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        assert "users.csv" in archive.namelist()

    key = Fernet.generate_key().decode()
    send_email = Mock()
    monkeypatch.setattr(backup_database, "BACKUP_EMAIL", "backup@example.com")
    monkeypatch.setattr(backup_database, "BACKUP_ENCRYPTION_KEY", key)
    monkeypatch.setattr(backup_database, "send_email", send_email)

    assert backup_database.run_backup() == "enviado para backup@example.com"
    attachment = send_email.call_args.args[3]
    assert attachment[0].endswith(".fernet")
    assert zipfile.is_zipfile(io.BytesIO(Fernet(key.encode()).decrypt(attachment[1])))


def test_sync_sheets_report(monkeypatch):
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    PlaceRepository().create_place(user["id"], "Bistro", "https://maps.example/x", "Restaurante")
    spreadsheet = Mock()
    spreadsheet.worksheet.side_effect = WorksheetNotFound("missing")
    monkeypatch.setattr(sync_sheets_report, "get_report_spreadsheet", lambda: spreadsheet)

    result = sync_sheets_report.sync_report()

    assert result == {"users": 1, "places": 1}
    assert spreadsheet.add_worksheet.call_count == 3


def test_import_sheets_to_postgres(monkeypatch):
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "users": [{"id": "user-1", "username": "Ana", "email": "ana@example.com", "password_hash": "hash"}],
        "places": [
            {
                "id": "place-1",
                "user_id": "user-1",
                "name": "Bistro",
                "maps_url": "https://maps.example/x",
                "category": "Restaurante",
                "visited": "true",
                "rating": "5",
                "created_at": now,
                "updated_at": now,
            }
        ],
        "groups": [{"id": "group-1", "created_by": "user-1", "created_at": now}],
        "group_members": [
            {"id": "member-1", "group_id": "group-1", "user_id": "user-1", "joined_at": now, "left_at": ""}
        ],
        "group_invites": [
            {
                "id": "invite-1",
                "group_id": "group-1",
                "created_by": "user-1",
                "code_hash": "code",
                "token_hash": "token",
                "created_at": now,
                "expires_at": now,
                "accepted_at": "",
                "accepted_by": "",
                "revoked_at": "",
            }
        ],
    }
    monkeypatch.setattr(import_sheets_to_postgres, "rows", lambda name: data[name])
    monkeypatch.setattr(import_sheets_to_postgres, "maybe_decrypt", lambda value: value)

    counts = import_sheets_to_postgres.import_all()

    assert counts["users"] == 1
    assert counts["places"] == 1
    assert counts["groups"] == 1
    assert counts["group_members"] == 1
    assert counts["group_invites"] == 1
    assert import_sheets_to_postgres.import_all()["users"] == 0
    assert import_sheets_to_postgres.migration_status()["matches"] is True
