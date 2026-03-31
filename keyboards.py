from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Tuple

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class CalendarDateCallback(CallbackData, prefix="cal"):
    iso: str


class TimeSlotCallback(CallbackData, prefix="time"):
    value: str


class ConfirmCallback(CallbackData, prefix="confirm"):
    action: str


def get_month_ahead_range(today: date | None = None) -> Tuple[date, date]:
    if today is None:
        today = date.today()
    # "на месяц вперед" -> диапазон до ~31 дня (с учетом разных месяцев).
    end = today + timedelta(days=31)
    return today, end


def _start_of_week(d: date, week_starts_monday: bool = True) -> date:
    # Python: Monday=0 ... Sunday=6
    weekday = d.weekday()
    if week_starts_monday:
        return d - timedelta(days=weekday)
    # Week starts Sunday
    return d - timedelta(days=(weekday + 1) % 7)


def build_calendar_keyboard(*, start_date: date, end_date: date) -> InlineKeyboardMarkup:
    grid_start = _start_of_week(start_date)
    grid_end = end_date + timedelta(days=(6 - end_date.weekday()))

    buttons: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []

    current = grid_start
    while current <= grid_end:
        if start_date <= current <= end_date:
            iso = current.isoformat()
            row.append(
                InlineKeyboardButton(
                    text=str(current.day),
                    callback_data=CalendarDateCallback(iso=iso).pack(),
                )
            )
        else:
            row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

        if len(row) == 7:
            buttons.append(row)
            row = []
        current += timedelta(days=1)

    # Header with month range label (non-interactive).
    month_label = f"{calendar.month_name[start_date.month]} {start_date.year} - {calendar.month_name[end_date.month]} {end_date.year}"
    header = [InlineKeyboardButton(text=month_label, callback_data="noop")]
    buttons.insert(0, header)

    # Weekday row: Пн..Вс
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    weekday_row = [InlineKeyboardButton(text=w, callback_data="noop") for w in weekdays]
    buttons.insert(1, weekday_row)

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def build_time_slots_keyboard() -> InlineKeyboardMarkup:
    # Slots: 10:00 .. 23:00 each hour.
    # В callback data нельзя использовать ':', поэтому храним "1000", "1100", ...
    values = [f"{h:02d}00" for h in range(10, 24)]
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for i, v in enumerate(values, start=1):
        # Текст для пользователя: 10:00, 11:00, ...
        label = f"{v[:2]}:{v[2:]}"
        row.append(InlineKeyboardButton(text=label, callback_data=TimeSlotCallback(value=v).pack()))
        if i % 4 == 0:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=ConfirmCallback(action="yes").pack()),
                InlineKeyboardButton(text="❌ Отмена", callback_data=ConfirmCallback(action="no").pack()),
            ]
        ]
    )

