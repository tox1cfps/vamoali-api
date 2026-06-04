from sqlalchemy import select

from database import session_scope
from models import GroupMember, utcnow
from repositories.base import model_to_dict


class GroupMemberRepository:
    COLUMNS = ["id", "group_id", "user_id", "joined_at", "left_at"]

    def _serialize(self, member):
        return model_to_dict(member, self.COLUMNS)

    def create_member(self, group_id, user_id):
        with session_scope() as session:
            member = GroupMember(group_id=group_id, user_id=user_id)
            session.add(member)
            session.flush()
            return self._serialize(member)

    def find_active_by_user(self, user_id):
        with session_scope() as session:
            member = session.scalar(
                select(GroupMember).where(GroupMember.user_id == user_id, GroupMember.left_at.is_(None))
            )
            return self._serialize(member) if member else None

    def find_active_by_group(self, group_id):
        with session_scope() as session:
            members = session.scalars(
                select(GroupMember).where(GroupMember.group_id == group_id, GroupMember.left_at.is_(None))
            ).all()
            return [self._serialize(member) for member in members]

    def deactivate_member(self, group_id, user_id):
        with session_scope() as session:
            member = session.scalar(
                select(GroupMember).where(
                    GroupMember.group_id == group_id,
                    GroupMember.user_id == user_id,
                    GroupMember.left_at.is_(None),
                )
            )
            if member is None:
                return None
            member.left_at = utcnow()
            session.flush()
            return self._serialize(member)
