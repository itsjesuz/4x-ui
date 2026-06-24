"""Notify all admins when an order review is finalized (remove duplicate actions)."""

from __future__ import annotations

import logging

from aiogram import Bot

from app import texts
from app.db import Database

log = logging.getLogger(__name__)


async def clear_admin_receipt_buttons(
    bot: Bot,
    db: Database,
    order_id: int,
    *,
    acting_admin_id: int | None = None,
    action: str,
) -> None:
    """Remove Accept/Decline buttons from every admin's receipt copy of this order."""
    refs = db.get_admin_receipt_refs(order_id)
    if not refs:
        return

    for admin_id, message_id in refs.items():
        try:
            await bot.edit_message_reply_markup(
                chat_id=admin_id,
                message_id=message_id,
                reply_markup=None,
            )
        except Exception:  # noqa: BLE001 — message deleted or too old
            log.debug(
                "Could not clear review buttons for admin %s msg %s",
                admin_id,
                message_id,
                exc_info=True,
            )

    for admin_id in refs:
        if acting_admin_id is not None and admin_id == acting_admin_id:
            continue
        try:
            await bot.send_message(
                admin_id,
                texts.REVIEW_OTHER_ADMIN_DONE.format(
                    order_id=order_id,
                    action=action,
                    admin_id=acting_admin_id or "—",
                ),
            )
        except Exception:  # noqa: BLE001
            log.debug("Could not notify admin %s about closed review", admin_id)
