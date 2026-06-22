"""Shared admin UI helpers (edit-in-place, formatted menus)."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app import texts
from app.db import Database

log = logging.getLogger(__name__)


def callback_inline_ids(callback: CallbackQuery) -> tuple[int, int] | None:
    """Chat and message id for the message that owns the tapped inline button."""
    msg = callback.message
    if msg is None:
        return None
    return msg.chat.id, msg.message_id


async def present_inline_screen(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | None,
    prefer_edit: bool,
) -> bool:
    """Update an existing inline message or send a new one (reliable for callbacks)."""
    if prefer_edit and message_id is not None:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return True
        except TelegramBadRequest as exc:
            err = (exc.message or str(exc)).lower()
            log.warning(
                "inline edit failed chat=%s msg=%s: %s",
                chat_id,
                message_id,
                exc.message or exc,
            )
            if "message is not modified" in err:
                if reply_markup is not None:
                    try:
                        await bot.edit_message_reply_markup(
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=reply_markup,
                        )
                        return True
                    except TelegramBadRequest:
                        pass
                return True
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML,
    )
    return True


async def admin_edit_or_answer(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
    *,
    edit_in_place: bool = False,
) -> None:
    """Prefer editing the current message; fall back to a new one."""
    if edit_in_place:
        try:
            await message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return
        except TelegramBadRequest as exc:
            err = (exc.message or "").lower()
            if "message is not modified" in err:
                if reply_markup is not None:
                    try:
                        await message.edit_reply_markup(reply_markup=reply_markup)
                        return
                    except TelegramBadRequest:
                        pass
                # Same text but markup may differ, or caller needs a visible refresh.
                await message.answer(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
                return
            if "privacy_restricted" in err or "user_privacy" in err:
                reply_markup = None
            try:
                await message.edit_text(
                    text,
                    reply_markup=reply_markup,
                    parse_mode=ParseMode.HTML,
                )
                return
            except TelegramBadRequest:
                pass
    try:
        await message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
    except TelegramBadRequest as exc:
        err = (exc.message or "").lower()
        if "privacy_restricted" in err or "user_privacy" in err:
            await message.answer(text, parse_mode=ParseMode.HTML)
        else:
            log.error(f"admin_edit_or_answer completely failed: {exc}")
            raise


def format_services_list_text(db: Database, *, loc_filter: int | None = None) -> str:
    packages = (
        db.list_service_packages(loc_filter, only_enabled=False)
        if loc_filter is not None
        else db.list_all_service_packages()
    )
    mode = "روشن ✅" if db.is_manual_purchase_enabled() else "خاموش ❌"
    if not packages:
        body = texts.LIST_SERVICES_EMPTY
    else:
        filter_line = f" — لوکیشن <code>#{loc_filter}</code>" if loc_filter else ""
        lines = [texts.LIST_SERVICES_HEADER.format(filter_line=filter_line)]
        from app.pricing import format_price_with_offer

        offer = db.get_offer_config()
        for pkg in packages:
            loc = db.get_location(pkg.location_id)
            loc_name = escape(loc.name) if loc else "—"
            base = int(pkg.price)
            final = db.resolve_price(base)
            if offer.is_active and final < base:
                price_label = format_price_with_offer(base, final)
            else:
                price_label = texts.format_price(base)
            lines.append(
                texts.LIST_SERVICES_LINE.format(
                    id=pkg.id,
                    loc_id=pkg.location_id,
                    loc_name=loc_name,
                    volume=pkg.volume_gb,
                    days=pkg.duration_days,
                    price=price_label,
                )
            )
        body = "\n".join(lines)
    return texts.ADMIN_SERVICES_MENU.format(
        manual_mode=mode,
        packages_block=body,
    )


def format_tools_menu_text(db: Database, settings) -> str:
    from app.channel_gate import channel_label, is_gate_enabled

    log_id = db.get_log_channel_id()
    log_line = (
        f"متصل: <code>{log_id}</code> ✅"
        if log_id
        else "غیرفعال ❌"
    )
    req_line = (
        f"{channel_label(db, settings)} ✅"
        if is_gate_enabled(db, settings)
        else "غیرفعال ❌"
    )
    test_line = "روشن ✅" if db.is_test_feature_enabled() else "خاموش ❌"
    return texts.ADMIN_TOOLS_MENU.format(
        log_channel=log_line,
        req_channel=req_line,
        test_sub=test_line,
    )
