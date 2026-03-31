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

    # Продолжающие строки начинаются с одного пробела.
    while rest:
        chunk = rest[: limit - 1]
        parts.append(" " + chunk)
        rest = rest[limit - 1 :]

    return parts


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

    # Floating timestamps: no "Z" suffix and no timezone identifiers.
    # Время с секундами лучше парсится некоторыми клиентами iOS.
    dtstart = start_dt.strftime("%Y%m%dT%H%M%S")
    dtend = end_dt.strftime("%Y%m%dT%H%M%S")

    summary = f"Маникюр: {style}"
    description = "Напоминание от бота"

    # Формируем raw-строки, затем делаем RFC5545 folding по каждой строке.
    # Это повышает шанс корректного распознавания в iOS Calendar.
    raw_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//bot1//Manicure Reminder//RU",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        # iOS иногда требует X-WR-CALNAME для корректной "кнопки добавления".
        "X-WR-CALNAME:Manicure",
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
        # Добавляем простой alarm; iOS часто позволяет выбрать/изменить время уведомления.
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

    # Важно: финальный перенос строки CRLF
    return "\r\n".join(folded_lines) + "\r\n"

