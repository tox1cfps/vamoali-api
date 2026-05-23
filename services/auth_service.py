from repositories.user_repository import UserRepository
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from config.settings import JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRATION_HOURS


class AuthService:
    def __init__(self):
        self.user_repo = UserRepository()

    def _generate_token(self, user_id):
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
        }        

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    @staticmethod
    def decode_token(token):
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    def register_user(self, username, email, password):
        check_email = self.user_repo.find_by_email(email)

        if check_email is not None:
            raise ValueError("E-mail já cadastrado")
        
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        user = self.user_repo.create_user(username, email, password_hash)

        token = self._generate_token(user["id"])
        return {"user": user, "token": token}

    def login_user(self, email, password):
        check_email = self.user_repo.find_by_email(email)
        
        if check_email is None:
            raise ValueError("Credenciais Inválidas")
        
        password_match = bcrypt.checkpw(password.encode("utf-8"), check_email["password_hash"].encode("utf-8"))
        
        if not password_match:
            raise ValueError("Credenciais Inválidas")

        user = {"id": check_email["id"], "username": check_email["username"], "email": check_email["email"]}
        token = self._generate_token(check_email["id"])
        return {"user": user, "token": token}