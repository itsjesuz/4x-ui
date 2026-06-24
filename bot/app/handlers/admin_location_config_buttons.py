from __future__ import annotations

import re
from html import escape

from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import LOCATIONS
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_ui_helpers import admin_edit_or_answer

router = Router(name="admin_location_config_buttons")

class LocationConfigButtonsFlow(StatesGroup):
    waiting_button_name = State()
    waiting_button_keywords = State()


async def send_config_buttons_menu(
    message: Message, db: Database, loc_id: int, edit_in_place: bool = False
) -> None:
    loc = db.get_location(loc_id)
    if loc is None:
        await admin_edit_or_answer(message, texts.EDIT_LOC_NOT_FOUND.format(id=loc_id), edit_in_place=edit_in_place)
        return

    buttons = loc.config_buttons
    text = (
        f"🎛 <b>مدیریت دکمه‌های دریافت کانفیگ لوکیشن:</b> {escape(loc.name)}\n\n"
        "در این بخش می‌توانید دکمه‌هایی بسازید که کاربران با کلیک روی آنها، فقط کانفیگ‌های مربوط به آن منطقه (مثلاً فقط انگلیس) را دریافت کنند.\n\n"
        f"<b>دکمه‌های فعلی ({len(buttons)}):</b>\n"
    )
    for i, btn in enumerate(buttons):
        text += f"{i+1}. <b>{escape(btn.get('name', ''))}</b> -> کلمات کلیدی: <code>{escape(btn.get('keywords', ''))}</code>\n"

    await admin_edit_or_answer(
        message,
        text,
        keyboards.admin_location_config_buttons(loc_id, buttons),
        edit_in_place=edit_in_place,
    )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_BTNS_PREFIX))
async def cb_admin_loc_btns(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
    state: FSMContext,
) -> None:
    if not await guard_admin_callback(callback, settings, db, LOCATIONS):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await state.clear()
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_BTNS_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    await send_config_buttons_menu(callback.message, db, loc_id, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_BTN_DEL_PREFIX))
async def cb_admin_loc_btn_del(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, LOCATIONS):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_BTN_DEL_PREFIX)
    try:
        loc_id_str, index_str = raw.split(":")
        loc_id = int(loc_id_str)
        index = int(index_str)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc and 0 <= index < len(loc.config_buttons):
        buttons = list(loc.config_buttons)
        buttons.pop(index)
        db.set_location_config_buttons(loc_id, buttons)
        await send_config_buttons_menu(callback.message, db, loc_id, edit_in_place=True)
    
    await callback.answer("دکمه حذف شد.", show_alert=True)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_BTN_ADD_PREFIX))
async def cb_admin_loc_btn_add(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, LOCATIONS):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_BTN_ADD_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    await state.update_data(loc_id=loc_id)
    await state.set_state(LocationConfigButtonsFlow.waiting_button_name)
    
    await admin_edit_or_answer(
        callback.message,
        "🏷 <b>نام دکمه را وارد کنید:</b>\n"
        "(مثلاً: <code>🇬🇧 سرورهای انگلیس</code> یا <code>🇩🇪 آلمان</code>)",
        keyboards.admin_flow_cancel_inline(back_data=f"{keyboards.CB_ADM_LOC_BTNS_PREFIX}{loc_id}"),
        edit_in_place=True,
    )
    await callback.answer()


@router.message(StateFilter(LocationConfigButtonsFlow.waiting_button_name))
async def edit_loc_btn_name(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    name = (message.text or "").strip()
    if not name:
        await message.answer("لطفاً یک نام معتبر وارد کنید.")
        return

    await state.update_data(btn_name=name)
    await state.set_state(LocationConfigButtonsFlow.waiting_button_keywords)
    await message.answer(
        f"✅ نام دکمه: <b>{escape(name)}</b>\n\n"
        "حالا <b>کلمات کلیدی</b> را وارد کنید.\n"
        "بات در نام کانفیگ‌ها (Remark) جستجو می‌کند و هر کانفیگی که این کلمات در نام آن باشد را برای کاربر می‌فرستد.\n"
        "می‌توانید چند کلمه را با کاما جدا کنید.\n\n"
        "مثال: <code>UK, London, GB</code>",
        reply_markup=keyboards.admin_flow_cancel_inline(back_data=f"{keyboards.CB_ADM_LOC_BTNS_PREFIX}{loc_id}"),
    )


@router.message(StateFilter(LocationConfigButtonsFlow.waiting_button_keywords))
async def edit_loc_btn_keywords(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    name = data["btn_name"]
    keywords = (message.text or "").strip()
    if not keywords:
        await message.answer("لطفاً کلمات کلیدی را وارد کنید.")
        return

    loc = db.get_location(loc_id)
    if not loc:
        await state.clear()
        return

    buttons = list(loc.config_buttons)
    buttons.append({
        "name": name,
        "keywords": keywords
    })
    
    db.set_location_config_buttons(loc_id, buttons)
    await state.clear()
    
    msg = await message.answer(f"✅ دکمه <b>{escape(name)}</b> با موفقیت اضافه شد!")
    await send_config_buttons_menu(msg, db, loc_id, edit_in_place=False)
