import uuid
from datetime import datetime, timezone

from config.settings import GROUPS_SHEET
from utils.sheets_client import get_worksheet


class GroupRepository:
    def __init__(self):
        self.sheet = get_worksheet(GROUPS_SHEET)

    def _get_all_rows(self):
        return self.sheet.get_all_records()

    def find_by_id(self, group_id):
        for row in self._get_all_rows():
            if row["id"] == group_id:
                return row

        return None

    def create_group(self, created_by):
        group_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        self.sheet.append_row([group_id, created_by, created_at], value_input_option="RAW")

        return {"id": group_id, "created_by": created_by, "created_at": created_at}
