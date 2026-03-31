import os

from dotenv import load_dotenv


load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = _require_env("TELEGRAM_BOT_TOKEN")

GOOGLE_SERVICE_ACCOUNT_FILE = _require_env("GOOGLE_SERVICE_ACCOUNT_FILE")
GOOGLE_SPREADSHEET_ID = _require_env("GOOGLE_SPREADSHEET_ID")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Sheet1")

# Event settings
REMINDER_DURATION_MINUTES = int(os.getenv("REMINDER_DURATION_MINUTES", "60"))

