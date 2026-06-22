"""Shared buyer menu helpers (test button visibility)."""

from __future__ import annotations

from aiogram.types import Message

from app import keyboards
from app.db import Database


def buyer_show_test_button(db: Database, user_id: int) -> bool:
    if not db.is_test_feature_enabled():
        return False
    if db.get_test_location() is None:
        return False
    if db.user_has_claimed_test(user_id):
        return False
    return True


def buyer_reply_keyboard(
    message: Message, db: Database, *, user_id: int | None = None
):
    uid = user_id
    if uid is None:
        user = message.from_user
        if user is None or user.is_bot:
            return keyboards.main_reply_keyboard(show_test=False)
        uid = user.id
    show_test = buyer_show_test_button(db, uid)
    return keyboards.main_reply_keyboard(show_test=show_test)
