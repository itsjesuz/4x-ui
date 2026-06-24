"""Admin panel: مشتریان (buyers with orders), search, detail."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.handlers.admin_customers_ui import (
    format_customer_detail,
    format_customers_page,
    format_customers_search_results,
)
from app.admin_perms import CUSTOMERS, USERS
from app.handlers.admin_helpers import (
    admin_can,
    guard_admin_callback,
    guard_admin_message,
    is_admin,
)
from app.handlers.admin_ui_helpers import admin_edit_or_answer

router = Router(name="admin_customers")


class AdminCustomersFlow(StatesGroup):
    waiting_search = State()


async def send_customers(
    message: Message,
    settings: Settings,
    db: Database,
    actor_id: int,
    page: int = 0,
    *,
    edit_in_place: bool = False,
) -> None:
    text, total_pages, customers = await format_customers_page(db, page)
    markup = keyboards.admin_customers_keyboard(
        customers, page=page, total_pages=total_pages
    )
    await admin_edit_or_answer(
        message,
        text,
        markup,
        edit_in_place=edit_in_place,
    )


async def send_customer_detail(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    actor_id: int,
    edit_in_place: bool = False,
) -> bool:
    text = await format_customer_detail(db, user_id)
    if text is None:
        return False
    row = db.get_user(user_id)
    if row is None:
        return False
    orders = db.list_user_orders_admin(user_id, limit=30, exclude_test=True)
    order_ids = [int(o["id"]) for o in orders][:8]
    markup = keyboards.admin_customer_detail_keyboard(
        user_id,
        actor_id,
        settings,
        db,
        is_banned=bool(row["is_banned"]),
        order_ids=order_ids,
    )
    await admin_edit_or_answer(
        message,
        text,
        markup,
        edit_in_place=edit_in_place,
    )
    return True


@router.message(F.text == texts.ADMIN_BTN_CUSTOMERS, StateFilter(None))
async def msg_admin_customers(
    message: Message, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, CUSTOMERS):
        return
    await send_customers(message, settings, db, message.from_user.id)


@router.callback_query(F.data == keyboards.CB_ADM_CUSTOMERS)
async def cb_admin_customers(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, CUSTOMERS):
        return
    await state.clear()
    if isinstance(callback.message, Message) and callback.from_user is not None:
        await send_customers(
            callback.message,
            settings,
            db,
            callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_CUSTOMERS_PAGE_PREFIX))
async def cb_admin_customers_page(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, CUSTOMERS):
        return
    raw = (callback.data or "").removeprefix(
        keyboards.CB_ADM_CUSTOMERS_PAGE_PREFIX
    )
    try:
        page = int(raw)
    except ValueError:
        await callback.answer()
        return
    if isinstance(callback.message, Message) and callback.from_user is not None:
        await send_customers(
            callback.message,
            settings,
            db,
            callback.from_user.id,
            page=page,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_CUSTOMERS_SEARCH)
async def cb_admin_customers_search_start(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, CUSTOMERS):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.set_state(AdminCustomersFlow.waiting_search)
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_CUSTOMERS_SEARCH_PROMPT,
        keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_CUSTOMERS),
        edit_in_place=True,
    )
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminCustomersFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminCustomersFlow)
)
async def customers_flow_cancel(
    event: Message | CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    user_id = event.from_user.id if event.from_user else None
    if user_id is None or not admin_can(user_id, CUSTOMERS, settings, db):
        msg = (
            texts.NOT_ADMIN
            if user_id is None or not is_admin(user_id, settings)
            else texts.NOT_PERMITTED
        )
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return
    await state.clear()
    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            await send_customers(
                event.message, settings, db, user_id, edit_in_place=True
            )
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(AdminCustomersFlow.waiting_search))
async def customers_search_input(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, CUSTOMERS):
        await state.clear()
        return

    query = (message.text or "").strip()
    if not query:
        await message.answer(texts.ADMIN_CUSTOMERS_SEARCH_EMPTY.format(query="—"))
        return

    await state.clear()
    text, rows = await format_customers_search_results(db, query)
    markup = keyboards.admin_customers_search_keyboard(rows)
    await message.answer(text, reply_markup=markup)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_CUST_DETAIL_PREFIX))
async def cb_admin_customer_detail(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, CUSTOMERS):
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_CUST_DETAIL_PREFIX)
    try:
        user_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await send_customer_detail(
        callback.message,
        settings,
        db,
        user_id,
        actor_id=callback.from_user.id,
        edit_in_place=True,
    ):
        await callback.answer("مشتری یافت نشد.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_CUST_BAN_PREFIX))
async def cb_admin_cust_ban(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, USERS):
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_CUST_BAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if callback.from_user and user_id == callback.from_user.id:
        await callback.answer(texts.BAN_SELF, show_alert=True)
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, True)
    if isinstance(callback.message, Message):
        await send_customer_detail(
            callback.message,
            settings,
            db,
            user_id,
            actor_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer(texts.BAN_OK.format(user_id=user_id))
    await _log_ban(bot, db, callback, user_id, banned=True)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_CUST_UNBAN_PREFIX))
async def cb_admin_cust_unban(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, USERS):
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_CUST_UNBAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, False)
    if isinstance(callback.message, Message):
        await send_customer_detail(
            callback.message,
            settings,
            db,
            user_id,
            actor_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer(texts.UNBAN_OK.format(user_id=user_id))
    await _log_ban(bot, db, callback, user_id, banned=False)


async def _log_ban(
    bot: Bot, db: Database, callback: CallbackQuery, user_id: int, *, banned: bool
) -> None:
    from app.logs import Actor, make_logger

    admin = Actor.from_user(callback.from_user)
    row = db.get_user(user_id)
    if admin is None or row is None:
        return
    target = Actor(
        user_id=user_id,
        full_name=" ".join(
            p for p in [row["first_name"], row["last_name"]] if p
        )
        or "—",
        username=row["username"],
    )
    await make_logger(bot, db).log_user_ban(
        admin=admin, user=target, banned=banned
    )
