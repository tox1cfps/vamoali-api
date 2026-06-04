import random
from datetime import timedelta

from sqlalchemy import select

from config.settings import UNVISITED_REMINDER_DAYS
from database import session_scope
from models import Place, User, utcnow
from repositories.email_job_repository import EmailJobRepository


def schedule_reminders():
    cutoff = utcnow() - timedelta(days=UNVISITED_REMINDER_DAYS)
    queued = 0
    jobs = EmailJobRepository()

    with session_scope() as session:
        users = session.scalars(
            select(User).where(
                User.unvisited_reminders_enabled.is_(True),
                (User.last_unvisited_reminder_at.is_(None) | (User.last_unvisited_reminder_at <= cutoff)),
            )
        ).all()
        for user in users:
            places = session.scalars(select(Place).where(Place.user_id == user.id, Place.visited.is_(False))).all()
            if not places:
                continue
            today = utcnow().date().isoformat()
            job_id = jobs.enqueue(
                "unvisited_reminder",
                user.email,
                {"count": len(places), "suggestion": random.choice(places).name},
                f"unvisited:{user.id}:{today}",
            )
            if job_id:
                user.last_unvisited_reminder_at = utcnow()
                queued += 1
    return queued


if __name__ == "__main__":
    print(f"{schedule_reminders()} lembrete(s) agendado(s)")
