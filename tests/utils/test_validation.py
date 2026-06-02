import pytest

from utils.validation import normalize_email, validate_category, validate_https_url, validate_string


def test_normalize_email_strips_and_casefolds():
    assert normalize_email("  USER@Example.COM ") == "user@example.com"


@pytest.mark.parametrize("email", [None, "invalid", "@example.com"])
def test_normalize_email_rejects_invalid_values(email):
    with pytest.raises(ValueError):
        normalize_email(email)


def test_validate_string_handles_optional_and_limits():
    assert validate_string(None, "Campo") == ""
    with pytest.raises(ValueError):
        validate_string("too long", "Campo", max_length=3)


def test_validate_https_url_rejects_http_and_accepts_empty_optional_url():
    assert validate_https_url("", "URL") == ""
    with pytest.raises(ValueError):
        validate_https_url("http://example.com", "URL")


def test_validate_category_rejects_unknown_value():
    with pytest.raises(ValueError):
        validate_category("Desconhecida")
