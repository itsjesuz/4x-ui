from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import USERS
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.buyer_ui import buyer_show_test_button
from app.logs import Actor, make_logger


router = Router(name="support")
log = logging.getLogger(__name__)

MAX_TICKET_LEN = 2000


class SupportFlow(StatesGroup):
    waiting_for_message = State()


class SupportAdminFlow(StatesGroup):
    waiting_reply = State()


def _buyer_keyboard_for(user_id: int | None, db: Database):
    show_test = user_id is not None and buyer_show_test_button(db, user_id)
    return keyboards.main_reply_keyboard(show_test=show_test)


async def _open_support_message(message: Message, state: FSMContext) -> None:
    await state.clear()
    from app.ui_reply import answer_with_inline_keyboard
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="ورود به ربات پشتیبانی", url="https://t.me/NetFlySupportBot")],
        [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=keyboards.CB_CANCEL_SUPPORT, style='danger')]
    ])

    await answer_with_inline_keyboard(
        message,
        texts.SUPPORT_PROMPT,
        keyboard,
    )


@router.message(F.text == texts.BTN_SUPPORT, StateFilter(None))
async def msg_open_support(message: Message, state: FSMContext) -> None:
    await _open_support_message(message, state)


@router.callback_query(F.data == keyboards.CB_MAIN_SUPPORT)
async def cb_open_support(callback: CallbackQuery, state: FSMContext) -> None:
    if isinstance(callback.message, Message):
        await _open_support_message(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_CANCEL_SUPPORT)
async def cb_cancel_support(
    callback: CallbackQuery, state: FSMContext, db: Database
) -> None:
    await state.clear()
    if callback.message is not None:
        user_id = callback.from_user.id if callback.from_user is not None else None
        await callback.message.answer(
            texts.CANCELLED, reply_markup=_buyer_keyboard_for(user_id, db)
        )
    await callback.answer()


@router.message(Command("cancel"), StateFilter(SupportFlow.waiting_for_message))
async def cmd_cancel_support(
    message: Message, state: FSMContext, db: Database
) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user is not None else None
    await message.answer(texts.CANCELLED, reply_markup=_buyer_keyboard_for(user_id, db))


@router.message(StateFilter(SupportFlow.waiting_for_message))
async def on_support_message(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    text = (message.text or message.caption or "").strip()
    if not text:
        await message.answer(texts.SUPPORT_EMPTY)
        return
    if len(text) > MAX_TICKET_LEN:
        await message.answer(texts.SUPPORT_TOO_LONG)
        return

    user = message.from_user
    if user is None:
        await state.clear()
        return

    ticket_id = db.create_ticket(user_id=user.id, message=text)
    await state.clear()
    await message.answer(
        texts.SUPPORT_SENT, reply_markup=_buyer_keyboard_for(user.id, db)
    )

    full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
    notify = texts.NEW_TICKET_NOTIFY.format(
        ticket_id=ticket_id,
        user_id=user.id,
        full_name=escape(full_name),
        message=escape(text),
    )
    actor = Actor.from_user(user)
    if actor is not None:
        await make_logger(bot, db).log_support_ticket(
            ticket_id=ticket_id,
            user=actor,
            message=text,
        )

    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(
                admin_id,
                notify,
                reply_markup=keyboards.admin_support_ticket(ticket_id),
            )
        except Exception:  # noqa: BLE001
            log.exception("Failed to notify admin %s about ticket %s", admin_id, ticket_id)


def _ticket_id_from_callback(data: str | None, prefix: str) -> int | None:
    raw = (data or "").removeprefix(prefix)
    try:
        return int(raw)
    except ValueError:
        return None


@router.callback_query(F.data.startswith(keyboards.CB_SUPPORT_REPLY_PREFIX))
async def cb_support_reply(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, USERS):
        return
    ticket_id = _ticket_id_from_callback(
        callback.data, keyboards.CB_SUPPORT_REPLY_PREFIX
    )
    if ticket_id is None:
        await callback.answer()
        return

    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer(texts.SUPPORT_TICKET_NOT_FOUND, show_alert=True)
        return
    if str(ticket["status"]) == "closed":
        await callback.answer(texts.SUPPORT_TICKET_ALREADY_CLOSED, show_alert=True)
        return

    await state.set_state(SupportAdminFlow.waiting_reply)
    await state.update_data(ticket_id=ticket_id, ticket_user_id=int(ticket["user_id"]))
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.SUPPORT_REPLY_PROMPT.format(ticket_id=ticket_id),
            reply_markup=keyboards.admin_flow_cancel_inline(),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_SUPPORT_CLOSE_PREFIX))
async def cb_support_close(
    callback: CallbackQuery,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, USERS):
        return
    ticket_id = _ticket_id_from_callback(
        callback.data, keyboards.CB_SUPPORT_CLOSE_PREFIX
    )
    if ticket_id is None:
        await callback.answer()
        return

    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        await callback.answer(texts.SUPPORT_TICKET_NOT_FOUND, show_alert=True)
        return
    if str(ticket["status"]) == "closed":
        await callback.answer(texts.SUPPORT_TICKET_ALREADY_CLOSED, show_alert=True)
        return

    db.close_ticket(ticket_id)
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except Exception:  # noqa: BLE001 - message may be too old or uneditable.
            pass
    await callback.answer(texts.SUPPORT_TICKET_CLOSED.format(ticket_id=ticket_id))


@router.message(Command("cancel"), StateFilter(SupportAdminFlow.waiting_reply))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(SupportAdminFlow.waiting_reply)
)
async def cancel_support_reply(
    event: Message | CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(SupportAdminFlow.waiting_reply))
async def on_support_reply(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_message(message, settings, db, USERS):
        await state.clear()
        return

    reply = (message.text or message.caption or "").strip()
    if not reply:
        await message.answer(texts.SUPPORT_EMPTY)
        return
    if len(reply) > MAX_TICKET_LEN:
        await message.answer(texts.SUPPORT_TOO_LONG)
        return

    data = await state.get_data()
    ticket_id = int(data.get("ticket_id") or 0)
    user_id = int(data.get("ticket_user_id") or 0)
    ticket = db.get_ticket(ticket_id)
    if ticket is None:
        await state.clear()
        await message.answer(texts.SUPPORT_TICKET_NOT_FOUND)
        return
    if str(ticket["status"]) == "closed":
        await state.clear()
        await message.answer(texts.SUPPORT_TICKET_ALREADY_CLOSED)
        return

    try:
        await bot.send_message(
            user_id,
            texts.SUPPORT_REPLY_SENT_USER.format(message=escape(reply)),
        )
    except Exception:  # noqa: BLE001 - user may have blocked the bot.
        log.exception("Failed to send support reply for ticket %s", ticket_id)
        await message.answer(texts.SUPPORT_REPLY_FAILED_USER)
        return
    db.close_ticket(ticket_id)
    await state.clear()
    await message.answer(
        texts.SUPPORT_REPLY_SENT_ADMIN,
        reply_markup=keyboards.admin_reply_keyboard(message.from_user.id, settings, db)
        if message.from_user is not None
        else None,
    )
