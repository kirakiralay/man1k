import uuid
from datetime import datetime, timedelta


def _escape_ics_text(value: str) -> str:
    # RFC 5545 text escaping (subset).
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\n", "\\n")
        .replace(",", "\\,")
        .replace(";", "\\;")
    )


def create_ics_text(*, style: str, date_iso: str, time_hhmm: str, duration_minutes: int = 60) -> str:
    """
    Creates a floating (local-time) ICS event suitable for "Add to calendar" import.
    """
    start_date = datetime.strptime(date_iso, "%Y-%m-%d").date()
    start_time = datetime.strptime(time_hhmm, "%H:%M").time()

    start_dt = datetime.combine(start_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    uid = f"{uuid.uuid4()}@bot1"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    created = dtstamp
    last_modified = dtstamp

    # Floating timestamps: no "Z" suffix and no timezone identifiers.
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")

    summary = f"Маникюр: {style}"
    description = "Напоминание от бота"

    return "\r\n".join(
        [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//bot1//RU",
            "CALSCALE:GREGORIAN",
            "METHOD:REQUEST",
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"CREATED:{created}",
            f"LAST-MODIFIED:{last_modified}",
            f"DTSTART:{dtstart}",
            f"DTEND:{dtend}",
            f"SUMMARY:{_escape_ics_text(summary)}",
            f"DESCRIPTION:{_escape_ics_text(description)}",
            "END:VEVENT",
            "END:VCALENDAR",
        ]
    )

