from unittest.mock import Mock

from utils.cache import TTLMemoryCache
from utils.sheet_records_cache import get_sheet_records, invalidate_sheet_records


def test_get_sheet_records_reuses_cached_rows(monkeypatch):
    sheet = Mock()
    sheet.get_all_records.return_value = [{"id": "place-1"}]
    monkeypatch.setattr("utils.sheet_records_cache.data_cache", TTLMemoryCache())

    first = get_sheet_records("places", sheet)
    second = get_sheet_records("places", sheet)

    assert first == second
    sheet.get_all_records.assert_called_once()


def test_get_sheet_records_returns_defensive_copy(monkeypatch):
    sheet = Mock()
    sheet.get_all_records.return_value = [{"id": "place-1"}]
    monkeypatch.setattr("utils.sheet_records_cache.data_cache", TTLMemoryCache())

    first = get_sheet_records("places", sheet)
    first[0]["id"] = "changed"

    assert get_sheet_records("places", sheet) == [{"id": "place-1"}]


def test_invalidate_sheet_records_forces_refresh(monkeypatch):
    sheet = Mock()
    sheet.get_all_records.side_effect = [[{"id": "place-1"}], [{"id": "place-2"}]]
    monkeypatch.setattr("utils.sheet_records_cache.data_cache", TTLMemoryCache())

    assert get_sheet_records("places", sheet) == [{"id": "place-1"}]
    invalidate_sheet_records("places")

    assert get_sheet_records("places", sheet) == [{"id": "place-2"}]
    assert sheet.get_all_records.call_count == 2
