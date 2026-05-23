import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config.settings import CREDENTIALS_FILE, SHEET_NAME

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

def get_spreadsheet():
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, SCOPES)

    client = gspread.authorize(creds)

    return client.open(SHEET_NAME)

def get_worksheet(sheet_name):
    sheet = get_spreadsheet().worksheet(sheet_name)

    return sheet
