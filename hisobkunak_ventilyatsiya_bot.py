import os
import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Меъёрҳои вентилятсия барои намудҳои гуногуни бино
# ach = маротибаи иваз шудани ҳаво дар як соат (air changes per hour)
# per_person = ҳаво (м³/соат) барои як нафар
ROOM_TYPES = {
    "turarjoy":   {"name": "🏠 Хонаи истиқоматӣ",              "ach": 3,  "per_person": 30},
    "ofis":       {"name": "🏢 Офис",                          "ach": 5,  "per_person": 40},
    "teatr":      {"name": "🎭 Театр / Синамо / Толори маърузавӣ", "ach": 8,  "per_person": 25},
    "restoran":   {"name": "🍽 Тарабхона / Ошхона",            "ach": 10, "per_person": 20},
    "varzishgoh": {"name": "🏋 Толори варзишӣ / Фитнес",        "ach": 8,  "per_person": 80},
    "dukon":      {"name": "🛍 Мағоза / Маркази савдо",         "ach": 5,  "per_person": 20},
}


class VentForm(StatesGroup):
    choosing_type = State()
    length = State()
    width = State()
    height = State()
    people = State()


def room_type_keyboard() -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for key, val in ROOM_TYPES.items():
        row.append(InlineKeyboardButton(text=val["name"], callback_data=f"type_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parse_positive_float(text: str) -> float:
    value = float(text.replace(",", "."))
    if value <= 0:
        raise ValueError("must be positive")
    return value


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Ассалому алайкум! 👋\n\n"
        "Ман бот барои ҳисоб кардани иқтидори лозимии вентилятор (кубометр дар як соат) ҳастам.\n\n"
        "Аввал навъи биноро интихоб кунед:",
        reply_markup=room_type_keyboard(),
    )
    await state.set_state(VentForm.choosing_type)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Барои ҳисоб кардани иқтидори вентилятсия фармони /start-ро пахш кунед.\n\n"
        "Ман аз шумо инҳоро мепурсам:\n"
        "1️⃣ Навъи бино (хона, офис, театр ва ғ.)\n"
        "2️⃣ Дарозӣ, бар ва баландии хона (метр)\n"
        "3️⃣ Шумораи одамон\n\n"
        "Пас аз он, иқтидори лозимии вентиляторро (м³/соат) ҳисоб карда медиҳам."
    )


@dp.callback_query(F.data.startswith("type_"))
async def process_type(callback: CallbackQuery, state: FSMContext):
    key = callback.data.replace("type_", "")
    room = ROOM_TYPES[key]
    await state.update_data(room_key=key)
    await callback.message.edit_text(f"Навъи бино: {room['name']} ✅")
    await callback.message.answer("Дарозии хонаро бо метр ворид кунед (масалан: 10):")
    await state.set_state(VentForm.length)
    await callback.answer()


@dp.message(VentForm.length)
async def process_length(message: Message, state: FSMContext):
    try:
        length = parse_positive_float(message.text)
    except ValueError:
        await message.answer("⚠️ Лутфан рақами дурусти мусбат ворид кунед (масалан: 10 ё 10.5)")
        return
    await state.update_data(length=length)
    await message.answer("Бари хонаро бо метр ворид кунед (масалан: 8):")
    await state.set_state(VentForm.width)


@dp.message(VentForm.width)
async def process_width(message: Message, state: FSMContext):
    try:
        width = parse_positive_float(message.text)
    except ValueError:
        await message.answer("⚠️ Лутфан рақами дурусти мусбат ворид кунед (масалан: 8)")
        return
    await state.update_data(width=width)
    await message.answer("Баландии хонаро бо метр ворид кунед (масалан: 3):")
    await state.set_state(VentForm.height)


@dp.message(VentForm.height)
async def process_height(message: Message, state: FSMContext):
    try:
        height = parse_positive_float(message.text)
    except ValueError:
        await message.answer("⚠️ Лутфан рақами дурусти мусбат ворид кунед (масалан: 3)")
        return
    await state.update_data(height=height)
    await message.answer("Шумораи одамоне, ки дар хона мебошанд, ворид кунед (масалан: 20):")
    await state.set_state(VentForm.people)


@dp.message(VentForm.people)
async def process_people(message: Message, state: FSMContext):
    try:
        people = int(message.text)
        if people < 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Лутфан рақами дурусти бутун ворид кунед (масалан: 20)")
        return

    data = await state.get_data()
    room = ROOM_TYPES[data["room_key"]]
    length = data["length"]
    width = data["width"]
    height = data["height"]

    volume = length * width * height
    airflow_by_volume = volume * room["ach"]
    airflow_by_people = people * room["per_person"]
    final_airflow = max(airflow_by_volume, airflow_by_people)
    recommended = final_airflow * 1.15  # 15% захираи бехатарӣ

    result_text = (
        f"📊 <b>Натиҷаи ҳисобот</b>\n\n"
        f"{room['name']}\n"
        f"📐 Андоза: {length:g} × {width:g} × {height:g} м\n"
        f"📦 Ҳаҷми хона: {volume:.1f} м³\n"
        f"👥 Шумораи одамон: {people}\n\n"
        f"💨 Талабот аз рӯйи ҳаҷм ({room['ach']}× иваз/соат): {airflow_by_volume:.0f} м³/соат\n"
        f"👤 Талабот аз рӯйи одамон ({room['per_person']} м³/соат/нафар): {airflow_by_people:.0f} м³/соат\n\n"
        f"✅ <b>Иқтидори лозимии вентилятор: {final_airflow:.0f} м³/соат</b>\n"
        f"🔧 Бо захираи бехатарӣ (15%): <b>{recommended:.0f} м³/соат</b>\n\n"
        f"Барои ҳисоби нав /start-ро пахш кунед."
    )
    await message.answer(result_text, parse_mode=ParseMode.HTML)
    await state.clear()


@dp.message()
async def fallback(message: Message):
    await message.answer("Барои оғоз /start-ро пахш кунед.")


async def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is not set!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
