from datetime import datetime


def serialize_value(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if value is None:
        return ""
    return value


def model_to_dict(model, columns):
    return {column: serialize_value(getattr(model, column)) for column in columns}


def parse_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)
