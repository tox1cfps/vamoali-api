import re
from urllib.parse import urlparse

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
ALLOWED_CATEGORIES = {
    "",
    "Restaurante",
    "Cafe",
    "Café",
    "Bar",
    "Lazer",
    "Compras",
    "Ao ar livre",
    "Cinema",
    "Outro",
}


def validate_string(value, field_name, *, required=False, max_length=None):
    if not isinstance(value, str):
        if value is None and not required:
            return ""
        raise ValueError(f"{field_name} invalido")

    value = value.strip()
    if required and not value:
        raise ValueError(f"{field_name} obrigatorio")
    if max_length is not None and len(value) > max_length:
        raise ValueError(f"{field_name} muito longo")
    return value


def normalize_email(value):
    email = validate_string(value, "E-mail", required=True, max_length=254).casefold()
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("E-mail invalido")
    return email


def validate_https_url(value, field_name, *, required=False):
    value = validate_string(value, field_name, required=required, max_length=2048)
    if not value:
        return ""

    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{field_name} deve ser uma URL https valida")
    return value


def validate_category(value):
    category = validate_string(value, "Categoria", max_length=40)
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("Categoria invalida")
    return category
