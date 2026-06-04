import uuid
from datetime import datetime, timezone

from config.settings import PLACES_SHEET
from utils.sheet_records_cache import get_sheet_records, invalidate_sheet_records
from utils.sheets_client import get_worksheet


class PlaceRepository:

    COLUMNS = [
        "id",
        "user_id",
        "name",
        "maps_url",
        "visited",
        "feedback",
        "created_at",
        "updated_at",
        "photo_url",
        "category",
        "favorited",
        "rating",
    ]

    def __init__(self):
        self.sheet = get_worksheet(PLACES_SHEET)

    def _get_all_rows(self):
        return get_sheet_records(PLACES_SHEET, self.sheet)

    def find_by_id(self, id):
        rows = self._get_all_rows()

        for row in rows:
            if row["id"] == id:
                return row

        return None

    def find_all_by_user(self, user_id):
        rows = self._get_all_rows()

        ids = []

        for row in rows:
            if row["user_id"] == user_id:
                ids.append(row)

        return ids

    def find_all_by_users(self, user_ids):
        allowed_ids = set(user_ids)

        return [row for row in self._get_all_rows() if row["user_id"] in allowed_ids]

    def create_place(self, user_id, name, maps_url, category, photo_url=""):
        id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        self.sheet.append_row(
            [id, user_id, name, maps_url, False, "", now, now, photo_url, category, False, ""],
            value_input_option="RAW",
        )
        invalidate_sheet_records(PLACES_SHEET)

        return {
            "id": id,
            "user_id": user_id,
            "name": name,
            "maps_url": maps_url,
            "visited": False,
            "feedback": "",
            "created_at": now,
            "updated_at": now,
            "photo_url": photo_url,
            "category": category,
            "favorited": False,
            "rating": "",
        }

    def _find_row_index(self, place_id):
        rows = self._get_all_rows()
        for i, row in enumerate(rows):
            if row["id"] == place_id:
                return i + 2
        return None

    def delete_place(self, place_id):
        row = self._find_row_index(place_id)
        if row is None:
            return False
        self.sheet.delete_rows(row)
        invalidate_sheet_records(PLACES_SHEET)
        return True

    def update_place(self, place_id, fields):
        state = None
        row = None
        for index, candidate in enumerate(self._get_all_rows()):
            if candidate["id"] == place_id:
                state = candidate
                row = index + 2
                break

        if state is None:
            return None

        fields = {**fields, "updated_at": datetime.now(timezone.utc).isoformat()}
        updated = {**state, **fields}

        new_row = [str(updated.get(col, "")) for col in self.COLUMNS]
        self.sheet.update([new_row], f"A{row}", raw=True)
        invalidate_sheet_records(PLACES_SHEET)

        return updated
