"""Owner-only: edit role permission matrix in the bot."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import is_owner
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import admin_from_message
from app.handlers.admin_ui_helpers import admin_edit_or_answer
from app.role_permissions import (
    CONFIGURABLE_ROLES,
    format_full_matrix_text,
    format_role_editor_text,
    reset_all_role_permissions,
    reset_role_permissions,
    toggle_role_permission,
)

router = Router(name="admin_permission_management")


def _require_owner(callback: CallbackQuery, settings: Settings) -> bool:
    if callback.from_user is None or not is_owner(callback.from_user.id, settings):
        return False
    return True


async def send_perm_matrix_home(
    message: Message, db: Database, *, edit_in_place: bool = False
) -> None:
    await admin_edit_or_answer(
        message,
        format_full_matrix_text(db),
        keyboards.admin_perm_matrix_home_keyboard(),
        edit_in_place=edit_in_place,
    )


async def send_role_perm_editor(
    message: Message,
    db: Database,
    role: str,
    *,
    edit_in_place: bool = False,
) -> None:
    await admin_edit_or_answer(
        message,
        format_role_editor_text(db, role),
        keyboards.admin_perm_role_keyboard(role, db),
        edit_in_place=edit_in_place,
    )


@router.callback_query(F.data == keyboards.CB_ADM_PERM_MATRIX)
async def cb_perm_matrix_home(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not _require_owner(callback, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_perm_matrix_home(callback.message, db, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_PERM_RESET_PREFIX))
async def cb_perm_reset_role(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not _require_owner(callback, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    role = (callback.data or "").removeprefix(keyboards.CB_ADM_PERM_RESET_PREFIX)
    if role not in CONFIGURABLE_ROLES:
        await callback.answer()
        return
    reset_role_permissions(db, role)
    if isinstance(callback.message, Message):
        await send_role_perm_editor(
            callback.message, db, role, edit_in_place=True
        )
    await callback.answer(texts.ADMIN_PERM_RESET_ROLE_OK)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_PERM_ROLE_PREFIX))
async def cb_perm_role_open(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not _require_owner(callback, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    role = (callback.data or "").removeprefix(keyboards.CB_ADM_PERM_ROLE_PREFIX)
    if role not in CONFIGURABLE_ROLES:
        await callback.answer()
        return
    if isinstance(callback.message, Message):
        await send_role_perm_editor(
            callback.message, db, role, edit_in_place=True
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_PERM_TOGGLE_PREFIX))
async def cb_perm_toggle(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not _require_owner(callback, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_PERM_TOGGLE_PREFIX)
    parts = raw.split(":", 1)
    if len(parts) != 2:
        await callback.answer()
        return
    role, perm = parts[0], parts[1]
    if role not in CONFIGURABLE_ROLES:
        await callback.answer()
        return
    try:
        enabled = toggle_role_permission(db, role, perm)
    except ValueError:
        await callback.answer(texts.ADMIN_PERM_PANEL_REQUIRED, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_role_perm_editor(
            callback.message, db, role, edit_in_place=True
        )
    state = "روشن" if enabled else "خاموش"
    await callback.answer(f"{perm}: {state}")


@router.callback_query(F.data == keyboards.CB_ADM_PERM_RESET_ALL)
async def cb_perm_reset_all(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not _require_owner(callback, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    reset_all_role_permissions(db)
    if isinstance(callback.message, Message):
        await send_perm_matrix_home(callback.message, db, edit_in_place=True)
    await callback.answer(texts.ADMIN_PERM_RESET_ALL_OK)


@router.message(Command("adminperms"))
async def cmd_adminperms(
    message: Message, settings: Settings, db: Database
) -> None:
    if not admin_from_message(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    if message.from_user is None or not is_owner(message.from_user.id, settings):
        await message.answer(texts.NOT_PERMITTED)
        return
    await send_perm_matrix_home(message, db)
