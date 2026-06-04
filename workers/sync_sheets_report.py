from collections import Counter

from gspread.exceptions import WorksheetNotFound
from sqlalchemy import func, select

from database import session_scope
from models import Group, GroupMember, Place, User
from utils.sheets_client import get_report_spreadsheet


def replace_worksheet(spreadsheet, name, rows):
    try:
        worksheet = spreadsheet.worksheet(name)
        worksheet.clear()
    except WorksheetNotFound:
        worksheet = spreadsheet.add_worksheet(title=name, rows=max(len(rows) + 10, 100), cols=10)
    worksheet.update(rows, "A1", raw=True)


def sync_report():
    with session_scope() as session:
        users_count = session.scalar(select(func.count()).select_from(User))
        places = session.scalars(select(Place)).all()
        groups_count = session.scalar(select(func.count()).select_from(Group))
        active_members_count = session.scalar(
            select(func.count()).select_from(GroupMember).where(GroupMember.left_at.is_(None))
        )

    categories = Counter(place.category for place in places)
    metrics = [
        ["metrica", "valor"],
        ["usuarios", users_count],
        ["lugares", len(places)],
        ["lugares_visitados", sum(place.visited for place in places)],
        ["lugares_pendentes", sum(not place.visited for place in places)],
        ["grupos", groups_count],
        ["membros_ativos", active_members_count],
    ]
    category_rows = [["categoria", "quantidade"], *sorted(categories.items())]
    place_rows = [
        ["nome", "categoria", "visitado", "favorito", "avaliacao", "criado_em"],
        *[
            [
                place.name,
                place.category,
                place.visited,
                place.favorited,
                place.rating or "",
                place.created_at.isoformat(),
            ]
            for place in places
        ],
    ]

    spreadsheet = get_report_spreadsheet()
    replace_worksheet(spreadsheet, "metricas", metrics)
    replace_worksheet(spreadsheet, "categorias", category_rows)
    replace_worksheet(spreadsheet, "lugares", place_rows)
    return {"users": users_count, "places": len(places)}


if __name__ == "__main__":
    print(sync_report())
