import asyncio
from datetime import datetime
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials


def _append_row_sync(
    *,
    service_account_file: str,
    spreadsheet_id: str,
    worksheet_name: str,
    style: str,
    date_iso: str,
    time_hhmm: str,
) -> None:
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(service_account_file, scopes=scopes)
    client = gspread.authorize(creds)

    spreadsheet = client.open_by_key(spreadsheet_id)
    worksheet = spreadsheet.worksheet(worksheet_name)

    # Ensure header row exists.
    try:
        first_row = worksheet.row_values(1)
    except gspread.exceptions.APIError:
        first_row = []

    if not first_row:
        worksheet.append_row(["Стиль ногтей", "Дата", "Время"], value_input_option="USER_ENTERED")

    worksheet.append_row([style, date_iso, time_hhmm], value_input_option="USER_ENTERED")


async def append_reminder_to_google_sheets(
    *,
    service_account_file: str,
    spreadsheet_id: str,
    worksheet_name: str,
    style: str,
    date_iso: str,
    time_hhmm: str,
) -> None:
    await asyncio.to_thread(
        _append_row_sync,
        service_account_file=service_account_file,
        spreadsheet_id=spreadsheet_id,
        worksheet_name=worksheet_name,
        style=style,
        date_iso=date_iso,
        time_hhmm=time_hhmm,
    )

