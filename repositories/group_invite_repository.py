from sqlalchemy import select

from database import session_scope
from models import GroupInvite
from repositories.base import model_to_dict, parse_datetime


class GroupInviteRepository:
    COLUMNS = [
        "id",
        "group_id",
        "created_by",
        "code_hash",
        "token_hash",
        "created_at",
        "expires_at",
        "accepted_at",
        "accepted_by",
        "revoked_at",
    ]
    ALLOWED_UPDATE_FIELDS = {"accepted_at", "accepted_by", "revoked_at"}

    def _serialize(self, invite):
        return model_to_dict(invite, self.COLUMNS)

    def find_by_id(self, invite_id):
        with session_scope() as session:
            invite = session.get(GroupInvite, invite_id)
            return self._serialize(invite) if invite else None

    def _find_by(self, field, value):
        with session_scope() as session:
            invite = session.scalar(select(GroupInvite).where(field == value))
            return self._serialize(invite) if invite else None

    def find_by_code_hash(self, code_hash):
        return self._find_by(GroupInvite.code_hash, code_hash)

    def find_by_token_hash(self, token_hash):
        return self._find_by(GroupInvite.token_hash, token_hash)

    def create_invite(self, group_id, created_by, code_hash, token_hash, expires_at):
        with session_scope() as session:
            invite = GroupInvite(
                group_id=group_id,
                created_by=created_by,
                code_hash=code_hash,
                token_hash=token_hash,
                expires_at=parse_datetime(expires_at),
            )
            session.add(invite)
            session.flush()
            return self._serialize(invite)

    def update_invite(self, invite_id, fields):
        unexpected_fields = set(fields) - self.ALLOWED_UPDATE_FIELDS
        if unexpected_fields:
            raise ValueError("Campos nao permitidos")

        with session_scope() as session:
            invite = session.get(GroupInvite, invite_id)
            if invite is None:
                return None
            for name, value in fields.items():
                setattr(invite, name, parse_datetime(value) if name.endswith("_at") else value or None)
            session.flush()
            return self._serialize(invite)
