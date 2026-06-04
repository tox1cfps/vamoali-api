import json
from functools import lru_cache

import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_CREDENTIALS_JSON, REPORT_SHEET_NAME, SHEET_NAME, _credentials_file

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


@lru_cache(maxsize=1)
def get_spreadsheet():
    if GOOGLE_CREDENTIALS_JSON:
        creds = Credentials.from_service_account_info(
            json.loads(GOOGLE_CREDENTIALS_JSON),
            scopes=SCOPES,
        )
    else:
        creds = Credentials.from_service_account_file(_credentials_file(), scopes=SCOPES)

    client = gspread.authorize(creds)

    return client.open(SHEET_NAME)


@lru_cache(maxsize=None)
def get_worksheet(sheet_name):
    sheet = get_spreadsheet().worksheet(sheet_name)

    return sheet


@lru_cache(maxsize=1)
def get_report_spreadsheet():
    if not REPORT_SHEET_NAME:
        raise RuntimeError("REPORT_SHEET_NAME nao configurado")
    if GOOGLE_CREDENTIALS_JSON:
        creds = Credentials.from_service_account_info(json.loads(GOOGLE_CREDENTIALS_JSON), scopes=SCOPES)
    else:
        creds = Credentials.from_service_account_file(_credentials_file(), scopes=SCOPES)
    return gspread.authorize(creds).open(REPORT_SHEET_NAME)


def clear_sheets_cache():
    get_worksheet.cache_clear()
    get_spreadsheet.cache_clear()
    get_report_spreadsheet.cache_clear()
