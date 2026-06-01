from utils.sheets_client import get_worksheet
from config.settings import USERS_SHEET
import uuid
from utils.encryption import encrypt, decrypt


def _maybe_decrypt(value):
    if value in (None, ""):
        return value

    try:
        return decrypt(value)
    except Exception:
        return value

class UserRepository:
    def __init__(self):
        self.sheet = get_worksheet(USERS_SHEET)

    def _get_all_rows(self):
        return self.sheet.get_all_records()
    
    def find_by_email(self, email):
        rows = self._get_all_rows()

        for row in rows:
            decrypted_email = _maybe_decrypt(row.get("email"))

            if decrypted_email == email:
                return {
                    **row,
                    "email": decrypted_email,
                    "username": _maybe_decrypt(row.get("username")),
                }
            
        return None
    
    def find_by_id(self, id):
        rows = self._get_all_rows()

        for row in rows:
            if row["id"] == id:
                return {
                    **row,
                    "email": _maybe_decrypt(row.get("email")),
                    "username": _maybe_decrypt(row.get("username")),
                }
            
        return None
    
    def create_user(self, username, email, password_hash):
        id = str(uuid.uuid4())
        self.sheet.append_row([id, encrypt(username), encrypt(email), password_hash])

        return {"id": id, "username": username}

    def update_password(self, email, new_password_hash):
        rows = self._get_all_rows()

        for index, row in enumerate(rows):
            decrypted_email = _maybe_decrypt(row.get("email"))

            if decrypted_email == email:
                sheet_row = index + 2
                self.sheet.update_cell(sheet_row, 4, new_password_hash)
                return True

        return False
