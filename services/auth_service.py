import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config.settings import JWT_ALGORITHM, JWT_EXPIRATION_HOURS, JWT_SECRET, PASSWORD_RESET_EXPIRATION_MINUTES
from repositories.user_repository import UserRepository
from utils.mailer import send_password_reset_email
from utils.validation import normalize_email, validate_string


class AuthService:
    _reset_tokens = {}
    RESET_REQUEST_RESPONSE = {
        "success": True,
        "message": "Se a conta existir, enviaremos instrucoes para redefinir a senha.",
    }

    def __init__(self):
        self.user_repo = UserRepository()

    @classmethod
    def _cleanup_reset_tokens(cls):
        now = datetime.now(timezone.utc)
        expired = [token_hash for token_hash, data in cls._reset_tokens.items() if data["expires_at"] <= now]

        for token_hash in expired:
            cls._reset_tokens.pop(token_hash, None)

    @staticmethod
    def _hash_reset_token(token):
        if not isinstance(token, str) or not token:
            raise ValueError("Token invalido ou expirado")
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_password_strength(password):
        if not isinstance(password, str) or len(password) < 8:
            raise ValueError("A senha precisa ter no minimo 8 caracteres")

        if len(password.encode("utf-8")) > 72:
            raise ValueError("A senha precisa ter no maximo 72 bytes")

        if not any(char.isupper() for char in password):
            raise ValueError("A senha precisa ter pelo menos uma letra maiuscula")

        if not any(char.isdigit() for char in password):
            raise ValueError("A senha precisa ter pelo menos um numero")

        special_chars = "!@#$%^&*()_+-=[]{}|;:,.<>?"
        if not any(char in special_chars for char in password):
            raise ValueError("A senha precisa ter pelo menos um caractere especial")

    @classmethod
    def _create_reset_token(cls, email):
        cls._cleanup_reset_tokens()
        token = secrets.token_urlsafe(32)
        token_hash = cls._hash_reset_token(token)
        cls._reset_tokens[token_hash] = {
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRATION_MINUTES),
            "email": email,
        }
        return token, token_hash

    def request_reset_password(self, email):
        email = normalize_email(email)
        if self.user_repo.find_by_email(email) is None:
            return self.RESET_REQUEST_RESPONSE

        token, token_hash = self._create_reset_token(email)
        try:
            send_password_reset_email(email, token)
        except Exception as exc:
            self.__class__._reset_tokens.pop(token_hash, None)
            raise RuntimeError("Nao foi possivel enviar o email de redefinicao") from exc

        return self.RESET_REQUEST_RESPONSE

    def reset_password(self, token, new_password):
        self.__class__._cleanup_reset_tokens()
        token_hash = self._hash_reset_token(token)
        token_data = self.__class__._reset_tokens.get(token_hash)
        if token_data is None:
            raise ValueError("Token invalido ou expirado")

        self._validate_password_strength(new_password)
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        updated = self.user_repo.update_password(token_data["email"], password_hash)
        if not updated:
            raise LookupError("Usuario nao encontrado")

        self.__class__._reset_tokens.pop(token_hash, None)
        return {"success": True, "message": "Senha atualizada com sucesso"}

    def _generate_token(self, user_id):
        payload = {
            "sub": user_id,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_token(token):
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])

    def register_user(self, username, email, password):
        username = validate_string(username, "Nome de usuario", required=True, max_length=80)
        email = normalize_email(email)
        check_email = self.user_repo.find_by_email(email)
        if check_email is not None:
            raise ValueError("E-mail ja cadastrado")

        self._validate_password_strength(password)
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = self.user_repo.create_user(username, email, password_hash)
        token = self._generate_token(user["id"])
        return {"user": user, "token": token}

    def login_user(self, email, password):
        email = normalize_email(email)
        if not isinstance(password, str):
            raise ValueError("Credenciais invalidas")

        check_email = self.user_repo.find_by_email(email)
        if check_email is None:
            raise ValueError("Credenciais invalidas")

        password_match = bcrypt.checkpw(password.encode("utf-8"), check_email["password_hash"].encode("utf-8"))
        if not password_match:
            raise ValueError("Credenciais invalidas")

        user = {"id": check_email["id"], "username": check_email["username"]}
        token = self._generate_token(check_email["id"])
        return {"user": user, "token": token}
