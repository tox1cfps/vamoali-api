import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from config.settings import (
    JWT_ALGORITHM,
    JWT_EXPIRATION_HOURS,
    JWT_SECRET,
    LOGIN_CACHE_TTL_SECONDS,
    PASSWORD_RESET_EXPIRATION_MINUTES,
)
from repositories.email_job_repository import EmailJobRepository
from repositories.password_reset_repository import PasswordResetRepository
from repositories.user_repository import UserRepository
from utils.cache import login_cache
from utils.mailer import send_password_reset_email, send_welcome_email
from utils.validation import normalize_email, validate_string


class AuthService:
    RESET_REQUEST_RESPONSE = {
        "success": True,
        "message": "Se a conta existir, enviaremos instrucoes para redefinir a senha.",
    }

    def __init__(self):
        self.user_repo = UserRepository()
        self.reset_repo = PasswordResetRepository()
        self.email_job_repo = EmailJobRepository()
        self.login_cache = login_cache

    @staticmethod
    def _login_cache_key(email):
        return f"login:user:{email}"

    def _find_user_for_login(self, email):
        cache_key = self._login_cache_key(email)
        cached_user = self.login_cache.get(cache_key)
        if cached_user is not None:
            return cached_user

        user = self.user_repo.find_by_email(email)
        if user is not None:
            self.login_cache.set(cache_key, user, LOGIN_CACHE_TTL_SECONDS)

        return user

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

    def _create_reset_token(self, user_id):
        token = secrets.token_urlsafe(32)
        token_hash = self._hash_reset_token(token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=PASSWORD_RESET_EXPIRATION_MINUTES)
        self.reset_repo.create(token_hash, user_id, expires_at.isoformat())
        return token, token_hash

    def request_reset_password(self, email):
        email = normalize_email(email)
        user = self.user_repo.find_by_email(email)
        if user is None:
            return self.RESET_REQUEST_RESPONSE

        token, token_hash = self._create_reset_token(user["id"])
        try:
            send_password_reset_email(email, token)
        except Exception as exc:
            self.reset_repo.delete(token_hash)
            raise RuntimeError("Nao foi possivel enviar o email de redefinicao") from exc

        return self.RESET_REQUEST_RESPONSE

    def reset_password(self, token, new_password):
        token_hash = self._hash_reset_token(token)
        token_data = self.reset_repo.find_valid(token_hash)
        if token_data is None:
            raise ValueError("Token invalido ou expirado")

        self._validate_password_strength(new_password)
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = self.user_repo.find_by_id(token_data["user_id"])
        if user is None:
            raise LookupError("Usuario nao encontrado")
        updated = self.user_repo.update_password(user["email"], password_hash)
        if not updated:
            raise LookupError("Usuario nao encontrado")

        self.login_cache.delete(self._login_cache_key(user["email"]))
        self.reset_repo.consume(token_hash)
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
        try:
            send_welcome_email(email, username)
        except Exception:
            self.email_job_repo.enqueue("welcome", email, {"username": username}, f"welcome:{user['id']}")
        self.login_cache.delete(self._login_cache_key(email))
        token = self._generate_token(user["id"])
        return {"user": user, "token": token}

    def login_user(self, email, password):
        email = normalize_email(email)
        if not isinstance(password, str):
            raise ValueError("Credenciais invalidas")

        check_email = self._find_user_for_login(email)
        if check_email is None:
            raise ValueError("Credenciais invalidas")

        password_match = bcrypt.checkpw(password.encode("utf-8"), check_email["password_hash"].encode("utf-8"))
        if not password_match:
            raise ValueError("Credenciais invalidas")

        user = {"id": check_email["id"], "username": check_email["username"]}
        token = self._generate_token(check_email["id"])
        return {"user": user, "token": token}
