from unittest.mock import Mock

import utils.sheets_client as sheets_client


def setup_function():
    sheets_client.clear_sheets_cache()


def teardown_function():
    sheets_client.clear_sheets_cache()


def test_get_spreadsheet_uses_json_credentials(monkeypatch):
    credentials = Mock()
    spreadsheet = Mock()
    client = Mock()
    client.open.return_value = spreadsheet
    factory = Mock(return_value=credentials)
    monkeypatch.setattr(sheets_client.Credentials, "from_service_account_info", factory)
    monkeypatch.setattr(sheets_client.gspread, "authorize", Mock(return_value=client))

    assert sheets_client.get_spreadsheet() is spreadsheet
    assert factory.call_args.args[0] == {"type": "service_account"}
    assert factory.call_args.kwargs["scopes"] == [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive.readonly",
    ]


def test_get_worksheet_selects_named_tab(monkeypatch):
    spreadsheet = Mock()
    worksheet = Mock()
    spreadsheet.worksheet.return_value = worksheet
    monkeypatch.setattr(sheets_client, "get_spreadsheet", lambda: spreadsheet)

    assert sheets_client.get_worksheet("places") is worksheet


def test_sheet_resources_are_reused(monkeypatch):
    spreadsheet = Mock()
    worksheet = Mock()
    spreadsheet.worksheet.return_value = worksheet
    monkeypatch.setattr(sheets_client, "get_spreadsheet", Mock(return_value=spreadsheet))

    assert sheets_client.get_worksheet("places") is worksheet
    assert sheets_client.get_worksheet("places") is worksheet
    spreadsheet.worksheet.assert_called_once_with("places")


def test_get_spreadsheet_can_use_credentials_file(monkeypatch):
    credentials = Mock()
    client = Mock()
    factory = Mock(return_value=credentials)
    monkeypatch.setattr(sheets_client, "GOOGLE_CREDENTIALS_JSON", None)
    monkeypatch.setattr(sheets_client.Credentials, "from_service_account_file", factory)
    monkeypatch.setattr(sheets_client.gspread, "authorize", Mock(return_value=client))

    sheets_client.get_spreadsheet()

    assert factory.called
