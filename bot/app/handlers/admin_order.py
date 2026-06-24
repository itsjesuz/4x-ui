"""Admin: /order, /editorder — view and manage provisioned orders."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import ORDERS_MANAGE
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_order_ui import format_admin_order_detail
from app.handlers.admin_ui_helpers import admin_edit_or_answer
from app.logs import Actor, make_logger
from app.xui import DAY_IN_SECONDS, GIB_IN_BYTES, XuiClient, XuiError, _gb_to_bytes

router = Router(name="admin_order")
log = logging.getLogger(__name__)

_GB_MAX = 10_240
_DAYS_MAX = 3_650


class AdminOrderEditFlow(StatesGroup):
    waiting_custom_gb = State()
    waiting_custom_days = State()


async def send_admin_order_view(
    message: Message,
    db: Database,
    order_id: int,
    *,
    edit_in_place: bool = False,
    manage_header: bool = False,
    back_data: str | None = keyboards.CB_ADM_PENDING_LIST,
) -> bool:
    """Show order detail + management keyboard; return False if not found."""
    text = format_admin_order_detail(db, order_id)
    if text is None:
        return False

    order = db.get_order(order_id)
    assert order is not None
    panel_live = await _panel_live_snippet(db, order)
    if panel_live:
        text = f"{text}\n\n{panel_live}"
    panel = await _panel_for_order(db, order)
    if manage_header:
        text = texts.ADMIN_EDIT_ORDER_HEADER.format(detail=text)
    markup = keyboards.admin_edit_order_keyboard(
        order_id,
        show_panel_actions=panel is not None,
        show_db_delete=True,
        back_data=back_data,
    )
    await admin_edit_or_answer(
        message, text, markup, edit_in_place=edit_in_place
    )
    return True


async def _panel_for_order(db: Database, order) -> tuple | None:
    """Return (location, email) or None if panel ops impossible."""
    if str(order["status"]) != "provisioned" or not order["xui_email"]:
        return None
    loc = db.get_location(int(order["location_id"]))
    if loc is None:
        return None
    return loc, str(order["xui_email"])


def _format_expiry_ms(ms: int) -> str:
    if ms <= 0:
        return texts.VIEW_USAGE_NEVER_EXPIRES
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M UTC")


async def _panel_live_snippet(db: Database, order) -> str | None:
    panel = await _panel_for_order(db, order)
    if panel is None:
        return None
    loc, email = panel
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            usage = await xui.get_usage(email)
    except XuiError:
        return "<i>وضعیت پنل: خطا در خواندن</i>"

    expiry = _format_expiry_ms(usage.expiry_time_ms)
    used = texts.format_bytes(usage.used_bytes)
    if usage.is_unlimited_traffic:
        return texts.ADMIN_EDIT_ORDER_PANEL_LIVE_UNLIMITED.format(
            used=used, expiry=escape(expiry)
        )
    total = texts.format_bytes(usage.total_bytes)
    return texts.ADMIN_EDIT_ORDER_PANEL_LIVE.format(
        used=used, total=total, expiry=escape(expiry)
    )


def _parse_positive_int(raw: str, *, max_value: int) -> int | None:
    s = (raw or "").strip()
    if not s.isdigit():
        return None
    value = int(s)
    if value < 1 or value > max_value:
        return None
    return value


def _parse_order_id_with_int(data: str | None, prefix: str) -> tuple[int | None, int | None]:
    """Parse ``prefix<order_id>:<value>``."""
    rest = (data or "").removeprefix(prefix)
    if ":" not in rest:
        return None, None
    oid_s, val_s = rest.split(":", 1)
    try:
        return int(oid_s), int(val_s)
    except ValueError:
        return None, None


async def _apply_add_gb(
    db: Database, order_id: int, order, loc, email: str, add_gb: int
) -> int:
    async with XuiClient(loc.base_url, loc.api_token) as xui:
        usage = await xui.get_usage(email)
        base_bytes = (
            usage.total_bytes
            if usage.total_bytes > 0
            else _gb_to_bytes(int(order["volume_gb"]))
        )
        new_total = base_bytes + _gb_to_bytes(add_gb)
        await xui.update_client(email=email, total_bytes=new_total)
    new_gb = max(int(order["volume_gb"]), (new_total + GIB_IN_BYTES - 1) // GIB_IN_BYTES)
    db.update_order_plan(order_id, volume_gb=new_gb)
    return new_gb


async def _apply_set_gb(
    db: Database, order_id: int, loc, email: str, total_gb: int
) -> None:
    async with XuiClient(loc.base_url, loc.api_token) as xui:
        await xui.update_client(email=email, volume_gb=total_gb)
    db.update_order_plan(order_id, volume_gb=total_gb)


async def _apply_add_days(
    db: Database, order_id: int, order, loc, email: str, add_days: int
) -> int:
    now_ms = int(time.time() * 1000)
    async with XuiClient(loc.base_url, loc.api_token) as xui:
        usage = await xui.get_usage(email)
        base_ms = (
            max(now_ms, usage.expiry_time_ms)
            if usage.expiry_time_ms > 0
            else now_ms
        )
        new_expiry = base_ms + add_days * DAY_IN_SECONDS * 1000
        await xui.update_client(email=email, expiry_time_ms=new_expiry)
    db.update_order_plan(
        order_id, duration_days=int(order["duration_days"]) + add_days
    )
    return new_expiry


async def _log_edit(
    bot: Bot,
    db: Database,
    *,
    order_id: int,
    from_user,
    action: str,
    order=None,
    notes: str | None = None,
) -> None:
    admin = Actor.from_user(from_user)
    if admin is None:
        return
    await make_logger(bot, db).log_admin_order_action(
        order_id=order_id,
        admin=admin,
        action=action,
        order=order,
        notes=notes,
    )


# ---------- /order ----------
@router.message(Command("order"))
async def cmd_order(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_ORDER_USAGE)
        return
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_ORDER_USAGE)
        return

    if not await send_admin_order_view(message, db, order_id):
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)


# ---------- /editorder ----------
@router.message(Command("editorder"))
async def cmd_editorder(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_EDIT_ORDER_USAGE)
        return
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_EDIT_ORDER_USAGE)
        return

    if not await send_admin_order_view(
        message, db, order_id, manage_header=True
    ):
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)


# ---------- panel enable / disable ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_ENABLE_PREFIX))
async def cb_order_enable(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_ENABLE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            await xui.update_client(email=email, enable=True)
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_ENABLED.format(order_id=order_id)
        )
    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="فعال‌سازی در پنل",
        )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DISABLE_PREFIX))
async def cb_order_disable(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DISABLE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            await xui.update_client(email=email, enable=False)
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_DISABLED.format(order_id=order_id)
        )
    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="غیرفعال در پنل",
        )


# ---------- delete (confirm) — register OK before ASK; prefixes must not nest ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DELETE_OK_PREFIX))
async def cb_order_delete_ok(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DELETE_OK_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    await callback.answer("⏳ …")

    panel_err: str | None = None
    panel = await _panel_for_order(db, order)
    if panel is not None:
        loc, email = panel
        try:
            async with XuiClient(loc.base_url, loc.api_token) as xui:
                await xui.delete_client(email, keep_traffic=1)
        except XuiError as exc:
            panel_err = str(exc)
            log.warning("Panel delete failed for order %s: %s", order_id, exc)

    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        delete_notes = (
            f"خطای حذف از پنل: {panel_err}" if panel_err else None
        )
        await make_logger(bot, db).log_admin_order_action(
            order_id=order_id,
            admin=admin,
            action="حذف از پنل و ربات",
            order=order,
            notes=delete_notes,
            fetch_panel=False,
        )

    if not db.delete_order(order_id):
        if isinstance(callback.message, Message):
            await callback.message.edit_text(
                "❗ حذف از دیتابیس ناموفق.",
                reply_markup=None,
            )
        return

    if isinstance(callback.message, Message):
        if panel_err:
            await callback.message.edit_text(
                texts.ADMIN_ORDER_DELETED_PARTIAL.format(
                    order_id=order_id, error=escape(panel_err)
                ),
                reply_markup=None,
            )
        else:
            await callback.message.edit_text(
                texts.ADMIN_ORDER_DELETED_OK.format(order_id=order_id),
                reply_markup=None,
            )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_DELETE_ASK_PREFIX))
async def cb_order_delete_ask(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_DELETE_ASK_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_ORDER_DELETE_CONFIRM.format(order_id=order_id),
            reply_markup=keyboards.admin_order_delete_confirm(order_id),
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_ORDER_DELETE_CANCEL)
async def cb_order_delete_cancel(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.ADMIN_ORDER_DELETE_CANCELLED, reply_markup=None)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_MANAGE_PREFIX))
async def cb_order_manage(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    order_id = _parse_order_id(callback.data, keyboards.CB_ADM_ORDER_MANAGE_PREFIX)
    if order_id is None:
        await callback.answer()
        return

    if not await send_admin_order_view(
        callback.message,
        db,
        order_id,
        edit_in_place=True,
        manage_header=True,
    ):
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    await callback.answer()


# ---------- panel volume / expiry ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_EDIT_PLAN_PREFIX))
async def cb_order_edit_plan_menu(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    order_id = _parse_order_id(
        callback.data, keyboards.CB_ADM_ORDER_EDIT_PLAN_PREFIX
    )
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    if await _panel_for_order(db, order) is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return

    panel_live = await _panel_live_snippet(db, order) or "—"
    text = texts.ADMIN_EDIT_ORDER_PLAN_MENU.format(
        order_id=order_id,
        panel_live=panel_live,
    )
    await admin_edit_or_answer(
        callback.message,
        text,
        keyboards.admin_order_plan_edit_keyboard(order_id),
        edit_in_place=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_ADD_GB_PREFIX))
async def cb_order_add_gb(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id, add_gb = _parse_order_id_with_int(
        callback.data, keyboards.CB_ADM_ORDER_ADD_GB_PREFIX
    )
    if order_id is None or add_gb is None or add_gb < 1 or add_gb > _GB_MAX:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        total_gb = await _apply_add_gb(db, order_id, order, loc, email, add_gb)
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_GB_ADDED.format(
                order_id=order_id, add_gb=add_gb, total_gb=total_gb
            )
        )
        await send_admin_order_view(
            callback.message,
            db,
            order_id,
            edit_in_place=True,
            manage_header=True,
        )
    await _log_edit(
        bot,
        db,
        order_id=order_id,
        from_user=callback.from_user,
        action=f"+{add_gb} GB پنل",
        notes=f"حجم کل پنل پس از تغییر: {total_gb} GB",
    )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_ADD_DAYS_PREFIX))
async def cb_order_add_days(
    callback: CallbackQuery, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return

    order_id, add_days = _parse_order_id_with_int(
        callback.data, keyboards.CB_ADM_ORDER_ADD_DAYS_PREFIX
    )
    if order_id is None or add_days is None or add_days < 1 or add_days > _DAYS_MAX:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    panel = await _panel_for_order(db, order)
    if panel is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return
    loc, email = panel

    await callback.answer("⏳ …")
    try:
        new_expiry = await _apply_add_days(
            db, order_id, order, loc, email, add_days
        )
    except XuiError as exc:
        if isinstance(callback.message, Message):
            await callback.message.answer(
                texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
            )
        return

    expiry_s = _format_expiry_ms(new_expiry)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.ADMIN_EDIT_ORDER_DAYS_ADDED.format(
                order_id=order_id,
                add_days=add_days,
                expiry=escape(expiry_s),
            )
        )
        await send_admin_order_view(
            callback.message,
            db,
            order_id,
            edit_in_place=True,
            manage_header=True,
        )
    await _log_edit(
        bot,
        db,
        order_id=order_id,
        from_user=callback.from_user,
        action=f"+{add_days} روز پنل",
        notes=f"انقضای جدید: {_format_expiry_ms(new_expiry)}",
    )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_SET_GB_ASK_PREFIX))
async def cb_order_set_gb_ask(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    order_id = _parse_order_id(
        callback.data, keyboards.CB_ADM_ORDER_SET_GB_ASK_PREFIX
    )
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    if await _panel_for_order(db, order) is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return

    await state.set_state(AdminOrderEditFlow.waiting_custom_gb)
    await state.update_data(order_id=order_id)
    await callback.message.answer(texts.ADMIN_EDIT_ORDER_PROMPT_GB)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_ADD_DAYS_ASK_PREFIX))
async def cb_order_add_days_ask(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    order_id = _parse_order_id(
        callback.data, keyboards.CB_ADM_ORDER_ADD_DAYS_ASK_PREFIX
    )
    if order_id is None:
        await callback.answer()
        return

    order = db.get_order(order_id)
    if order is None:
        await callback.answer(texts.ADMIN_ORDER_NOTFOUND, show_alert=True)
        return
    if await _panel_for_order(db, order) is None:
        await callback.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL, show_alert=True)
        return

    await state.set_state(AdminOrderEditFlow.waiting_custom_days)
    await state.update_data(order_id=order_id)
    await callback.message.answer(texts.ADMIN_EDIT_ORDER_PROMPT_DAYS)
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminOrderEditFlow))
async def cmd_order_edit_cancel(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return
    data = await state.get_data()
    order_id = data.get("order_id")
    await state.clear()
    await message.answer(texts.CANCELLED)
    if order_id is not None:
        await send_admin_order_view(
            message, db, int(order_id), manage_header=True
        )


@router.message(StateFilter(AdminOrderEditFlow.waiting_custom_gb))
async def msg_order_set_gb(
    message: Message, state: FSMContext, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    total_gb = _parse_positive_int(message.text or "", max_value=_GB_MAX)
    if total_gb is None:
        await message.answer(
            texts.ADMIN_EDIT_ORDER_INVALID_NUMBER.format(max=_GB_MAX)
        )
        return

    data = await state.get_data()
    order_id = int(data["order_id"])
    await state.clear()

    order = db.get_order(order_id)
    if order is None:
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)
        return
    panel = await _panel_for_order(db, order)
    if panel is None:
        await message.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL)
        return
    loc, email = panel

    try:
        await _apply_set_gb(db, order_id, loc, email, total_gb)
    except XuiError as exc:
        await message.answer(
            texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
        )
        return

    await message.answer(
        texts.ADMIN_EDIT_ORDER_GB_SET.format(
            order_id=order_id, total_gb=total_gb
        )
    )
    await send_admin_order_view(
        message,
        db,
        order_id,
        manage_header=True,
    )
    await _log_edit(
        bot,
        db,
        order_id=order_id,
        from_user=message.from_user,
        action=f"تنظیم حجم {total_gb} GB",
        notes=f"حجم کل پنل: {total_gb} GB",
    )


@router.message(StateFilter(AdminOrderEditFlow.waiting_custom_days))
async def msg_order_add_days_custom(
    message: Message, state: FSMContext, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    add_days = _parse_positive_int(message.text or "", max_value=_DAYS_MAX)
    if add_days is None:
        await message.answer(
            texts.ADMIN_EDIT_ORDER_INVALID_NUMBER.format(max=_DAYS_MAX)
        )
        return

    data = await state.get_data()
    order_id = int(data["order_id"])
    await state.clear()

    order = db.get_order(order_id)
    if order is None:
        await message.answer(texts.ADMIN_ORDER_NOTFOUND)
        return
    panel = await _panel_for_order(db, order)
    if panel is None:
        await message.answer(texts.ADMIN_EDIT_ORDER_NO_PANEL)
        return
    loc, email = panel

    try:
        new_expiry = await _apply_add_days(
            db, order_id, order, loc, email, add_days
        )
    except XuiError as exc:
        await message.answer(
            texts.ADMIN_EDIT_ORDER_FAIL.format(error=escape(str(exc)))
        )
        return

    await message.answer(
        texts.ADMIN_EDIT_ORDER_DAYS_ADDED.format(
            order_id=order_id,
            add_days=add_days,
            expiry=escape(_format_expiry_ms(new_expiry)),
        )
    )
    await send_admin_order_view(
        message,
        db,
        order_id,
        manage_header=True,
    )
    await _log_edit(
        bot,
        db,
        order_id=order_id,
        from_user=message.from_user,
        action=f"+{add_days} روز (دستی)",
        notes=f"انقضای جدید: {_format_expiry_ms(new_expiry)}",
    )


def _parse_order_id(data: str | None, prefix: str) -> int | None:
    try:
        return int((data or "").removeprefix(prefix))
    except ValueError:
        return None
