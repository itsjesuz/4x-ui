"""Owner-only: assign roles to staff admins (ADMIN_IDS)."""

from __future__ import annotations


from aiogram import F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import VALID_ROLES, is_owner
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import admin_from_message
from app.handlers.admin_ui_helpers import admin_edit_or_answer

router = Router(name="admin_roles")


def _roles_menu_text(settings: Settings, db: Database) -> str:
    lines: list[str] = []
    for uid, role in db.list_staff_roles(settings.admin_ids):
        label = "👑 " + texts.ADMIN_ROLE_LABELS["owner"] if is_owner(uid, settings) else texts.ADMIN_ROLE_LABELS.get(role, role)
        lines.append(
            texts.ADMIN_ROLES_LINE.format(
                user_id=uid,
                role_label=label,
            )
        )
    body = "\n".join(lines) if lines else "<i>لیست ADMIN_IDS خالی است.</i>"
    return texts.ADMIN_ROLES_MENU.format(lines=body)


async def send_roles_menu(
    message: Message, settings: Settings, db: Database, *, edit_in_place: bool = False
) -> None:
    await admin_edit_or_answer(
        message,
        _roles_menu_text(settings, db),
        keyboards.admin_roles_keyboard(settings, db),
        edit_in_place=edit_in_place,
    )


@router.message(Command("setadminrole"))
async def cmd_setadminrole(
    message: Message,
    command: CommandObject,
    settings: Settings,
    db: Database,
) -> None:
    if not admin_from_message(message, settings):
        await message.answer(texts.NOT_ADMIN)
        return
    if message.from_user is None or not is_owner(message.from_user.id, settings):
        await message.answer(texts.NOT_PERMITTED)
        return

    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer(texts.ADMIN_ROLE_USAGE)
        return
    try:
        target_id = int(parts[0])
    except ValueError:
        await message.answer(texts.ADMIN_ROLE_USAGE)
        return
    role = parts[1].lower()
    if target_id not in settings.admin_ids:
        await message.answer("❗ این شناسه در ADMIN_IDS نیست.")
        return
    if is_owner(target_id, settings):
        await message.answer("❗ نقش مالک قابل تغییر نیست.")
        return
    if role not in VALID_ROLES:
        await message.answer(texts.ADMIN_ROLE_USAGE)
        return

    db.set_admin_role(target_id, role)
    await message.answer(
        texts.ADMIN_ROLE_SET_OK.format(
            user_id=target_id,
            role_label=texts.ADMIN_ROLE_LABELS.get(role, role),
        )
    )


@router.callback_query(F.data == keyboards.CB_ADM_ROLES)
async def cb_admin_roles_menu(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_owner(callback.from_user.id, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_roles_menu(callback.message, settings, db, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ROLE_SET_PREFIX))
async def cb_set_admin_role(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if callback.from_user is None or not is_owner(callback.from_user.id, settings):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ROLE_SET_PREFIX)
    parts = raw.split(":", 1)
    if len(parts) != 2:
        await callback.answer()
        return
    try:
        target_id = int(parts[0])
    except ValueError:
        await callback.answer()
        return
    role = parts[1]
    if is_owner(target_id, settings):
        await callback.answer("نقش مالک ثابت است.", show_alert=True)
        return
    try:
        db.set_admin_role(target_id, role)
    except ValueError:
        await callback.answer(texts.ADMIN_ROLE_USAGE, show_alert=True)
        return

    if isinstance(callback.message, Message):
        await send_roles_menu(callback.message, settings, db, edit_in_place=True)
    await callback.answer(
        texts.ADMIN_ROLE_SET_OK.format(
            user_id=target_id,
            role_label=texts.ADMIN_ROLE_LABELS.get(role, role),
        )
    )
