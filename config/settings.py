import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
SHEET_NAME = os.getenv("SHEET_NAME")
FERNET_KEY = os.getenv("FERNET_KEY")
EMAIL_PAYLOAD_ENCRYPTION_KEY = os.getenv("EMAIL_PAYLOAD_ENCRYPTION_KEY") or FERNET_KEY
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
REDIS_URL = os.getenv("REDIS_URL")
DATABASE_URL = os.getenv("DATABASE_URL")
ENABLE_PASSWORD_RESET = os.getenv("ENABLE_PASSWORD_RESET", "false").casefold() == "true"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "2"))
SHARING_INVITE_EXPIRATION_HOURS = int(os.getenv("SHARING_INVITE_EXPIRATION_HOURS", "24"))
PASSWORD_RESET_URL = os.getenv("PASSWORD_RESET_URL", "http://localhost:5000/auth.html")
PASSWORD_RESET_EXPIRATION_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRATION_MINUTES", "15"))
LOGIN_CACHE_TTL_SECONDS = int(os.getenv("LOGIN_CACHE_TTL_SECONDS", "900"))
SHEETS_CACHE_TTL_SECONDS = int(os.getenv("SHEETS_CACHE_TTL_SECONDS", "15"))
REDIS_SOCKET_TIMEOUT_SECONDS = float(os.getenv("REDIS_SOCKET_TIMEOUT_SECONDS", "2"))

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VamoAli")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").casefold() == "true"
BACKUP_EMAIL = os.getenv("BACKUP_EMAIL")
BACKUP_DIR = os.getenv("BACKUP_DIR", "backups")
BACKUP_ENCRYPTION_KEY = os.getenv("BACKUP_ENCRYPTION_KEY")
EMAIL_WORKER_POLL_SECONDS = int(os.getenv("EMAIL_WORKER_POLL_SECONDS", "5"))
EMAIL_MAX_ATTEMPTS = int(os.getenv("EMAIL_MAX_ATTEMPTS", "5"))
UNVISITED_REMINDER_DAYS = int(os.getenv("UNVISITED_REMINDER_DAYS", "3"))
REPORT_SHEET_NAME = os.getenv("REPORT_SHEET_NAME")

CREDENTIALS_FILE = "credentials.json"

USERS_SHEET = "users"
PLACES_SHEET = "places"
GROUPS_SHEET = "groups"
GROUP_MEMBERS_SHEET = "group_members"
GROUP_INVITES_SHEET = "group_invites"


def _credentials_file():
    return Path(GOOGLE_APPLICATION_CREDENTIALS or CREDENTIALS_FILE)


def validate_settings():
    missing = [
        name
        for name, value in {
            "JWT_SECRET": JWT_SECRET,
            "DATABASE_URL": DATABASE_URL,
            "EMAIL_PAYLOAD_ENCRYPTION_KEY": EMAIL_PAYLOAD_ENCRYPTION_KEY,
        }.items()
        if not value
    ]

    if GOOGLE_CREDENTIALS_JSON:
        try:
            json.loads(GOOGLE_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_CREDENTIALS_JSON deve conter um JSON valido") from exc

    if REPORT_SHEET_NAME and not GOOGLE_CREDENTIALS_JSON and not _credentials_file().is_file():
        missing.append("GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")

    if BACKUP_EMAIL and not BACKUP_ENCRYPTION_KEY:
        missing.append("BACKUP_ENCRYPTION_KEY")

    if missing:
        raise RuntimeError(f"Variaveis de ambiente ausentes: {', '.join(missing)}")

    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET deve possuir pelo menos 32 caracteres")

    if FERNET_KEY:
        try:
            Fernet(FERNET_KEY.encode())
        except (TypeError, ValueError) as exc:
            raise RuntimeError("FERNET_KEY possui formato invalido") from exc

    if BACKUP_ENCRYPTION_KEY:
        try:
            Fernet(BACKUP_ENCRYPTION_KEY.encode())
        except (TypeError, ValueError) as exc:
            raise RuntimeError("BACKUP_ENCRYPTION_KEY possui formato invalido") from exc

    try:
        Fernet(EMAIL_PAYLOAD_ENCRYPTION_KEY.encode())
    except (TypeError, ValueError) as exc:
        raise RuntimeError("EMAIL_PAYLOAD_ENCRYPTION_KEY possui formato invalido") from exc
