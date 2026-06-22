"""Admin broadcast: text, photo, video, document, and other single messages."""

from __future__ import annotations

import asyncio
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ContentType, ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import TOOLS_BROADCAST
from app.handlers.admin_helpers import (
    admin_can,
    guard_admin_callback,
    guard_admin_message,
    is_admin,
)
from app.logs import Actor, make_logger

router = Router(name="admin_broadcast")
log = logging.getLogger(__name__)

BROADCAST_DELAY_SEC = 0.05
BROADCAST_PROGRESS_EVERY = 25


class BroadcastFlow(StatesGroup):
    waiting_content = State()
    waiting_confirm = State()


_CONTENT_TYPE_FA: dict[str, str] = {
    ContentType.TEXT.value: "متن",
    ContentType.PHOTO.value: "عکس",
    ContentType.VIDEO.value: "ویدیو",
    ContentType.DOCUMENT.value: "فایل",
    ContentType.ANIMATION.value: "گیف",
    ContentType.AUDIO.value: "صوت",
    ContentType.VOICE.value: "ویس",
    ContentType.VIDEO_NOTE.value: "ویدیو دایره‌ای",
    ContentType.STICKER.value: "استیکر",
}


def _content_type_label(message: Message) -> str:
    return _CONTENT_TYPE_FA.get(message.content_type, message.content_type)


def _caption_preview(message: Message, *, max_len: int = 120) -> str:
    cap = (message.caption or message.text or "").strip()
    if not cap:
        return "—"
    if len(cap) > max_len:
        return cap[: max_len - 1] + "…"
    return cap


async def _start_broadcast_wizard(message: Message, state: FSMContext) -> None:
    from app.ui_reply import answer_with_inline_keyboard

    await state.clear()
    await state.set_state(BroadcastFlow.waiting_content)
    await answer_with_inline_keyboard(
        message,
        texts.BROADCAST_PROMPT,
        keyboards.broadcast_cancel_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def run_broadcast_copy(
    bot: Bot,
    *,
    from_chat_id: int,
    message_id: int,
    user_ids: list[int],
    progress_message: Message | None = None,
) -> tuple[int, int]:
    """Copy one admin message to every user. Returns (ok, fail)."""
    ok = 0
    fail = 0
    total = len(user_ids)

    for i, uid in enumerate(user_ids, start=1):
        try:
            await bot.copy_message(
                chat_id=uid,
                from_chat_id=from_chat_id,
                message_id=message_id,
            )
            ok += 1
        except Exception:  # noqa: BLE001 — blocked bot, deactivated account, etc.
            fail += 1

        if (
            progress_message is not None
            and total > 0
            and (i % BROADCAST_PROGRESS_EVERY == 0 or i == total)
        ):
            try:
                await progress_message.edit_text(
                    texts.BROADCAST_PROGRESS.format(
                        done=i, total=total, ok=ok, fail=fail
                    ),
                    parse_mode=ParseMode.HTML,
                )
            except Exception:  # noqa: BLE001
                pass

        await asyncio.sleep(BROADCAST_DELAY_SEC)

    return ok, fail


async def send_quick_text_broadcast(
    message: Message, bot: Bot, db: Database, text: str
) -> None:
    user_ids = db.all_user_ids()
    await message.answer(
        texts.BROADCAST_STARTED.format(count=len(user_ids)),
        parse_mode=ParseMode.HTML,
    )
    ok = 0
    fail = 0
    for uid in user_ids:
        try:
            await bot.send_message(uid, text)
            ok += 1
        except Exception:  # noqa: BLE001
            fail += 1
        await asyncio.sleep(BROADCAST_DELAY_SEC)
    await message.answer(
        texts.BROADCAST_DONE.format(ok=ok, fail=fail),
        parse_mode=ParseMode.HTML,
    )


# ---------- entry ----------
@router.message(Command("broadcast"), StateFilter(None))
async def cmd_broadcast_entry(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_BROADCAST):
        return

    args = (message.text or "").split(maxsplit=1)
    if len(args) > 1 and args[1].strip():
        await send_quick_text_broadcast(message, bot, db, args[1].strip())
        return

    await _start_broadcast_wizard(message, state)


@router.callback_query(F.data == keyboards.CB_ADM_BROADCAST, StateFilter(None))
async def cb_broadcast_start(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, TOOLS_BROADCAST):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await _start_broadcast_wizard(callback.message, state)
    await callback.answer()


# ---------- cancel ----------
@router.message(Command("cancel"), StateFilter(BroadcastFlow))
@router.callback_query(F.data == keyboards.CB_BROADCAST_CANCEL, StateFilter(BroadcastFlow))
async def broadcast_cancel(
    event: Message | CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    user_id = event.from_user.id if event.from_user else None
    if user_id is None or not admin_can(user_id, TOOLS_BROADCAST, settings, db):
        msg = (
            texts.NOT_ADMIN
            if user_id is None or not is_admin(user_id, settings)
            else texts.NOT_PERMITTED
        )
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        return

    await state.clear()
    text = texts.BROADCAST_CANCELLED
    kb = (
        keyboards.admin_reply_keyboard(user_id, settings, db)
        if user_id is not None
        else None
    )
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            try:
                await event.message.edit_text(text, reply_markup=None)
            except Exception:  # noqa: BLE001
                await event.message.answer(text)
        await event.answer()
    else:
        await event.answer(text, reply_markup=kb)


# ---------- receive content ----------
@router.message(StateFilter(BroadcastFlow.waiting_content))
async def on_broadcast_content(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_BROADCAST):
        return

    if message.media_group_id:
        await message.answer(texts.BROADCAST_ALBUM_UNSUPPORTED, parse_mode=ParseMode.HTML)
        return

    if message.from_user is None or message.chat is None:
        return

    user_count = len(db.all_user_ids())
    await state.update_data(
        from_chat_id=message.chat.id,
        message_id=message.message_id,
        admin_id=message.from_user.id,
        content_type=message.content_type,
    )
    await state.set_state(BroadcastFlow.waiting_confirm)

    preview = texts.BROADCAST_PREVIEW.format(
        type_label=_content_type_label(message),
        caption_preview=escape(_caption_preview(message)),
        count=user_count,
    )
    await message.answer(
        preview,
        reply_markup=keyboards.broadcast_confirm_keyboard(),
        parse_mode=ParseMode.HTML,
    )


# ---------- confirm & send ----------
@router.callback_query(
    F.data == keyboards.CB_BROADCAST_CONFIRM,
    StateFilter(BroadcastFlow.waiting_confirm),
)
async def cb_broadcast_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_callback(callback, settings, db, TOOLS_BROADCAST):
        return

    data = await state.get_data()
    if int(data.get("admin_id", 0)) != callback.from_user.id:
        await callback.answer(texts.BROADCAST_WRONG_ADMIN, show_alert=True)
        return

    from_chat_id = int(data.get("from_chat_id", 0))
    message_id = int(data.get("message_id", 0))
    if not from_chat_id or not message_id:
        await state.clear()
        await callback.answer("پیام یافت نشد.", show_alert=True)
        return

    user_ids = db.all_user_ids()
    await state.clear()

    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await callback.message.edit_text(
        texts.BROADCAST_STARTED.format(count=len(user_ids)),
        reply_markup=None,
        parse_mode=ParseMode.HTML,
    )
    await callback.answer("📣 در حال ارسال...")

    ok, fail = await run_broadcast_copy(
        bot,
        from_chat_id=from_chat_id,
        message_id=message_id,
        user_ids=user_ids,
        progress_message=callback.message,
    )

    uid = callback.from_user.id
    await callback.message.answer(
        texts.BROADCAST_DONE.format(ok=ok, fail=fail),
        reply_markup=keyboards.admin_reply_keyboard(uid, settings, db),
        parse_mode=ParseMode.HTML,
    )

    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_broadcast_done(
            admin=admin,
            total=len(user_ids),
            ok=ok,
            fail=fail,
        )


@router.message(StateFilter(BroadcastFlow.waiting_confirm))
async def on_broadcast_confirm_waiting(
    message: Message, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_BROADCAST):
        return
    await message.answer(texts.BROADCAST_CONFIRM_HINT, parse_mode=ParseMode.HTML)
