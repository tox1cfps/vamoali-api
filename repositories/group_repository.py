from database import session_scope
from models import Group
from repositories.base import model_to_dict


class GroupRepository:
    COLUMNS = ["id", "created_by", "created_at"]

    def find_by_id(self, group_id):
        with session_scope() as session:
            group = session.get(Group, group_id)
            return model_to_dict(group, self.COLUMNS) if group else None

    def create_group(self, created_by):
        with session_scope() as session:
            group = Group(created_by=created_by)
            session.add(group)
            session.flush()
            return model_to_dict(group, self.COLUMNS)
