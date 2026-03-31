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


def _fold_ics_line(line: str, limit: int = 75) -> list[str]:
    """
    RFC 5545: строки длиной > 75 должны быть "folded":
    каждый последующий кусок начинается с пробела.
    """
    if len(line) <= limit:
        return [line]

    first = line[:limit]
    rest = line[limit:]
    parts = [first]

    while rest:
        chunk = rest[: limit - 1]
        parts.append(" " + chunk)
        rest = rest[limit - 1 :]

    return parts


def create_ics_text(*, style: str, date_iso: str, time_hhmm: str, duration_minutes: int = 60) -> str:
    """
    Creates a floating (local-time) ICS event suitable for iOS "Add to calendar" import.

    Key iOS behaviour:
      - No METHOD property at all -> iOS treats the file as a plain import
        and shows the "Add to Calendar" button.
      - METHOD:PUBLISH -> view-only, no Add button.
      - METHOD:REQUEST -> shown as an invite (with Organizer), no Add button either.
    """
    start_date = datetime.strptime(date_iso, "%Y-%m-%d").date()
    start_time = datetime.strptime(time_hhmm, "%H:%M").time()

    start_dt = datetime.combine(start_date, start_time)
    end_dt = start_dt + timedelta(minutes=duration_minutes)

    uid = f"{uuid.uuid4()}@manicure-bot"
    dtstamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")

    # Floating timestamps (no Z, no TZID) — device local time.
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")

    summary = f"Маникюр: {style}"
    description = "Напоминание от бота"

    raw_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Manicure Bot//Manicure Reminder//RU",
        "CALSCALE:GREGORIAN",
        # Намеренно НЕТ строки METHOD — это заставляет iOS показать кнопку
        # «Добавить в календарь» вместо интерфейса приглашения.
        "X-WR-CALNAME:Маникюр",
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{dtstamp}",
        "STATUS:CONFIRMED",
        "SEQUENCE:0",
        "TRANSP:OPAQUE",
        f"DTSTART:{dtstart}",
        f"DTEND:{dtend}",
        f"SUMMARY:{_escape_ics_text(summary)}",
        f"DESCRIPTION:{_escape_ics_text(description)}",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        "TRIGGER:-PT60M",
        f"DESCRIPTION:{_escape_ics_text(summary)}",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR",
    ]

    folded_lines: list[str] = []
    for line in raw_lines:
        folded_lines.extend(_fold_ics_line(line))

    # RFC 5545: lines separated by CRLF, trailing CRLF required.
    return "\r\n".join(folded_lines) + "\r\n"
