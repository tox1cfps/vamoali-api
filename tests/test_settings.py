from unittest.mock import Mock

import pytest

import config.settings as settings
from database import _normalized_database_url


def test_validate_settings_accepts_test_environment():
    settings.validate_settings()


def test_validate_settings_rejects_short_jwt_secret(monkeypatch):
    monkeypatch.setattr(settings, "JWT_SECRET", "short")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        settings.validate_settings()


def test_validate_settings_requires_google_credentials(monkeypatch):
    monkeypatch.setattr(settings, "REPORT_SHEET_NAME", "report")
    monkeypatch.setattr(settings, "GOOGLE_CREDENTIALS_JSON", None)
    monkeypatch.setattr(settings, "_credentials_file", Mock(return_value=Mock(is_file=lambda: False)))
    with pytest.raises(RuntimeError, match="GOOGLE"):
        settings.validate_settings()


def test_validate_settings_rejects_invalid_fernet_key(monkeypatch):
    monkeypatch.setattr(settings, "FERNET_KEY", "invalid")
    with pytest.raises(RuntimeError, match="FERNET_KEY"):
        settings.validate_settings()


def test_validate_settings_rejects_invalid_google_credentials_json(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CREDENTIALS_JSON", "credentials.json")
    with pytest.raises(RuntimeError, match="JSON valido"):
        settings.validate_settings()


def test_validate_settings_requires_backup_key_when_email_backup_is_enabled(monkeypatch):
    monkeypatch.setattr(settings, "BACKUP_EMAIL", "backup@example.com")
    monkeypatch.setattr(settings, "BACKUP_ENCRYPTION_KEY", None)
    with pytest.raises(RuntimeError, match="BACKUP_ENCRYPTION_KEY"):
        settings.validate_settings()


def test_database_url_must_be_configured():
    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        _normalized_database_url(None)
