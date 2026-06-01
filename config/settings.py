from dotenv import load_dotenv
import os

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
SHEET_NAME = os.getenv("SHEET_NAME")
FERNET_KEY = os.getenv("FERNET_KEY")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

CREDENTIALS_FILE = "credentials.json"

USERS_SHEET = "users"
PLACES_SHEET = "places"