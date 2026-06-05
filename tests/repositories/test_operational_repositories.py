from datetime import datetime, timedelta, timezone
import json

from database import session_scope
from models import EmailJob
from repositories.email_job_repository import EmailJobRepository
from repositories.password_reset_repository import PasswordResetRepository
from repositories.user_repository import UserRepository


def test_password_reset_repository_lifecycle():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    repo = PasswordResetRepository()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=5)

    repo.create("token-hash", user["id"], expires_at.isoformat())
    assert repo.find_valid("token-hash")["user_id"] == user["id"]
    assert repo.consume("token-hash") is True
    assert repo.find_valid("token-hash") is None
    assert repo.consume("missing") is False

    repo.create("delete-me", user["id"], expires_at.isoformat())
    assert repo.delete("delete-me") is True


def test_password_reset_repository_cleans_expired_tokens():
    user = UserRepository().create_user("Ana", "ana@example.com", "hash")
    repo = PasswordResetRepository()
    repo.create("expired", user["id"], (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())

    assert repo.cleanup_expired() == 1


def test_email_job_repository_lifecycle(monkeypatch):
    repo = EmailJobRepository()
    job_id = repo.enqueue("welcome", "ana@example.com", {"username": "Ana"}, "welcome:user-1")

    assert job_id
    with session_scope() as session:
        stored_payload = session.get(EmailJob, job_id).payload_json
        assert stored_payload != json.dumps({"username": "Ana"})
        assert repo._decrypt_payload(stored_payload) == {"username": "Ana"}
    assert repo.enqueue("welcome", "ana@example.com", {}, "welcome:user-1") is None
    claimed = repo.claim_next()
    assert claimed["payload"] == {"username": "Ana"}

    repo.mark_failed(job_id, RuntimeError("smtp"))
    assert repo.claim_next() is None

    monkeypatch.setattr("repositories.email_job_repository.EMAIL_MAX_ATTEMPTS", 1)
    second_id = repo.enqueue("welcome", "bia@example.com")
    repo.claim_next()
    repo.mark_failed(second_id, RuntimeError("final"))


def test_email_job_repository_marks_sent():
    repo = EmailJobRepository()
    job_id = repo.enqueue("welcome", "ana@example.com")
    assert repo.claim_next()["id"] == job_id
    repo.mark_sent(job_id)
    assert repo.claim_next() is None
