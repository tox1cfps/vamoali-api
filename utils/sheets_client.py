import json

import gspread
from google.oauth2.service_account import Credentials

from config.settings import GOOGLE_CREDENTIALS_JSON, SHEET_NAME, _credentials_file

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]


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


def get_worksheet(sheet_name):
    sheet = get_spreadsheet().worksheet(sheet_name)

    return sheet
