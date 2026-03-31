import asyncio
import os
import tempfile
from datetime import date

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import FSInputFile, KeyboardButton, Message, ReplyKeyboardMarkup

from config import (
    BOT_TOKEN,
    GOOGLE_SERVICE_ACCOUNT_INFO,
    GOOGLE_SPREADSHEET_ID,
    GOOGLE_WORKSHEET_NAME,
    REMINDER_DURATION_MINUTES,
)
from calendar_ics import create_ics_text
from google_sheets import append_reminder_to_google_sheets
from keyboards import (
    CalendarDateCallback,
    ConfirmCallback,
    TimeSlotCallback,
    build_calendar_keyboard,
    build_confirm_keyboard,
    build_time_slots_keyboard,
    get_month_ahead_range,
)


class CreateReminder(StatesGroup):
    style = State()
    date = State()
    time = State()
    confirm = State()


dp = Dispatcher(storage=MemoryStorage())

CREATE_BUTTON = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Создать запись")]],
    resize_keyboard=True,
)


@dp.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        "Привет! Нажмите «Создать запись», чтобы добавить напоминание по маникюру.",
        reply_markup=CREATE_BUTTON,
    )


@dp.message(Command("new"))
async def cmd_new(message: Message, state: FSMContext) -> None:
    await state.clear()
    start_date, end_date = get_month_ahead_range()
    await state.set_state(CreateReminder.style)
    await state.update_data(start_date=start_date.isoformat(), end_date=end_date.isoformat())
    await message.answer("Какой стиль ногтей? Напишите текстом (например: «френч, гель-лак»).")


@dp.message(lambda m: m.text == "Создать запись")
async def on_create_record_button(message: Message, state: FSMContext) -> None:
    await cmd_new(message, state)


@dp.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Ок, отменено. Нажмите «Создать запись» для новой записи.", reply_markup=CREATE_BUTTON)


@dp.message(CreateReminder.style)
async def handle_style(message: Message, state: FSMContext) -> None:
    style = (message.text or "").strip()
    if not style:
        await message.answer("Стиль ногтей не может быть пустым. Напишите текст.")
        return
    if len(style) > 120:
        await message.answer("Слишком длинное описание. Попробуйте короче (до 120 символов).")
        return

    await state.update_data(style=style)
    data = await state.get_data()
    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])

    await state.set_state(CreateReminder.date)
    await message.answer(
        "Выберите дату (календарь на месяц вперед):",
        reply_markup=build_calendar_keyboard(start_date=start_date, end_date=end_date),
    )


@dp.callback_query(lambda c: c.data == "noop")
async def handle_noop(callback_query) -> None:
    await callback_query.answer()


@dp.callback_query(CalendarDateCallback.filter())
async def handle_date(callback_query, state: FSMContext) -> None:
    if (await state.get_state()) != CreateReminder.date.state:
        await callback_query.answer("Сейчас выбирается другая стадия.", show_alert=False)
        return

    try:
        parsed = CalendarDateCallback.unpack(callback_query.data)
        # В aiogram в зависимости от версии/типизации unpack может возвращать dict или объект.
        iso = parsed["iso"] if isinstance(parsed, dict) else parsed.iso
        selected = date.fromisoformat(iso)
    except Exception:
        await callback_query.answer("Не удалось распознать дату.", show_alert=False)
        return

    data = await state.get_data()
    start_date = date.fromisoformat(data["start_date"])
    end_date = date.fromisoformat(data["end_date"])

    if not (start_date <= selected <= end_date):
        await callback_query.answer("Выберите дату в пределах календаря.", show_alert=False)
        return

    await state.update_data(date_iso=iso)
    await state.set_state(CreateReminder.time)

    await callback_query.answer()
    await callback_query.message.answer("Теперь выберите время (слоты с 10:00 до 23:00):", reply_markup=build_time_slots_keyboard())


@dp.callback_query(TimeSlotCallback.filter())
async def handle_time(callback_query, state: FSMContext) -> None:
    if (await state.get_state()) != CreateReminder.time.state:
        await callback_query.answer("Сейчас выбирается другая стадия.", show_alert=False)
        return

    try:
        parsed = TimeSlotCallback.unpack(callback_query.data)
        time_hhmm = parsed["value"] if isinstance(parsed, dict) else parsed.value
    except Exception:
        await callback_query.answer("Не удалось распознать время.", show_alert=False)
        return

    await state.update_data(time_hhmm=time_hhmm)
    await state.set_state(CreateReminder.confirm)

    data = await state.get_data()
    style = data["style"]
    date_iso = data["date_iso"]

    await callback_query.answer()
    await callback_query.message.answer(
        "Проверьте запись:\n"
        f"• Стиль ногтей: {style}\n"
        f"• Дата: {date_iso}\n"
        f"• Время: {time_hhmm}\n\n"
        "Подтвердить?",
        reply_markup=build_confirm_keyboard(),
    )


@dp.callback_query(ConfirmCallback.filter())
async def handle_confirm(callback_query, state: FSMContext) -> None:
    if (await state.get_state()) != CreateReminder.confirm.state:
        await callback_query.answer("Сейчас нельзя подтвердить.", show_alert=False)
        return

    try:
        parsed = ConfirmCallback.unpack(callback_query.data)
        action = parsed["action"] if isinstance(parsed, dict) else parsed.action
    except Exception:
        await callback_query.answer("Не удалось распознать действие.", show_alert=False)
        return

    if action != "yes":
        await state.clear()
        await callback_query.answer()
        await callback_query.message.answer("Отменено. Нажмите «Создать запись» для новой записи.", reply_markup=CREATE_BUTTON)
        return

    data = await state.get_data()
    style = data["style"]
    date_iso = data["date_iso"]
    time_hhmm = data["time_hhmm"]

    await callback_query.answer("Сохраняю…")

    tmp_path = None
    success = False
    try:
        # 1) Save to Google Sheets
        await append_reminder_to_google_sheets(
            service_account_info=GOOGLE_SERVICE_ACCOUNT_INFO,
            spreadsheet_id=GOOGLE_SPREADSHEET_ID,
            worksheet_name=GOOGLE_WORKSHEET_NAME,
            style=style,
            date_iso=date_iso,
            time_hhmm=time_hhmm,
        )

        # 2) Create an .ics and send it to user.
        ics_text = create_ics_text(
            style=style,
            date_iso=date_iso,
            time_hhmm=time_hhmm,
            duration_minutes=REMINDER_DURATION_MINUTES,
        )
        tmp_dir = tempfile.gettempdir()
        filename = f"manicure_reminder_{callback_query.from_user.id}_{date_iso}_{time_hhmm.replace(':', '')}.ics"
        tmp_path = os.path.join(tmp_dir, filename)
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(ics_text)

        await callback_query.message.answer_document(
            FSInputFile(tmp_path),
            caption=(
                "Готово! Я сохранил запись в Google Sheets и сформировал событие для календаря.\n"
                "Откройте вложение с расширением .ics и выберите «Добавить в календарь» (импорт на устройстве)."
            ),
        )
        success = True
        await callback_query.message.answer(
            "Если не появилось сразу: попробуйте открыть файл заново или импортировать вручную. "
            "Команду /new можно использовать для следующей записи."
        )
    except Exception as e:
        await callback_query.message.answer(
            f"Не удалось создать запись: {e}\n"
            "Проверьте настройки Google Sheets и перезапустите бота, если проблема повторяется."
        )
    finally:
        try:
            # tmp_path может не существовать при ошибках до его создания.
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except OSError:
            pass

    await state.clear()
    if success:
        await callback_query.message.answer(
            "Готово. Нажмите «Создать запись» для следующей записи.",
            reply_markup=CREATE_BUTTON,
        )
    else:
        await callback_query.message.answer(
            "Попробуйте создать запись ещё раз кнопкой «Создать запись».",
            reply_markup=CREATE_BUTTON,
        )


async def main() -> None:
    bot = Bot(token=BOT_TOKEN)
    dp.startup.register(lambda *_: None)
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())

