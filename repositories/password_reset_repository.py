from sqlalchemy import delete, select

from database import session_scope
from models import PasswordResetToken, utcnow
from repositories.base import parse_datetime


class PasswordResetRepository:
    def create(self, token_hash, user_id, expires_at):
        with session_scope() as session:
            session.add(
                PasswordResetToken(token_hash=token_hash, user_id=user_id, expires_at=parse_datetime(expires_at))
            )

    def find_valid(self, token_hash):
        with session_scope() as session:
            token = session.scalar(
                select(PasswordResetToken).where(
                    PasswordResetToken.token_hash == token_hash,
                    PasswordResetToken.consumed_at.is_(None),
                    PasswordResetToken.expires_at > utcnow(),
                )
            )
            if token is None:
                return None
            return {
                "token_hash": token.token_hash,
                "user_id": token.user_id,
                "expires_at": token.expires_at.isoformat(),
            }

    def consume(self, token_hash):
        with session_scope() as session:
            token = session.get(PasswordResetToken, token_hash)
            if token is None or token.consumed_at is not None:
                return False
            token.consumed_at = utcnow()
            return True

    def delete(self, token_hash):
        with session_scope() as session:
            result = session.execute(delete(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash))
            return result.rowcount > 0

    def cleanup_expired(self):
        with session_scope() as session:
            result = session.execute(delete(PasswordResetToken).where(PasswordResetToken.expires_at <= utcnow()))
            return result.rowcount
