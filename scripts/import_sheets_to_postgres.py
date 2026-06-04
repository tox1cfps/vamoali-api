from datetime import datetime, timezone

from sqlalchemy import func, select

from config.settings import GROUP_INVITES_SHEET, GROUP_MEMBERS_SHEET, GROUPS_SHEET, PLACES_SHEET, USERS_SHEET
from database import session_scope
from models import Group, GroupInvite, GroupMember, Place, User
from repositories.base import parse_datetime
from utils.encryption import decrypt
from utils.sheets_client import get_worksheet


def maybe_decrypt(value):
    try:
        return decrypt(value)
    except Exception:
        return value


def as_bool(value):
    return value is True or str(value).strip().casefold() == "true"


def as_rating(value):
    return int(value) if str(value).strip() else None


def rows(sheet_name):
    return get_worksheet(sheet_name).get_all_records()


def migration_status():
    sheet_counts = {
        "users": len(rows(USERS_SHEET)),
        "places": len(rows(PLACES_SHEET)),
        "groups": len(rows(GROUPS_SHEET)),
        "group_members": len(rows(GROUP_MEMBERS_SHEET)),
        "group_invites": len(rows(GROUP_INVITES_SHEET)),
    }
    with session_scope() as session:
        postgres_counts = {
            "users": session.scalar(select(func.count()).select_from(User)),
            "places": session.scalar(select(func.count()).select_from(Place)),
            "groups": session.scalar(select(func.count()).select_from(Group)),
            "group_members": session.scalar(select(func.count()).select_from(GroupMember)),
            "group_invites": session.scalar(select(func.count()).select_from(GroupInvite)),
        }
    return {"sheets": sheet_counts, "postgres": postgres_counts, "matches": sheet_counts == postgres_counts}


def import_all():
    counts = {}
    with session_scope() as session:
        counts["users"] = 0
        for row in rows(USERS_SHEET):
            if session.get(User, row["id"]):
                continue
            session.add(
                User(
                    id=row["id"],
                    username=maybe_decrypt(row["username"]),
                    email=maybe_decrypt(row["email"]),
                    password_hash=row["password_hash"],
                    created_at=parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
                )
            )
            counts["users"] += 1
        session.flush()

        counts["places"] = 0
        for row in rows(PLACES_SHEET):
            if session.get(Place, row["id"]):
                continue
            session.add(
                Place(
                    id=row["id"],
                    user_id=row["user_id"],
                    name=row["name"],
                    maps_url=row["maps_url"],
                    visited=as_bool(row.get("visited")),
                    feedback=row.get("feedback", ""),
                    created_at=parse_datetime(row.get("created_at")) or datetime.now(timezone.utc),
                    updated_at=parse_datetime(row.get("updated_at")) or datetime.now(timezone.utc),
                    photo_url=row.get("photo_url", ""),
                    category=row["category"],
                    favorited=as_bool(row.get("favorited")),
                    rating=as_rating(row.get("rating")),
                )
            )
            counts["places"] += 1
        session.flush()

        for sheet_name, model, fields in [
            (GROUPS_SHEET, Group, ["id", "created_by", "created_at"]),
            (GROUP_MEMBERS_SHEET, GroupMember, ["id", "group_id", "user_id", "joined_at", "left_at"]),
            (
                GROUP_INVITES_SHEET,
                GroupInvite,
                [
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
                ],
            ),
        ]:
            counts[model.__tablename__] = 0
            for row in rows(sheet_name):
                if session.get(model, row["id"]):
                    continue
                values = {}
                for field in fields:
                    value = row.get(field)
                    values[field] = parse_datetime(value) if field.endswith("_at") else (value or None)
                session.add(model(**values))
                counts[model.__tablename__] += 1
            session.flush()
    return counts


if __name__ == "__main__":
    print(import_all())
