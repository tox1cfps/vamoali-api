import os

import pytest

os.environ["SHEET_NAME"] = "test-sheet"
os.environ["JWT_SECRET"] = "test-only-secret-with-at-least-32-characters"
os.environ["FERNET_KEY"] = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="
os.environ["GOOGLE_CREDENTIALS_JSON"] = '{"type": "service_account"}'
os.environ["ENABLE_PASSWORD_RESET"] = "false"
os.environ["DATABASE_URL"] = "sqlite:///test-vamoali.db"


@pytest.fixture(autouse=True)
def reset_database_between_tests():
    from database import engine
    from models import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    yield

    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def clear_sheet_records_between_tests():
    from config.settings import GROUP_INVITES_SHEET, GROUP_MEMBERS_SHEET, GROUPS_SHEET, PLACES_SHEET, USERS_SHEET
    from utils.sheet_records_cache import invalidate_sheet_records

    for sheet_name in (USERS_SHEET, PLACES_SHEET, GROUPS_SHEET, GROUP_MEMBERS_SHEET, GROUP_INVITES_SHEET):
        invalidate_sheet_records(sheet_name)

    yield

    for sheet_name in (USERS_SHEET, PLACES_SHEET, GROUPS_SHEET, GROUP_MEMBERS_SHEET, GROUP_INVITES_SHEET):
        invalidate_sheet_records(sheet_name)


@pytest.fixture
def client():
    from app import app

    app.config.update(TESTING=True)
    return app.test_client()


@pytest.fixture
def authenticated_client(client, monkeypatch):
    monkeypatch.setattr("middleware.auth_middleware.AuthService.decode_token", lambda token: {"sub": "user-1"})
    client.environ_base["HTTP_AUTHORIZATION"] = "Bearer valid"
    return client
