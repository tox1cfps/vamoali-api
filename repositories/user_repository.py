from sqlalchemy import select

from database import session_scope
from models import User
from repositories.base import model_to_dict


class UserRepository:
    COLUMNS = [
        "id",
        "username",
        "email",
        "password_hash",
        "created_at",
        "last_unvisited_reminder_at",
        "unvisited_reminders_enabled",
    ]

    def find_by_email(self, email):
        with session_scope() as session:
            user = session.scalar(select(User).where(User.email == email))
            return model_to_dict(user, self.COLUMNS) if user else None

    def find_by_id(self, id):
        with session_scope() as session:
            user = session.get(User, id)
            return model_to_dict(user, self.COLUMNS) if user else None

    def find_by_ids(self, ids):
        with session_scope() as session:
            users = session.scalars(select(User).where(User.id.in_(set(ids)))).all()
            return {user.id: model_to_dict(user, self.COLUMNS) for user in users}

    def create_user(self, username, email, password_hash):
        with session_scope() as session:
            user = User(username=username, email=email, password_hash=password_hash)
            session.add(user)
            session.flush()
            return {"id": user.id, "username": user.username}

    def update_password(self, email, new_password_hash):
        with session_scope() as session:
            user = session.scalar(select(User).where(User.email == email))
            if user is None:
                return False
            user.password_hash = new_password_hash
            return True
