"""Mandatory Telegram channel membership before using the bot."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database

log = logging.getLogger(__name__)

_MEMBER_OK = frozenset({"creator", "administrator", "member", "restricted"})
_PROMPT_COOLDOWN_SEC = 30.0
_BOT_CHECK_CACHE_SEC = 120.0
_ADMIN_ALERT_COOLDOWN_SEC = 3600.0

# chat_id -> (message_id, monotonic timestamp)
_prompt_by_chat: dict[int, tuple[int, float]] = {}
# channel_id -> (can_check, monotonic timestamp)
_bot_check_by_channel: dict[int, tuple[bool, float]] = {}
_last_admin_alert_at = 0.0


@dataclass(frozen=True)
class MembershipCheck:
    joined: bool
    """True when the bot cannot verify membership (misconfigured channel/bot)."""

    gate_unavailable: bool = False


def required_channel_id(db: Database, settings: Settings) -> int | None:
    """Active channel id. Env applies only until admin explicitly disables the gate."""
    if db.is_required_channel_turned_off():
        return None
    cid = db.get_required_channel_id()
    if cid is not None:
        return cid
    return settings.required_channel_id


def is_gate_enabled(db: Database, settings: Settings) -> bool:
    return required_channel_id(db, settings) is not None


async def bot_can_check_channel(bot: Bot, channel_id: int) -> bool:
    now = time.monotonic()
    cached = _bot_check_by_channel.get(channel_id)
    if cached is not None and now - cached[1] < _BOT_CHECK_CACHE_SEC:
        return cached[0]

    ok = False
    try:
        me = await bot.get_me()
        member = await bot.get_chat_member(channel_id, me.id)
        ok = member.status in ("administrator", "creator")
    except TelegramBadRequest as exc:
        log.warning(
            "bot membership check failed channel=%s: %s",
            channel_id,
            exc.message or exc,
        )

    _bot_check_by_channel[channel_id] = (ok, now)
    return ok


async def check_user_membership(
    bot: Bot, db: Database, settings: Settings, user_id: int
) -> MembershipCheck:
    channel_id = required_channel_id(db, settings)
    if channel_id is None:
        return MembershipCheck(joined=True)

    if not await bot_can_check_channel(bot, channel_id):
        return MembershipCheck(joined=False, gate_unavailable=True)

    try:
        member = await bot.get_chat_member(channel_id, user_id)
        return MembershipCheck(joined=member.status in _MEMBER_OK)
    except TelegramBadRequest as exc:
        log.warning(
            "get_chat_member failed channel=%s user=%s: %s",
            channel_id,
            user_id,
            exc.message or exc,
        )
        return MembershipCheck(joined=False, gate_unavailable=True)


async def is_user_joined(
    bot: Bot, db: Database, settings: Settings, user_id: int
) -> bool:
    result = await check_user_membership(bot, db, settings, user_id)
    return result.joined and not result.gate_unavailable


async def notify_admins_gate_broken(bot: Bot, settings: Settings, channel_id: int) -> None:
    global _last_admin_alert_at
    now = time.monotonic()
    if now - _last_admin_alert_at < _ADMIN_ALERT_COOLDOWN_SEC:
        return
    _last_admin_alert_at = now
    body = texts.JOIN_GATE_ADMIN_ALERT.format(channel_id=channel_id)
    for admin_id in settings.admin_ids:
        try:
            await bot.send_message(admin_id, body, parse_mode=ParseMode.HTML)
        except TelegramBadRequest:
            pass


async def resolve_join_url(
    bot: Bot, db: Database, settings: Settings
) -> str | None:
    stored = db.get_required_channel_link()
    if stored:
        return stored
    channel_id = required_channel_id(db, settings)
    if channel_id is None:
        return None
    try:
        chat = await bot.get_chat(channel_id)
        if chat.username:
            return f"https://t.me/{chat.username}"
        return await bot.export_chat_invite_link(channel_id)
    except TelegramBadRequest as exc:
        log.warning("resolve_join_url channel=%s: %s", channel_id, exc.message or exc)
        return None


def channel_label(db: Database, settings: Settings) -> str:
    title = db.get_required_channel_title()
    if title:
        return escape(title)
    cid = required_channel_id(db, settings)
    if cid is None:
        return "—"
    return f"<code>{cid}</code>"


async def join_prompt_text(bot: Bot, db: Database, settings: Settings) -> str:
    body = texts.JOIN_CHANNEL_REQUIRED.format(channel=channel_label(db, settings))
    if not await resolve_join_url(bot, db, settings):
        body += texts.JOIN_CHANNEL_NO_LINK_HINT
    return body


def _normalize_invite_link(raw: str) -> str | None:
    text = raw.strip()
    if not text:
        return None
    if text.startswith(("https://t.me/", "http://t.me/", "t.me/")):
        if text.startswith("t.me/"):
            return f"https://{text}"
        if text.startswith("http://"):
            return "https://" + text.removeprefix("http://")
        return text
    return None


async def send_join_prompt(
    bot: Bot,
    db: Database,
    settings: Settings,
    *,
    chat_id: int,
    message: Message | None = None,
    force: bool = False,
) -> None:
    body = await join_prompt_text(bot, db, settings)
    join_url = await resolve_join_url(bot, db, settings)
    markup = keyboards.join_channel_keyboard(join_url)
    now = time.monotonic()
    cached = _prompt_by_chat.get(chat_id)

    if not force and cached is not None:
        msg_id, sent_at = cached
        if now - sent_at < _PROMPT_COOLDOWN_SEC:
            try:
                await bot.edit_message_text(
                    chat_id=chat_id,
                    message_id=msg_id,
                    text=body,
                    reply_markup=markup,
                    parse_mode=ParseMode.HTML,
                )
                return
            except TelegramBadRequest:
                pass

    sent: Message | None = None
    if message is not None:
        sent = await message.answer(body, reply_markup=markup)
    else:
        sent = await bot.send_message(chat_id, body, reply_markup=markup)

    if sent is not None:
        _prompt_by_chat[chat_id] = (sent.message_id, now)


async def send_gate_unavailable(
    bot: Bot,
    settings: Settings,
    event: Message | CallbackQuery,
    channel_id: int,
) -> None:
    await notify_admins_gate_broken(bot, settings, channel_id)
    if isinstance(event, Message):
        await event.answer(texts.JOIN_GATE_UNAVAILABLE)
        return
    if event.from_user is None:
        await event.answer()
        return
    await event.answer(texts.JOIN_GATE_UNAVAILABLE_SHORT, show_alert=True)


async def reply_join_required(
    bot: Bot,
    db: Database,
    settings: Settings,
    event: Message | CallbackQuery,
    *,
    force: bool = False,
) -> None:
    chat_id: int | None = None
    if isinstance(event, Message):
        chat_id = event.chat.id
    elif event.message is not None:
        chat_id = event.message.chat.id

    if chat_id is None:
        if isinstance(event, CallbackQuery):
            await event.answer()
        return

    if isinstance(event, CallbackQuery):
        if event.from_user is None:
            await event.answer()
            return
        await event.answer(texts.JOIN_CHANNEL_REQUIRED_SHORT, show_alert=True)
        cached = _prompt_by_chat.get(chat_id)
        if not force and cached is not None:
            if time.monotonic() - cached[1] < _PROMPT_COOLDOWN_SEC:
                return
        await send_join_prompt(
            bot,
            db,
            settings,
            chat_id=chat_id,
            message=event.message if isinstance(event.message, Message) else None,
            force=force,
        )
        return

    await send_join_prompt(
        bot,
        db,
        settings,
        chat_id=chat_id,
        message=event,
        force=force,
    )


async def try_bind_required_channel(
    bot: Bot, db: Database, chat_id: int
) -> tuple[bool, str, bool]:
    """Returns (ok, admin_message, needs_invite_link)."""
    try:
        chat = await bot.get_chat(chat_id)
        me = await bot.get_me()
        bot_member = await bot.get_chat_member(chat_id, me.id)
        if bot_member.status not in ("administrator", "creator"):
            return False, texts.REQ_CHANNEL_BOT_NOT_ADMIN, False
    except TelegramBadRequest as exc:
        return False, texts.REQ_CHANNEL_BAD.format(
            error=escape(str(exc.message or exc))
        ), False
    except Exception as exc:  # noqa: BLE001
        log.exception("bind required channel %s", chat_id)
        return False, texts.REQ_CHANNEL_BAD.format(error=escape(str(exc))), False

    _bot_check_by_channel[chat_id] = (True, time.monotonic())

    link: str | None = None
    if chat.username:
        link = f"https://t.me/{chat.username}"
    else:
        try:
            link = await bot.export_chat_invite_link(chat_id)
        except (TelegramBadRequest, TelegramForbiddenError):
            link = None

    db.set_required_channel(
        chat_id,
        title=chat.title or "",
        link=link,
    )

    if link:
        link_line = f"\n🔗 لینک: {escape(link)}"
        return True, texts.REQ_CHANNEL_OK.format(
            chat_id=chat_id,
            title=escape(chat.title or "—"),
            link_line=link_line,
        ), False

    return True, texts.REQ_CHANNEL_OK_NEED_LINK.format(
        chat_id=chat_id,
        title=escape(chat.title or "—"),
    ), True


def save_invite_link(db: Database, raw: str) -> tuple[bool, str]:
    link = _normalize_invite_link(raw)
    if link is None:
        return False, texts.REQ_CHANNEL_LINK_INVALID
    if db.get_required_channel_id() is None:
        return False, texts.REQ_CHANNEL_LINK_NO_CHANNEL
    db.set_required_channel_link(link)
    return True, texts.REQ_CHANNEL_LINK_SAVED.format(link=escape(link))
