from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import admin_panel_access
from app.handlers.admin_panel import send_admin_home
from app.handlers.buyer_ui import buyer_reply_keyboard, buyer_show_test_button


router = Router(name="start")


def _main_kb(
    message: Message,
    settings: Settings,
    db: Database,
    *,
    user_id: int | None = None,
):
    uid = user_id
    if uid is None:
        user = message.from_user
        if user is None or user.is_bot:
            return keyboards.main_reply_keyboard(show_test=False)
        uid = user.id
    if admin_panel_access(uid, settings, db):
        return keyboards.admin_reply_keyboard(uid, settings, db)
    return buyer_reply_keyboard(message, db, user_id=uid)


async def _show_menu(message: Message, settings: Settings, db: Database) -> None:
    """Welcome text + bottom reply keyboard (main navigation)."""
    await message.answer(texts.WELCOME, reply_markup=_main_kb(message, settings, db))


def _account_text(
    message: Message, db: Database, *, user_id: int | None = None
) -> str | None:
    uid = user_id
    user = message.from_user
    if uid is None:
        if user is None or user.is_bot:
            return None
        uid = user.id
    row = db.get_user(uid)
    if row:
        full_name = " ".join(
            p for p in [row["first_name"], row["last_name"]] if p
        ) or "—"
        username = f"@{row['username']}" if row["username"] else "—"
    elif user is not None and not user.is_bot:
        full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
        username = f"@{user.username}" if user.username else "—"
    else:
        full_name = "—"
        username = "—"
    created_at = row["created_at"] if row else "—"
    return texts.ACCOUNT_INFO.format(
        user_id=uid,
        username=username,
        full_name=full_name,
        created_at=created_at,
    )


@router.message(CommandStart())
async def cmd_start(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    if message.from_user and admin_panel_access(message.from_user.id, settings, db):
        await send_admin_home(message, settings, db)
    else:
        await _show_menu(message, settings, db)


@router.message(Command("help"))
async def cmd_help(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    await message.answer(texts.HELP, reply_markup=_main_kb(message, settings, db))


@router.message(Command("cancel"), StateFilter(None))
async def cmd_cancel(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=_main_kb(message, settings, db))


# ---------- reply-keyboard menu (bottom buttons) ----------
@router.message(F.text == texts.BTN_HELP, StateFilter(None))
async def msg_help(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    await message.answer(texts.HELP, reply_markup=_main_kb(message, settings, db))


@router.message(F.text == texts.BTN_ABOUT, StateFilter(None))
async def msg_about(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    await message.answer(texts.ABOUT, reply_markup=_main_kb(message, settings, db))


@router.message(F.text == texts.BTN_MY_ACCOUNT, StateFilter(None))
async def msg_account(
    message: Message, db: Database, state: FSMContext, settings: Settings
) -> None:
    await state.clear()
    text = _account_text(message, db)
    if text:
        await message.answer(text, reply_markup=_main_kb(message, settings, db))


# ---------- inline callbacks (still used inside wizards) ----------
@router.callback_query(F.data == keyboards.CB_MAIN_HOME)
async def cb_home(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    await state.clear()
    if callback.message is not None:
        if (
            callback.from_user
            and admin_panel_access(callback.from_user.id, settings, db)
        ):
            await send_admin_home(
                callback.message,
                settings,
                db,
                admin_user_id=callback.from_user.id,
                edit_in_place=True,
            )
        else:
            show_test = (
                callback.from_user is not None
                and buyer_show_test_button(db, callback.from_user.id)
            )
            await callback.message.answer(
                texts.WELCOME,
                reply_markup=keyboards.main_reply_keyboard(show_test=show_test),
            )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_HELP)
async def cb_help(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if isinstance(callback.message, Message) and callback.from_user is not None:
        uid = callback.from_user.id
        await callback.message.answer(
            texts.HELP,
            reply_markup=_main_kb(callback.message, settings, db, user_id=uid),
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_ABOUT)
async def cb_about(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if isinstance(callback.message, Message) and callback.from_user is not None:
        uid = callback.from_user.id
        await callback.message.answer(
            texts.ABOUT,
            reply_markup=_main_kb(callback.message, settings, db, user_id=uid),
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_MAIN_ACCOUNT)
async def cb_account(
    callback: CallbackQuery, db: Database, state: FSMContext, settings: Settings
) -> None:
    if not isinstance(callback.message, Message) or callback.from_user is None:
        await callback.answer()
        return
    uid = callback.from_user.id
    text = _account_text(callback.message, db, user_id=uid)
    if text:
        await callback.message.answer(
            text,
            reply_markup=_main_kb(callback.message, settings, db, user_id=uid),
        )
    await callback.answer()
