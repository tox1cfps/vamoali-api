import json
from datetime import timedelta

from cryptography.fernet import Fernet
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from config.settings import EMAIL_MAX_ATTEMPTS, EMAIL_PAYLOAD_ENCRYPTION_KEY
from database import session_scope
from models import EmailJob, utcnow


class EmailJobRepository:
    @staticmethod
    def _encrypt_payload(payload):
        serialized = json.dumps(payload or {}).encode()
        return Fernet(EMAIL_PAYLOAD_ENCRYPTION_KEY.encode()).encrypt(serialized).decode()

    @staticmethod
    def _decrypt_payload(payload):
        decrypted = Fernet(EMAIL_PAYLOAD_ENCRYPTION_KEY.encode()).decrypt(payload.encode())
        return json.loads(decrypted)

    def enqueue(self, kind, recipient, payload=None, deduplication_key=None):
        try:
            with session_scope() as session:
                job = EmailJob(
                    kind=kind,
                    recipient=recipient,
                    payload_json=self._encrypt_payload(payload),
                    deduplication_key=deduplication_key,
                )
                session.add(job)
                session.flush()
                return job.id
        except IntegrityError:
            return None

    def claim_next(self):
        with session_scope() as session:
            job = session.scalar(
                select(EmailJob)
                .where(
                    EmailJob.status == "pending",
                    EmailJob.available_at <= utcnow(),
                    EmailJob.attempts < EMAIL_MAX_ATTEMPTS,
                )
                .order_by(EmailJob.created_at)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
            if job is None:
                return None
            job.status = "processing"
            job.attempts += 1
            session.flush()
            return {
                "id": job.id,
                "kind": job.kind,
                "recipient": job.recipient,
                "payload": self._decrypt_payload(job.payload_json),
                "attempts": job.attempts,
            }

    def mark_sent(self, job_id):
        with session_scope() as session:
            job = session.get(EmailJob, job_id)
            job.status = "sent"
            job.sent_at = utcnow()
            job.last_error = None

    def mark_failed(self, job_id, error):
        with session_scope() as session:
            job = session.get(EmailJob, job_id)
            job.status = "pending" if job.attempts < EMAIL_MAX_ATTEMPTS else "failed"
            job.available_at = utcnow() + timedelta(minutes=min(2**job.attempts, 60))
            job.last_error = str(error)[:2000]
