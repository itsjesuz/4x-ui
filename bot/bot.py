"""NetFly Telegram bot — entry point.

Run with:  python bot.py
Requires a .env file (see .env.example) with at least BOT_TOKEN set.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from app.config import load_settings
from app.db import Database
from app.handlers import build_root_router
from app.middlewares import ChannelJoinMiddleware, UserMiddleware


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
log = logging.getLogger("netfly")


PUBLIC_COMMANDS = [
    BotCommand(command="start",  description="شروع و نمایش منوی اصلی"),
    BotCommand(command="help",   description="راهنمای استفاده از ربات"),
    BotCommand(command="cancel", description="لغو عملیات در حال انجام"),
]


async def main() -> None:
    settings = load_settings()
    if not settings.is_configured:
        log.error(
            "BOT_TOKEN is missing or still set to the placeholder. "
            "Copy .env.example to .env and fill in your real token."
        )
        sys.exit(1)

    db = Database(settings.db_path)
    log.info("Database ready at %s", settings.db_path)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Make the Settings instance available to handlers via DI.
    dp["settings"] = settings

    user_mw = UserMiddleware(db, settings)
    join_mw = ChannelJoinMiddleware(db, settings)
    dp.message.middleware(user_mw)
    dp.callback_query.middleware(user_mw)
    dp.message.middleware(join_mw)
    dp.callback_query.middleware(join_mw)

    dp.include_router(build_root_router())

    await bot.set_my_commands(PUBLIC_COMMANDS)
    me = await bot.get_me()
    log.info("Starting NetFly bot as @%s (id=%s)", me.username, me.id)

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        db.close()
        log.info("Bot stopped cleanly.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Interrupted by user.")
