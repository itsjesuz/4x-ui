from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware, Bot
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from app import keyboards, texts
from app.admin_perms import is_staff
from app.channel_gate import (
    check_user_membership,
    is_gate_enabled,
    reply_join_required,
    required_channel_id,
    send_gate_unavailable,
)
from app.config import Settings
from app.db import Database

log = logging.getLogger(__name__)


class UserMiddleware(BaseMiddleware):
    """Auto-register every Telegram user we see, and short-circuit banned users.

    Also injects the `Database` instance into handler data so handlers can use
    `db: Database` as a parameter.
    """

    def __init__(self, db: Database, settings: Settings) -> None:
        super().__init__()
        self.db = db
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: User | None = data.get("event_from_user")

        if tg_user is not None and not tg_user.is_bot:
            self.db.upsert_user(
                user_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                lang_code=tg_user.language_code,
            )

            if self.db.is_banned(tg_user.id) and not is_staff(
                tg_user.id, self.settings
            ):
                if isinstance(event, Message):
                    await event.answer(texts.USER_BANNED)
                elif isinstance(event, CallbackQuery):
                    await event.answer(texts.USER_BANNED, show_alert=True)
                return None

        data["db"] = self.db
        return await handler(event, data)


class ChannelJoinMiddleware(BaseMiddleware):
    """Block non-members until they join the configured channel."""

    def __init__(self, db: Database, settings: Settings) -> None:
        super().__init__()
        self.db = db
        self.settings = settings

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if not is_gate_enabled(self.db, self.settings):
            return await handler(event, data)

        tg_user: User | None = data.get("event_from_user")
        if tg_user is None or tg_user.is_bot:
            return await handler(event, data)

        if is_staff(tg_user.id, self.settings):
            return await handler(event, data)

        if isinstance(event, CallbackQuery) and event.data == keyboards.CB_MAIN_CHECK_JOIN:
            return await handler(event, data)

        bot: Bot | None = data.get("bot")
        if bot is None:
            log.error("ChannelJoinMiddleware: bot missing from handler data")
            return None

        channel_id = required_channel_id(self.db, self.settings)
        check = await check_user_membership(
            bot, self.db, self.settings, tg_user.id
        )

        if check.gate_unavailable and channel_id is not None:
            if isinstance(event, (Message, CallbackQuery)):
                await send_gate_unavailable(bot, self.settings, event, channel_id)
            return None

        if check.joined:
            return await handler(event, data)

        if isinstance(event, (Message, CallbackQuery)):
            await reply_join_required(bot, self.db, self.settings, event)
        return None
