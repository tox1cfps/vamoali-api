import json
import os
from pathlib import Path

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
SHEET_NAME = os.getenv("SHEET_NAME")
FERNET_KEY = os.getenv("FERNET_KEY")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
ENABLE_PASSWORD_RESET = os.getenv("ENABLE_PASSWORD_RESET", "false").casefold() == "true"
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "2"))
PASSWORD_RESET_URL = os.getenv("PASSWORD_RESET_URL", "http://localhost:5000/auth.html")
PASSWORD_RESET_EXPIRATION_MINUTES = int(os.getenv("PASSWORD_RESET_EXPIRATION_MINUTES", "15"))

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "VamoAli")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").casefold() == "true"

CREDENTIALS_FILE = "credentials.json"

USERS_SHEET = "users"
PLACES_SHEET = "places"


def _credentials_file():
    return Path(GOOGLE_APPLICATION_CREDENTIALS or CREDENTIALS_FILE)


def validate_settings():
    missing = [
        name
        for name, value in {
            "JWT_SECRET": JWT_SECRET,
            "SHEET_NAME": SHEET_NAME,
            "FERNET_KEY": FERNET_KEY,
        }.items()
        if not value
    ]

    if not GOOGLE_CREDENTIALS_JSON and not _credentials_file().is_file():
        missing.append("GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")

    if GOOGLE_CREDENTIALS_JSON:
        try:
            json.loads(GOOGLE_CREDENTIALS_JSON)
        except json.JSONDecodeError as exc:
            raise RuntimeError("GOOGLE_CREDENTIALS_JSON deve conter um JSON valido") from exc

    if ENABLE_PASSWORD_RESET:
        missing.extend(
            name
            for name, value in {
                "SMTP_HOST": SMTP_HOST,
                "SMTP_USER": SMTP_USER,
                "SMTP_PASSWORD": SMTP_PASSWORD,
                "SMTP_FROM_EMAIL": SMTP_FROM_EMAIL,
                "PASSWORD_RESET_URL": PASSWORD_RESET_URL,
            }.items()
            if not value
        )

    if missing:
        raise RuntimeError(f"Variaveis de ambiente ausentes: {', '.join(missing)}")

    if len(JWT_SECRET) < 32:
        raise RuntimeError("JWT_SECRET deve possuir pelo menos 32 caracteres")

    try:
        Fernet(FERNET_KEY.encode())
    except (TypeError, ValueError) as exc:
        raise RuntimeError("FERNET_KEY possui formato invalido") from exc
