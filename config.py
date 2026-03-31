import json
import os

from dotenv import load_dotenv


load_dotenv()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


BOT_TOKEN = _require_env("TELEGRAM_BOT_TOKEN")

def _load_service_account_info() -> dict:
    """
    Railway удобнее хранить JSON как строку переменной окружения.
    Ожидаем GOOGLE_SERVICE_ACCOUNT_JSON (строка JSON).
    """
    json_str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if json_str:
        return json.loads(json_str)

    # Backward-compatible fallback (если вдруг оставить путь к файлу).
    file_path = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE")
    if file_path:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON (or GOOGLE_SERVICE_ACCOUNT_FILE fallback).")


GOOGLE_SERVICE_ACCOUNT_INFO = _load_service_account_info()

GOOGLE_SPREADSHEET_ID = _require_env("GOOGLE_SPREADSHEET_ID")
GOOGLE_WORKSHEET_NAME = os.getenv("GOOGLE_WORKSHEET_NAME", "Sheet1")

# Event settings
REMINDER_DURATION_MINUTES = int(os.getenv("REMINDER_DURATION_MINUTES", "60"))

