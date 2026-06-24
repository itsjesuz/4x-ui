"""Show / hide the Telegram reply keyboard (bottom menu buttons).

Use Telegram's built-in behaviour:
- attach ``ReplyKeyboardMarkup`` on a normal ``message.answer(...)`` to show the menu
- attach ``ReplyKeyboardRemove()`` on a message that has real (non-empty) text
- use ``answer_with_inline_keyboard`` to hide the reply menu and show inline buttons
  in a single chat message
"""

from __future__ import annotations

import logging

from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import InlineKeyboardMarkup, Message

from app import keyboards

log = logging.getLogger(__name__)


async def answer_with_inline_keyboard(
    message: Message,
    text: str,
    inline_markup: InlineKeyboardMarkup,
    *,
    parse_mode: str | ParseMode | None = ParseMode.HTML,
    remove_reply_keyboard: bool = True,
) -> Message:
    """Hide the reply keyboard (if requested) and show inline buttons — one message."""
    if not remove_reply_keyboard:
        return await message.answer(
            text,
            reply_markup=inline_markup,
            parse_mode=parse_mode,
        )

    sent = await message.answer(
        text,
        reply_markup=keyboards.hide_reply_keyboard(),
        parse_mode=parse_mode,
    )
    try:
        await sent.edit_text(
            text,
            reply_markup=inline_markup,
            parse_mode=parse_mode,
        )
        return sent
    except TelegramBadRequest:
        log.debug("edit_text for inline keyboard failed", exc_info=True)

    try:
        await sent.delete()
    except Exception:  # noqa: BLE001
        log.debug("could not delete keyboard-remove stub message", exc_info=True)

    return await message.answer(
        text,
        reply_markup=inline_markup,
        parse_mode=parse_mode,
    )


async def answer_removing_reply_keyboard(
    message: Message,
    text: str,
    *,
    parse_mode: str | ParseMode | None = ParseMode.HTML,
) -> Message:
    """Send text and remove the bottom reply keyboard."""
    return await message.answer(
        text,
        reply_markup=keyboards.hide_reply_keyboard(),
        parse_mode=parse_mode,
    )
