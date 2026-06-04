import uuid
from datetime import datetime, timezone

from config.settings import GROUP_MEMBERS_SHEET
from utils.sheet_records_cache import get_sheet_records, invalidate_sheet_records
from utils.sheets_client import get_worksheet


class GroupMemberRepository:
    COLUMNS = ["id", "group_id", "user_id", "joined_at", "left_at"]

    def __init__(self):
        self.sheet = get_worksheet(GROUP_MEMBERS_SHEET)

    def _get_all_rows(self):
        return get_sheet_records(GROUP_MEMBERS_SHEET, self.sheet)

    @staticmethod
    def _is_active(member):
        return member.get("left_at") in (None, "")

    def create_member(self, group_id, user_id):
        member_id = str(uuid.uuid4())
        joined_at = datetime.now(timezone.utc).isoformat()

        self.sheet.append_row([member_id, group_id, user_id, joined_at, ""], value_input_option="RAW")
        invalidate_sheet_records(GROUP_MEMBERS_SHEET)

        return {"id": member_id, "group_id": group_id, "user_id": user_id, "joined_at": joined_at, "left_at": ""}

    def find_active_by_user(self, user_id):
        for member in self._get_all_rows():
            if member["user_id"] == user_id and self._is_active(member):
                return member

        return None

    def find_active_by_group(self, group_id):
        return [member for member in self._get_all_rows() if member["group_id"] == group_id and self._is_active(member)]

    def deactivate_member(self, group_id, user_id):
        members = self._get_all_rows()

        for index, member in enumerate(members):
            if member["group_id"] == group_id and member["user_id"] == user_id and self._is_active(member):
                row_number = index + 2
                left_at = datetime.now(timezone.utc).isoformat()
                self.sheet.update_cell(row_number, 5, left_at)
                invalidate_sheet_records(GROUP_MEMBERS_SHEET)

                return {**member, "left_at": left_at}

        return None
