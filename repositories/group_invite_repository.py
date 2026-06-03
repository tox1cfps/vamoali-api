import uuid
from datetime import datetime, timezone

from config.settings import GROUP_INVITES_SHEET
from utils.sheets_client import get_worksheet


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

    ALLOWED_UPDATE_FIELDS = {
        "accepted_at",
        "accepted_by",
        "revoked_at",
    }

    def __init__(self):
        self.sheet = get_worksheet(GROUP_INVITES_SHEET)

    def _get_all_rows(self):
        return self.sheet.get_all_records()

    def find_by_id(self, invite_id):
        for invite in self._get_all_rows():
            if invite["id"] == invite_id:
                return invite

        return None

    def find_by_code_hash(self, code_hash):
        for invite in self._get_all_rows():
            if invite["code_hash"] == code_hash:
                return invite

        return None

    def find_by_token_hash(self, token_hash):
        for invite in self._get_all_rows():
            if invite["token_hash"] == token_hash:
                return invite

        return None

    def create_invite(
        self,
        group_id,
        created_by,
        code_hash,
        token_hash,
        expires_at,
    ):
        invite_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        invite = {
            "id": invite_id,
            "group_id": group_id,
            "created_by": created_by,
            "code_hash": code_hash,
            "token_hash": token_hash,
            "created_at": created_at,
            "expires_at": expires_at,
            "accepted_at": "",
            "accepted_by": "",
            "revoked_at": "",
        }

        self.sheet.append_row(
            [invite[column] for column in self.COLUMNS],
            value_input_option="RAW",
        )

        return invite

    def update_invite(self, invite_id, fields):
        unexpected_fields = set(fields) - self.ALLOWED_UPDATE_FIELDS
        if unexpected_fields:
            raise ValueError("Campos nao permitidos")

        invites = self._get_all_rows()

        for index, invite in enumerate(invites):
            if invite["id"] == invite_id:
                updated = {**invite, **fields}
                row_number = index + 2
                new_row = [str(updated.get(column, "")) for column in self.COLUMNS]

                self.sheet.update(
                    [new_row],
                    f"A{row_number}",
                    raw=True,
                )

                return updated

        return None
