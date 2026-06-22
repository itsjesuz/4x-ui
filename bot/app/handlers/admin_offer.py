"""Admin: global offer (percent / amount off / fixed price) on all services."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import OFFER
from app.handlers.admin_helpers import (
    admin_can,
    guard_admin_callback,
    guard_admin_message,
    is_admin,
)
from app.handlers.admin_ui_helpers import admin_edit_or_answer
from app.pricing import describe_offer

router = Router(name="admin_offer")


class AdminOfferFlow(StatesGroup):
    waiting_percent = State()
    waiting_amount = State()
    waiting_fixed = State()


def _offer_menu_text(db: Database) -> str:
    return texts.ADMIN_OFFER_MENU.format(
        offer_desc=describe_offer(db.get_offer_config())
    )


async def send_offer_menu(
    message: Message, db: Database, *, edit_in_place: bool = False
) -> None:
    await admin_edit_or_answer(
        message,
        _offer_menu_text(db),
        keyboards.admin_offer_inline(db),
        edit_in_place=edit_in_place,
    )


def _parse_setoffer_args(parts: list[str]) -> tuple[str, int] | None:
    """Return (kind, value) or None."""
    if not parts:
        return None
    if len(parts) == 1:
        raw = parts[0].rstrip("%")
        if raw.isdigit():
            v = int(raw)
            if 1 <= v <= 99:
                return "percent", v
        return None
    kind = parts[0].lower()
    try:
        value = int(parts[1])
    except ValueError:
        return None
    if kind in ("percent", "pct", "%"):
        if 1 <= value <= 99:
            return "percent", value
    elif kind in ("off", "amount", "minus"):
        if value > 0:
            return "amount", value
    elif kind in ("price", "fixed"):
        if value >= 0:
            return "fixed", value
    return None


@router.message(Command("setoffer"))
async def cmd_setoffer(
    message: Message,
    command: CommandObject,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, OFFER):
        return

    raw = (command.args or "").strip().lower()
    if not raw or raw in ("clear", "off", "none", "0"):
        db.clear_global_offer()
        await message.answer(texts.ADMIN_OFFER_CLEARED)
        return

    parts = raw.split()
    parsed = _parse_setoffer_args(parts)
    if parsed is None:
        await message.answer(texts.ADMIN_OFFER_USAGE)
        return

    kind, value = parsed
    db.set_global_offer(kind, value)
    await message.answer(
        texts.ADMIN_OFFER_SET_OK.format(
            offer_desc=describe_offer(db.get_offer_config())
        )
    )


@router.callback_query(F.data == keyboards.CB_ADM_OFFER)
async def cb_admin_offer_menu(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    if isinstance(callback.message, Message):
        await send_offer_menu(callback.message, db, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_OFFER_CLEAR)
async def cb_admin_offer_clear(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    db.clear_global_offer()
    if isinstance(callback.message, Message):
        await send_offer_menu(callback.message, db, edit_in_place=True)
    await callback.answer(texts.ADMIN_OFFER_CLEARED)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_OFFER_PCT_PREFIX))
async def cb_admin_offer_percent_preset(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_OFFER_PCT_PREFIX)
    try:
        pct = int(raw)
    except ValueError:
        await callback.answer()
        return
    if not 1 <= pct <= 99:
        await callback.answer(texts.ADMIN_OFFER_INVALID, show_alert=True)
        return
    db.set_global_offer("percent", pct)
    if isinstance(callback.message, Message):
        await send_offer_menu(callback.message, db, edit_in_place=True)
    await callback.answer(
        texts.ADMIN_OFFER_SET_OK.format(
            offer_desc=describe_offer(db.get_offer_config())
        )
    )


@router.callback_query(F.data == keyboards.CB_ADM_OFFER_PCT_CUSTOM)
async def cb_admin_offer_percent_custom(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.set_state(AdminOfferFlow.waiting_percent)
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_OFFER_PERCENT_PROMPT,
        keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_OFFER),
        edit_in_place=True,
    )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_OFFER_AMOUNT)
async def cb_admin_offer_amount(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.set_state(AdminOfferFlow.waiting_amount)
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_OFFER_AMOUNT_PROMPT,
        keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_OFFER),
        edit_in_place=True,
    )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_OFFER_FIXED)
async def cb_admin_offer_fixed(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, OFFER):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.set_state(AdminOfferFlow.waiting_fixed)
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_OFFER_FIXED_PROMPT,
        keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_OFFER),
        edit_in_place=True,
    )
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminOfferFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminOfferFlow)
)
async def offer_flow_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    user_id = event.from_user.id if event.from_user else None
    if user_id is None or not admin_can(user_id, OFFER, settings, db):
        msg = (
            texts.NOT_ADMIN
            if user_id is None or not is_admin(user_id, settings)
            else texts.NOT_PERMITTED
        )
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return
    await state.clear()
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await send_offer_menu(event.message, db, edit_in_place=True)
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(AdminOfferFlow.waiting_percent))
async def offer_percent_input(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, OFFER):
        await state.clear()
        return
    raw = (message.text or "").strip().rstrip("%")
    try:
        pct = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    if not 1 <= pct <= 99:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    await state.clear()
    db.set_global_offer("percent", pct)
    await message.answer(
        texts.ADMIN_OFFER_SET_OK.format(
            offer_desc=describe_offer(db.get_offer_config())
        ),
        reply_markup=keyboards.admin_offer_inline(db),
    )


@router.message(StateFilter(AdminOfferFlow.waiting_amount))
async def offer_amount_input(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, OFFER):
        await state.clear()
        return
    try:
        amount = int((message.text or "").strip().replace(",", ""))
    except ValueError:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    if amount <= 0:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    await state.clear()
    db.set_global_offer("amount", amount)
    await message.answer(
        texts.ADMIN_OFFER_SET_OK.format(
            offer_desc=describe_offer(db.get_offer_config())
        ),
        reply_markup=keyboards.admin_offer_inline(db),
    )


@router.message(StateFilter(AdminOfferFlow.waiting_fixed))
async def offer_fixed_input(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, OFFER):
        await state.clear()
        return
    try:
        price = int((message.text or "").strip().replace(",", ""))
    except ValueError:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    if price < 0:
        await message.answer(texts.ADMIN_OFFER_INVALID)
        return
    await state.clear()
    db.set_global_offer("fixed", price)
    await message.answer(
        texts.ADMIN_OFFER_SET_OK.format(
            offer_desc=describe_offer(db.get_offer_config())
        ),
        reply_markup=keyboards.admin_offer_inline(db),
    )
