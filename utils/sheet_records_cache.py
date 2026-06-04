from copy import deepcopy

from config.settings import SHEETS_CACHE_TTL_SECONDS
from utils.cache import data_cache


def _cache_key(sheet_name):
    return f"sheets:records:{sheet_name}"


def get_sheet_records(sheet_name, worksheet):
    key = _cache_key(sheet_name)
    cached = data_cache.get(key)
    if cached is not None:
        return deepcopy(cached)

    rows = worksheet.get_all_records()
    data_cache.set(key, rows, SHEETS_CACHE_TTL_SECONDS)
    return deepcopy(rows)


def invalidate_sheet_records(sheet_name):
    data_cache.delete(_cache_key(sheet_name))
