from utils.sheets_client import get_worksheet
from config.settings import USERS_SHEET
import uuid

class UserRepository:
    def __init__(self):
        self.sheet = get_worksheet(USERS_SHEET)

    def _get_all_rows(self):
        return self.sheet.get_all_records()
    
    def find_by_email(self, email):
        rows = self._get_all_rows()

        for row in rows:
            if row["email"] == email:
                return row
            
        return None
    
    def find_by_id(self, id):
        rows = self._get_all_rows()

        for row in rows:
            if row["id"] == id:
                return row
            
        return None
    
    def create_user(self, username, email, password_hash):
        id = str(uuid.uuid4())
        self.sheet.append_row([id, username, email, password_hash])

        return {"id":id, "username":username, "email":email}
