# -*- coding: utf-8 -*-
"""
Боти ҳисобкунаки вентилятсия (Telegram) — нусхаи чандинсамта.

Ҳар ҳисобкунак акнун мепурсад: "кадоме номаълум аст?" —
ва бо ҳар ду қимати боқимонда, сеюмашро меёбад.

ФОРМУЛАҲО:

1. Ҳаҷми ҳавои лозима:
   V = дарозӣ × бар × баландӣ
   L = V × n   (аз рӯи крати иваз)
   L = меъёр × шумораи одамон   (аз рӯи одамон)
   → калонтарини ду натиҷа тавсия дода мешавад

2. Андозаи қубур (се қимат: L, v, d):
   A = L / (3600 × v)
   d = sqrt(4A/π)

3. Тавоноии вентилятор (чор қимат: N, L, ΔP, η):
   N = (L × ΔP) / (3600 × 1000 × η)

ЧӢ ЛОЗИМ АСТ ПЕШ АЗ ИҶРО:
1. Токенро аз @BotFather гиред
2. Ба ҷои "ТОКЕНИ_ШУМО_ИНҶО" (поён), токени худро гузоред
3. Дар терминал: pip install aiogram
"""

import asyncio
import math
import os
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)

TOKEN = os.environ.get("BOT_TOKEN", "ТОКЕНИ_ШУМО_ИНҶО")

bot = Bot(token=TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


class Hajm(StatesGroup):
    waiting_length = State()
    waiting_width = State()
    waiting_height = State()
    waiting_ach = State()
    waiting_type = State()
    waiting_people = State()
    waiting_duct_confirm = State()


class Qubur(StatesGroup):
    waiting_choice = State()
    waiting_fan_confirm = State()


class Fan(StatesGroup):
    waiting_choice = State()


class Generic(StatesGroup):
    collecting = State()


def parse_number(text: str):
    try:
        value = float(text.strip().replace(",", "."))
        if value < 0:
            return None
        return value
    except ValueError:
        return None


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📦 Ҳаҷми ҳавои лозима")],
        [KeyboardButton(text="🔵 Андозаи қубур")],
        [KeyboardButton(text="🌀 Тавоноии вентилятор")],
    ],
    resize_keyboard=True,
)

confirm_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="✅ Ҳа")], [KeyboardButton(text="❌ Не")]],
    resize_keyboard=True,
)

OCCUPANCY_NORMS = {
    "🏢 Офис": 30,
    "🎭 Театр / Кинотеатр": 20,
    "🍽 Ресторан": 25,
    "🏋 Толори варзишӣ": 80,
    "🏫 Синфхонаи мактаб": 20,
    "🛍 Мағоза": 20,
    "🏥 Беморхона (палата)": 40,
    "🏨 Меҳмонхона (утоқ)": 30,
    "🏠 Хонаи истиқоматӣ": 0,
}

type_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=name)] for name in OCCUPANCY_NORMS.keys()],
    resize_keyboard=True,
)

QUBUR_OPTIONS = {
    "Диаметри қубур (d) номаълум": {
        "unknown": "d",
        "ask": [
            ("L", "Ҳавои лозимаро бо м³/соат ворид кунед (масалан: 300):"),
            ("v", "Суръати ҳаворо бо м/с ворид кунед (одатан 3-6, масалан: 4):"),
        ],
    },
    "Ҳавои лозима (L) номаълум": {
        "unknown": "L",
        "ask": [
            ("d", "Диаметри қубурро бо мм ворид кунед (масалан: 200):"),
            ("v", "Суръати ҳаворо бо м/с ворид кунед (масалан: 4):"),
        ],
    },
    "Суръати ҳаво (v) номаълум": {
        "unknown": "v",
        "ask": [
            ("L", "Ҳавои лозимаро бо м³/соат ворид кунед (масалан: 300):"),
            ("d", "Диаметри қубурро бо мм ворид кунед (масалан: 200):"),
        ],
    },
}

qubur_choice_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=name)] for name in QUBUR_OPTIONS.keys()]
    + [[KeyboardButton(text="🔙 Ба меню")]],
    resize_keyboard=True,
)

FAN_OPTIONS = {
    "Тавоноӣ (N) номаълум": {
        "unknown": "N",
        "ask": [
            ("L", "Ҳавои лозимаро бо м³/соат ворид кунед (масалан: 300):"),
            ("dP", "Фарқи фишорро (ΔP) бо Паскал ворид кунед (масалан: 100):"),
            ("eta", "Самаранокиро (η) аз 0 то 1 ворид кунед (масалан: 0.7):"),
        ],
    },
    "Ҳавои лозима (L) номаълум": {
        "unknown": "L",
        "ask": [
            ("N", "Тавоноиро (N) бо кВт ворид кунед (масалан: 0.5):"),
            ("dP", "Фарқи фишорро (ΔP) бо Паскал ворид кунед (масалан: 100):"),
            ("eta", "Самаранокиро (η) аз 0 то 1 ворид кунед (масалан: 0.7):"),
        ],
    },
    "Фарқи фишор (ΔP) номаълум": {
        "unknown": "dP",
        "ask": [
            ("N", "Тавоноиро (N) бо кВт ворид кунед (масалан: 0.5):"),
            ("L", "Ҳавои лозимаро бо м³/соат ворид кунед (масалан: 300):"),
            ("eta", "Самаранокиро (η) аз 0 то 1 ворид кунед (масалан: 0.7):"),
        ],
    },
    "Самаранокӣ (η) номаълум": {
        "unknown": "eta",
        "ask": [
            ("N", "Тавоноиро (N) бо кВт ворид кунед (масалан: 0.5):"),
            ("L", "Ҳавои лозимаро бо м³/соат ворид кунед (масалан: 300):"),
            ("dP", "Фарқи фишорро (ΔP) бо Паскал ворид кунед (масалан: 100):"),
        ],
    },
}

fan_choice_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=name)] for name in FAN_OPTIONS.keys()]
    + [[KeyboardButton(text="🔙 Ба меню")]],
    resize_keyboard=True,
)


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Салом! Ман ҳисобкунаки вентилятсия ҳастам.\nКадом ҳисобро мехоҳед?",
        reply_markup=main_menu,
    )


@router.message(F.text == "🔙 Ба меню")
async def back_to_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Менюи асосӣ:", reply_markup=main_menu)


@router.message(F.text == "📦 Ҳаҷми ҳавои лозима")
async def hajm_start(message: Message, state: FSMContext):
    await state.set_state(Hajm.waiting_length)
    await message.answer(
        "Ҳисоби ҳаҷми ҳавои лозима барои хона.\n\n"
        "Дарозии хонаро бо метр ворид кунед (масалан: 5):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Hajm.waiting_length)
async def hajm_get_length(message: Message, state: FSMContext):
    length = parse_number(message.text)
    if not length:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед (масалан: 5)")
        return
    await state.update_data(length=length)
    await state.set_state(Hajm.waiting_width)
    await message.answer("Бари хонаро бо метр ворид кунед (масалан: 4):")


@router.message(Hajm.waiting_width)
async def hajm_get_width(message: Message, state: FSMContext):
    width = parse_number(message.text)
    if not width:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед (масалан: 4)")
        return
    await state.update_data(width=width)
    await state.set_state(Hajm.waiting_height)
    await message.answer("Баландии хонаро бо метр ворид кунед (масалан: 3):")


@router.message(Hajm.waiting_height)
async def hajm_get_height(message: Message, state: FSMContext):
    height = parse_number(message.text)
    if not height:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед (масалан: 3)")
        return
    await state.update_data(height=height)
    await state.set_state(Hajm.waiting_ach)
    await message.answer(
        "Крати иваз шудани ҳаво дар як соат (n) чанд бошад?\n"
        "(Мисол: хонаи хоб 1-2, ошхона 6-10, идора 4-6):"
    )


@router.message(Hajm.waiting_ach)
async def hajm_get_ach(message: Message, state: FSMContext):
    ach = parse_number(message.text)
    if not ach:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед (масалан: 5)")
        return
    await state.update_data(ach=ach)
    await state.set_state(Hajm.waiting_type)
    await message.answer(
        "Акнун навъи биноро интихоб кунед, то ҳисоби иловагӣ "
        "аз рӯи шумораи одамон низ гузаронем:",
        reply_markup=type_menu,
    )


@router.message(Hajm.waiting_type, F.text.in_(OCCUPANCY_NORMS.keys()))
async def hajm_get_type(message: Message, state: FSMContext):
    norm = OCCUPANCY_NORMS[message.text]
    await state.update_data(building_type=message.text, norm=norm)
    if norm == 0:
        await hajm_show_result(message, state, people=0)
        return
    await state.set_state(Hajm.waiting_people)
    await message.answer(
        f"Барои «{message.text}», меъёр {norm} м³/соат барои 1 нафар аст.\n"
        f"Шумораи одамонро ворид кунед (масалан: 20):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Hajm.waiting_people)
async def hajm_get_people(message: Message, state: FSMContext):
    people = parse_number(message.text)
    if people is None:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед (масалан: 20)")
        return
    await hajm_show_result(message, state, people=people)


async def hajm_show_result(message: Message, state: FSMContext, people: float):
    data = await state.get_data()
    length = data["length"]
    width = data["width"]
    height = data["height"]
    ach = data["ach"]
    norm = data["norm"]
    building_type = data["building_type"]

    volume = length * width * height
    airflow_by_volume = volume * ach
    airflow_by_people = norm * people
    final_airflow = max(airflow_by_volume, airflow_by_people)

    text = (
        f"📊 Натиҷа:\n"
        f"Ҳаҷми хона (V) = {length} × {width} × {height} = {volume:.2f} м³\n\n"
        f"1) Аз рӯи крати иваз (n={ach}):\n"
        f"   L₁ = V × n = {airflow_by_volume:.2f} м³/соат\n\n"
    )
    if norm > 0:
        text += (
            f"2) Аз рӯи одамон ({building_type}, {int(people)} нафар × {norm} м³/соат):\n"
            f"   L₂ = {airflow_by_people:.2f} м³/соат\n\n"
            f"✅ Тавсия (калонтарин): {final_airflow:.2f} м³/соат"
        )
    else:
        text += f"✅ Тавсия: {final_airflow:.2f} м³/соат"

    await state.update_data(airflow=final_airflow)
    await state.set_state(Hajm.waiting_duct_confirm)
    await message.answer(
        text + "\n\n➡️ Оё андозаи қубурро низ ҳисоб кунем?",
        reply_markup=confirm_menu,
    )


@router.message(Hajm.waiting_duct_confirm, F.text == "✅ Ҳа")
async def hajm_to_duct_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    airflow = data["airflow"]
    await state.update_data(
        calc_type="qubur", unknown="d", answers={"L": airflow},
        remaining=[], current_key="v",
    )
    await state.set_state(Generic.collecting)
    await message.answer(
        "Суръати ҳаворо бо м/с ворид кунед (одатан 3-6 м/с, масалан: 4):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Hajm.waiting_duct_confirm, F.text == "❌ Не")
async def hajm_to_duct_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Хуб, тамом шуд. Менюи асосӣ:", reply_markup=main_menu)


@router.message(F.text == "🔵 Андозаи қубур")
async def qubur_start(message: Message, state: FSMContext):
    await state.set_state(Qubur.waiting_choice)
    await message.answer(
        "Ҳисоби қубури вентилятсия.\nКадоме аз ин се қимат номаълум аст?",
        reply_markup=qubur_choice_menu,
    )


@router.message(Qubur.waiting_choice, F.text.in_(QUBUR_OPTIONS.keys()))
async def qubur_choice_made(message: Message, state: FSMContext):
    option = QUBUR_OPTIONS[message.text]
    ask = option["ask"]
    first_key, first_question = ask[0]
    await state.update_data(
        calc_type="qubur", unknown=option["unknown"],
        answers={}, remaining=ask[1:], current_key=first_key,
    )
    await state.set_state(Generic.collecting)
    await message.answer(first_question, reply_markup=ReplyKeyboardRemove())


@router.message(Qubur.waiting_fan_confirm, F.text == "✅ Ҳа")
async def qubur_to_fan_yes(message: Message, state: FSMContext):
    data = await state.get_data()
    airflow = data["airflow"]
    await state.update_data(
        calc_type="fan", unknown="N", answers={"L": airflow},
        remaining=[("eta", "Самаранокии вентиляторро (η) аз 0 то 1 ворид кунед (масалан: 0.7):")],
        current_key="dP",
    )
    await state.set_state(Generic.collecting)
    await message.answer(
        "Фарқи фишорро (ΔP) бо Паскал ворид кунед (одатан 50-200, масалан: 100):",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Qubur.waiting_fan_confirm, F.text == "❌ Не")
async def qubur_to_fan_no(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Хуб, тамом шуд. Менюи асосӣ:", reply_markup=main_menu)


@router.message(F.text == "🌀 Тавоноии вентилятор")
async def fan_start(message: Message, state: FSMContext):
    await state.set_state(Fan.waiting_choice)
    await message.answer(
        "Ҳисоби тавоноии вентилятор.\nКадоме аз ин чор қимат номаълум аст?",
        reply_markup=fan_choice_menu,
    )


@router.message(Fan.waiting_choice, F.text.in_(FAN_OPTIONS.keys()))
async def fan_choice_made(message: Message, state: FSMContext):
    option = FAN_OPTIONS[message.text]
    ask = option["ask"]
    first_key, first_question = ask[0]
    await state.update_data(
        calc_type="fan", unknown=option["unknown"],
        answers={}, remaining=ask[1:], current_key=first_key,
    )
    await state.set_state(Generic.collecting)
    await message.answer(first_question, reply_markup=ReplyKeyboardRemove())


@router.message(Generic.collecting)
async def generic_collect(message: Message, state: FSMContext):
    value = parse_number(message.text)
    if value is None:
        await message.answer("Лутфан рақами дурусти мусбат ворид кунед")
        return

    data = await state.get_data()
    answers = dict(data.get("answers", {}))
    answers[data["current_key"]] = value
    remaining = list(data.get("remaining", []))

    if remaining:
        next_key, next_question = remaining[0]
        await state.update_data(
            answers=answers, remaining=remaining[1:], current_key=next_key
        )
        await message.answer(next_question)
        return

    calc_type = data["calc_type"]
    unknown = data["unknown"]
    if calc_type == "qubur":
        await finish_qubur(message, state, unknown, answers)
    else:
        await finish_fan(message, state, unknown, answers)


async def finish_qubur(message: Message, state: FSMContext, unknown: str, answers: dict):
    if unknown == "d":
        L = answers["L"]
        v = answers["v"]
        if v <= 0:
            await message.answer("Хатогӣ: суръат наметавонад 0 бошад.")
            await state.clear()
            return
        area = L / (3600 * v)
        d_mm = math.sqrt(4 * area / math.pi) * 1000
        text = (
            f"Ҳавои лозима (L) = {L:.2f} м³/соат\n"
            f"Суръат (v) = {v} м/с\n"
            f"Диаметри қубур (d) = {d_mm:.0f} мм"
        )
        final_airflow = L

    elif unknown == "L":
        d_mm = answers["d"]
        v = answers["v"]
        area = math.pi * (d_mm / 1000) ** 2 / 4
        L = area * 3600 * v
        text = (
            f"Диаметр (d) = {d_mm} мм\n"
            f"Суръат (v) = {v} м/с\n"
            f"Ҳавои лозима (L) = {L:.2f} м³/соат"
        )
        final_airflow = L

    else:
        L = answers["L"]
        d_mm = answers["d"]
        area = math.pi * (d_mm / 1000) ** 2 / 4
        if area <= 0:
            await message.answer("Хатогӣ: диаметр нодуруст аст.")
            await state.clear()
            return
        v = L / (3600 * area)
        text = (
            f"Ҳавои лозима (L) = {L:.2f} м³/соат\n"
            f"Диаметр (d) = {d_mm} мм\n"
            f"Суръати ҳаво (v) = {v:.2f} м/с"
        )
        final_airflow = L

    await state.update_data(airflow=final_airflow)
    await state.set_state(Qubur.waiting_fan_confirm)
    await message.answer(
        f"📊 Натиҷа:\n{text}\n\n➡️ Оё тавоноии вентиляторро низ ҳисоб кунем?",
        reply_markup=confirm_menu,
    )


async def finish_fan(message: Message, state: FSMContext, unknown: str, answers: dict):
    if unknown == "N":
        L, dP, eta = answers["L"], answers["dP"], answers["eta"]
        if eta <= 0:
            await message.answer("Хатогӣ: самаранокӣ бояд аз 0 калон бошад.")
            await state.clear()
            return
        N = (L * dP) / (3600 * 1000 * eta)
        text = (
            f"Ҳавои лозима (L) = {L} м³/соат\nФарқи фишор (ΔP) = {dP} Па\n"
            f"Самаранокӣ (η) = {eta}\nТавоноии вентилятор (N) = {N:.3f} кВт"
        )

    elif unknown == "L":
        N, dP, eta = answers["N"], answers["dP"], answers["eta"]
        if dP <= 0:
            await message.answer("Хатогӣ: фарқи фишор бояд аз 0 калон бошад.")
            await state.clear()
            return
        L = (N * 3600 * 1000 * eta) / dP
        text = (
            f"Тавоноӣ (N) = {N} кВт\nФарқи фишор (ΔP) = {dP} Па\n"
            f"Самаранокӣ (η) = {eta}\nҲавои лозима (L) = {L:.2f} м³/соат"
        )

    elif unknown == "dP":
        N, L, eta = answers["N"], answers["L"], answers["eta"]
        if L <= 0:
            await message.answer("Хатогӣ: ҳавои лозима наметавонад 0 бошад.")
            await state.clear()
            return
        dP = (N * 3600 * 1000 * eta) / L
        text = (
            f"Тавоноӣ (N) = {N} кВт\nҲавои лозима (L) = {L} м³/соат\n"
            f"Самаранокӣ (η) = {eta}\nФарқи фишор (ΔP) = {dP:.2f} Па"
        )

    else:
        N, L, dP = answers["N"], answers["L"], answers["dP"]
        if N <= 0:
            await message.answer("Хатогӣ: тавоноӣ наметавонад 0 бошад.")
            await state.clear()
            return
        eta = (L * dP) / (3600 * 1000 * N)
        text = (
            f"Тавоноӣ (N) = {N} кВт\nҲавои лозима (L) = {L} м³/соат\n"
            f"Фарқи фишор (ΔP) = {dP} Па\nСамаранокии зарурӣ (η) = {eta:.3f}"
        )

    await message.answer(f"📊 Натиҷа:\n{text}", reply_markup=main_menu)
    await state.clear()


async def main():
    print("Боти вентилятсия кор карда истодааст...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
