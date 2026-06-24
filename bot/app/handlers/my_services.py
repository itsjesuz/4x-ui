"""User-facing "سرویس‌های من" (My Services) flow.

Lets a buyer:
  * see all their orders (active, pending, disabled, etc.) with status badges
  * view the connection info (sub link + per-inbound configs)
  * live usage on the service detail page (refresh button)
  * disable / re-enable a service
  * rename a service (panel client id + optional display label)
  * regenerate configs (disable old client, new id with remaining traffic)
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from html import escape

from aiogram import F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.buyer_orders import filter_visible_orders, is_visible_to_buyer
from app.db import Database
from app.xui import ClientUsage, XuiClient, XuiError, email_from_user_label


router = Router(name="my_services")
log = logging.getLogger(__name__)

MAX_NICKNAME_LEN = 30


class RenameFlow(StatesGroup):
    waiting_for_nickname = State()


# ---------- helpers ----------
def _is_not_modified_error(exc: TelegramBadRequest) -> bool:
    msg = (exc.message or str(exc)).lower()
    return "message is not modified" in msg or "exactly the same" in msg


async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    """Edit the callback's message in place; only send a new one if edit is impossible."""
    if not isinstance(callback.message, Message):
        return
    try:
        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )
        return
    except TelegramBadRequest as exc:
        if _is_not_modified_error(exc):
            # Same text/markup — still a successful refresh, do not duplicate the message.
            if reply_markup is not None:
                try:
                    await callback.message.edit_reply_markup(reply_markup=reply_markup)
                except TelegramBadRequest as exc2:
                    if not _is_not_modified_error(exc2):
                        log.debug("edit_reply_markup failed", exc_info=True)
            return
    except Exception:  # noqa: BLE001 — e.g. photo message, message too old
        log.debug("edit_text failed, falling back to answer", exc_info=True)
    await callback.message.answer(
        text, reply_markup=reply_markup, parse_mode=ParseMode.HTML
    )


def _status_badge(status: str) -> str:
    return texts.STATUS_BADGE.get(status, status)


def _format_expiry(ms: int) -> tuple[str, str]:
    """Return (absolute, time_left) strings."""
    if ms <= 0:
        return (texts.VIEW_USAGE_NEVER_EXPIRES, "—")
    dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    absolute = dt.strftime("%Y-%m-%d %H:%M UTC")
    remaining_seconds = int(ms / 1000 - time.time())
    if remaining_seconds <= 0:
        return (absolute, texts.VIEW_USAGE_EXPIRED)
    days, rem = divmod(remaining_seconds, 86400)
    hours = rem // 3600
    if days > 0:
        time_left = f"{days} روز و {hours} ساعت"
    else:
        minutes = (remaining_seconds % 3600) // 60
        time_left = f"{hours} ساعت و {minutes} دقیقه"
    return (absolute, time_left)


def _is_test_order(row) -> bool:
    return bool(row["is_test"]) if "is_test" in row.keys() else False


def _order_volume_label(row) -> str:
    is_test = _is_test_order(row)
    if is_test:
        return texts.format_test_volume()
    return f"{int(row['volume_gb'])}GB"


def _service_list_label(row) -> str:
    badge = _status_badge(str(row["status"]))
    nick = f" — «{row['nickname']}»" if (row["nickname"] or "") else ""
    vol = _order_volume_label(row)
    test_mark = " 🧪" if ("is_test" in row.keys() and row["is_test"]) else ""
    dur = (
        texts.format_test_duration()
        if _is_test_order(row)
        else f"{row['duration_days']}d"
    )
    return f"{badge} #{row['id']}{test_mark} · {row['location_name']} · {vol}/{dur}{nick}"


def _format_usage_block(usage: ClientUsage) -> str:
    total_str = (
        texts.VIEW_USAGE_UNLIMITED_TRAFFIC
        if usage.is_unlimited_traffic
        else texts.format_bytes(usage.total_bytes)
    )
    remaining_str = (
        texts.VIEW_USAGE_UNLIMITED_TRAFFIC
        if usage.is_unlimited_traffic
        else texts.format_bytes(usage.remaining_bytes)
    )
    absolute, time_left = _format_expiry(usage.expiry_time_ms)
    enabled_str = (
        texts.VIEW_USAGE_ENABLED if usage.enable else texts.VIEW_USAGE_DISABLED
    )
    return texts.SERVICE_DETAIL_USAGE_BLOCK.format(
        enabled=enabled_str,
        used=texts.format_bytes(usage.used_bytes),
        total=total_str,
        remaining=remaining_str,
        expiry=absolute,
        time_left=time_left,
    )


def _build_detail_text(
    row,
    *,
    usage: ClientUsage | None = None,
    usage_error: str | None = None,
) -> str:
    nickname_part = f" — «{escape(row['nickname'])}»" if (row["nickname"] or "") else ""
    panel_id_line = ""
    if row["xui_email"]:
        panel_id_line = f"🆔 شناسه پنل: <code>{escape(str(row['xui_email']))}</code>\n"

    usage_block = ""
    if str(row["status"]) == "provisioned":
        if usage_error:
            usage_block = texts.SERVICE_DETAIL_USAGE_ERROR.format(
                error=escape(usage_error)
            )
        elif usage is not None:
            usage_block = _format_usage_block(usage)

    detail = texts.SERVICE_DETAIL.format(
        order_id=row["id"],
        nickname_part=nickname_part,
        location=escape(str(row["location_name"])),
        volume=texts.format_order_volume(
            int(row["volume_gb"]),
            is_test=_is_test_order(row),
        ),
        duration=texts.format_order_duration(
            int(row["duration_days"]), is_test=_is_test_order(row)
        ),
        price=texts.format_price(int(row["price"])),
        status=_status_badge(str(row["status"])),
        panel_id_line=panel_id_line,
        usage_block=usage_block,
        created_at=str(row["created_at"]),
    )
    if _is_test_order(row) and str(row["status"]) == "provisioned":
        detail += texts.TEST_SERVICE_LIMITED
    return detail


async def _fetch_panel_usage(row, location) -> tuple[ClientUsage | None, str | None]:
    if not row["xui_email"]:
        return None, "اطلاعات پنل موجود نیست"
    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            return await xui.get_usage(str(row["xui_email"])), None
    except XuiError as exc:
        return None, str(exc)
    except Exception as exc:  # noqa: BLE001
        log.exception("Usage fetch failed for order %s", row["id"])
        return None, str(exc)


async def _show_service_detail(
    callback: CallbackQuery,
    db: Database,
    order_id: int,
    user_id: int,
    *,
    refresh: bool = False,
) -> None:
    row = await _own_order_or_none(db, order_id, user_id)
    if row is None:
        await callback.answer("سرویس یافت نشد.", show_alert=True)
        return

    provisioned = str(row["status"]) == "provisioned"
    usage: ClientUsage | None = None
    usage_error: str | None = None
    enabled = True

    if provisioned:
        location = db.get_location(int(row["location_id"]))
        if location is None:
            usage_error = "لوکیشن یافت نشد"
        else:
            usage, usage_error = await _fetch_panel_usage(row, location)
            if usage is not None:
                enabled = usage.enable

    is_test = _is_test_order(row)
    text = _build_detail_text(row, usage=usage, usage_error=usage_error)
    if not provisioned:
        text += texts.SERVICE_NOT_PROVISIONED_ACTIONS

    await _edit_or_answer(
        callback,
        text,
        keyboards.my_service_detail(
            order_id,
            provisioned=provisioned,
            enabled=enabled,
            is_test=is_test,
        ),
    )
    if refresh:
        if usage_error:
            await callback.answer("⚠️ بروزرسانی ناموفق", show_alert=True)
        else:
            await callback.answer("✅ بروزرسانی شد")
    else:
        await callback.answer()


async def _own_order_or_none(db: Database, order_id: int, user_id: int):
    row = db.get_order(order_id)
    if row is None or int(row["user_id"]) != user_id:
        return None
    if not await is_visible_to_buyer(db, row):
        return None
    return row


async def _show_services_list(
    message: Message,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> None:
    rows = await filter_visible_orders(db, db.list_user_orders(user_id, limit=50))
    if not rows:
        text = texts.MY_SERVICES_EMPTY
        if edit_in_place:
            try:
                await message.edit_text(text, parse_mode=ParseMode.HTML)
            except TelegramBadRequest as exc:
                if not _is_not_modified_error(exc):
                    await message.answer(
                        text,
                        reply_markup=keyboards.main_reply_keyboard(),
                        parse_mode=ParseMode.HTML,
                    )
            except Exception:  # noqa: BLE001
                await message.answer(
                    text,
                    reply_markup=keyboards.main_reply_keyboard(),
                    parse_mode=ParseMode.HTML,
                )
        else:
            await message.answer(
                text,
                reply_markup=keyboards.main_reply_keyboard(),
                parse_mode=ParseMode.HTML,
            )
        return

    items = [{"id": int(r["id"]), "label": _service_list_label(r)} for r in rows]
    text = texts.MY_SERVICES_HEADER
    markup = keyboards.my_services_list(items)
    if edit_in_place:
        try:
            await message.edit_text(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        except TelegramBadRequest as exc:
            if _is_not_modified_error(exc):
                return
            await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
        except Exception:  # noqa: BLE001
            await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    else:
        from app.ui_reply import answer_with_inline_keyboard

        await answer_with_inline_keyboard(
            message, text, markup, parse_mode=ParseMode.HTML
        )


# ---------- entry: list ----------
@router.message(F.text == texts.BTN_MY_SERVICES, StateFilter(None))
async def msg_my_services(message: Message, db: Database) -> None:
    if message.from_user is None:
        return
    await _show_services_list(message, db, message.from_user.id)


@router.callback_query(F.data == keyboards.CB_MAIN_MY_SERVICES)
@router.callback_query(F.data == keyboards.CB_MY_LIST)
async def cb_my_services(callback: CallbackQuery, db: Database) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await _show_services_list(
        callback.message,
        db,
        callback.from_user.id,
        edit_in_place=True,
    )
    await callback.answer()


# ---------- detail ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_DETAIL_PREFIX))
async def cb_my_service_detail(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_DETAIL_PREFIX))
    except ValueError:
        await callback.answer()
        return
    await _show_service_detail(callback, db, order_id, user.id, refresh=False)


# ---------- view configs ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_CONFIGS_PREFIX))
async def cb_view_configs(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_CONFIGS_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    sub_links: list[str] = []
    try:
        sub_links = json.loads(row["sub_links"] or "[]")
    except (TypeError, ValueError):
        sub_links = []

    sub_url = location.render_sub_url(row["xui_sub_id"]) if location else None
    
    # Check if this location has config buttons configured
    config_buttons = location.config_buttons if location else []
    
    if config_buttons:
        text = "🎛 لطفاً موقعیت جغرافیایی کانفیگ مورد نظر خود را انتخاب کنید:"
        if sub_url:
            text += f"\n\n🔗 <b>لینک سابسکریپشن شما:</b>\n<code>{escape(sub_url)}</code>"
        await _edit_or_answer(
            callback,
            text,
            keyboards.view_configs_keyboard(order_id, config_buttons),
        )
    else:
        configs_block = texts.format_configs_block(
            sub_url=sub_url, sub_links=[escape(x) for x in sub_links]
        )
        await _edit_or_answer(
            callback,
            texts.VIEW_CONFIGS_TITLE.format(order_id=order_id, configs_block=configs_block),
            keyboards.back_to_service(order_id),
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_MY_CONFIGS_FILTER_PREFIX))
async def cb_view_configs_filtered(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
        
    try:
        raw = (callback.data or "").removeprefix(keyboards.CB_MY_CONFIGS_FILTER_PREFIX)
        order_id_str, btn_index_str = raw.split(":")
        order_id = int(order_id_str)
        btn_index = int(btn_index_str)
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if not location or btn_index < 0 or btn_index >= len(location.config_buttons):
        await callback.answer("تنظیمات دکمه یافت نشد.", show_alert=True)
        return
        
    btn = location.config_buttons[btn_index]
    btn_name = btn.get("name", "دریافت کانفیگ")
    keywords = [k.strip().lower() for k in btn.get("keywords", "").split(",") if k.strip()]
    
    sub_links: list[str] = []
    try:
        sub_links = json.loads(row["sub_links"] or "[]")
    except (TypeError, ValueError):
        sub_links = []
        
    # Filter the sub_links based on keywords
    import urllib.parse
    filtered_links = []
    for link in sub_links:
        link_lower = urllib.parse.unquote(link).lower()
        if not keywords or any(kw in link_lower for kw in keywords):
            filtered_links.append(link)
            
    sub_url = location.render_sub_url(row["xui_sub_id"]) if location else None
    
    # Render
    if not filtered_links and keywords:
        configs_block = "هیچ کانفیگی مطابق با این موقعیت یافت نشد."
    else:
        configs_block = texts.format_configs_block(
            sub_url=sub_url, sub_links=[escape(x) for x in filtered_links]
        )
        
    title = f"<b>{escape(btn_name)}</b>\n\n{texts.VIEW_CONFIGS_TITLE.format(order_id=order_id, configs_block=configs_block)}"
    
    # We add a back button to go back to the buttons menu
    markup = keyboards.InlineKeyboardMarkup(inline_keyboard=[
        [keyboards.InlineKeyboardButton(text="🔙 بازگشت به منوی کانفیگ‌ها", callback_data=f"{keyboards.CB_MY_CONFIGS_PREFIX}{order_id}")],
        [keyboards.InlineKeyboardButton(text="🔙 جزئیات سرویس", callback_data=f"{keyboards.CB_MY_DETAIL_PREFIX}{order_id}")],
    ])
    
    await _edit_or_answer(callback, title, markup)
    await callback.answer()


# ---------- refresh usage on detail page ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_REFRESH_USAGE_PREFIX))
async def cb_refresh_usage(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int(
            (callback.data or "").removeprefix(keyboards.CB_MY_REFRESH_USAGE_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return

    await _show_service_detail(callback, db, order_id, user.id, refresh=True)


# ---------- toggle (disable/enable) ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_TOGGLE_PREFIX))
async def cb_toggle(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_TOGGLE_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return
    if _is_test_order(row):
        await callback.answer(texts.TEST_SERVICE_ACTION_BLOCKED, show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if location is None or not row["xui_email"]:
        await callback.answer("اطلاعات کافی نیست.", show_alert=True)
        return

    # We don't store live enable state; fetch first to flip it.
    await callback.answer("⏳ در حال اعمال تغییر...")
    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            usage = await xui.get_usage(str(row["xui_email"]))
            new_state = not usage.enable
            await xui.update_client(email=str(row["xui_email"]), enable=new_state)
    except XuiError as exc:
        await _edit_or_answer(
            callback,
            texts.TOGGLE_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected error toggling order %s", order_id)
        await _edit_or_answer(
            callback,
            texts.TOGGLE_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return

    msg = (
        texts.TOGGLE_OK_ENABLED.format(order_id=order_id)
        if new_state
        else texts.TOGGLE_OK_DISABLED.format(order_id=order_id)
    )
    await _edit_or_answer(callback, msg, keyboards.back_to_service(order_id))


# ---------- rename ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_RENAME_PREFIX))
async def cb_rename(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_RENAME_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None:
        await callback.answer("سرویس یافت نشد.", show_alert=True)
        return
    if _is_test_order(row):
        await callback.answer(texts.TEST_SERVICE_ACTION_BLOCKED, show_alert=True)
        return

    await state.set_state(RenameFlow.waiting_for_nickname)
    await state.update_data(rename_order_id=order_id)
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.RENAME_PROMPT.format(order_id=order_id))
    await callback.answer()


@router.message(StateFilter(RenameFlow.waiting_for_nickname), Command("cancel"))
async def cmd_cancel_rename(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=keyboards.main_reply_keyboard())


@router.message(StateFilter(RenameFlow.waiting_for_nickname))
async def on_nickname_received(
    message: Message, state: FSMContext, db: Database
) -> None:
    if message.from_user is None:
        await state.clear()
        return

    data = await state.get_data()
    order_id = int(data.get("rename_order_id", 0))
    if not order_id:
        await state.clear()
        return

    row = await _own_order_or_none(db, order_id, message.from_user.id)
    if row is None:
        await state.clear()
        await message.answer("سرویس یافت نشد.")
        return
    if _is_test_order(row):
        await state.clear()
        await message.answer(texts.TEST_SERVICE_ACTION_BLOCKED)
        return

    nick = (message.text or "").strip()
    if nick == "-":
        db.set_order_nickname(order_id, None)
        await state.clear()
        await message.answer(
            texts.RENAME_CLEARED, reply_markup=keyboards.back_to_service(order_id)
        )
        return

    if len(nick) > MAX_NICKNAME_LEN:
        await message.answer(texts.RENAME_TOO_LONG)
        return

    is_test = bool(row["is_test"]) if "is_test" in row.keys() else False
    new_panel_id: str | None = None
    if row["status"] == "provisioned" and row["xui_email"]:
        new_panel_id = email_from_user_label(nick, order_id, is_test=is_test)
        if new_panel_id is None:
            await message.answer(texts.RENAME_INVALID_LABEL)
            return

        old_email = str(row["xui_email"])
        location = db.get_location(int(row["location_id"]))
        if location is None:
            await message.answer(texts.RENAME_PANEL_FAILED.format(error="لوکیشن یافت نشد"))
            return

        try:
            async with XuiClient(location.base_url, location.api_token) as xui:
                if new_panel_id != old_email:
                    await xui.rename_client_email(old_email, new_panel_id)
                    sub_id, client_uuid = await xui.resolve_client_identity(new_panel_id)
                    links = await xui.get_sub_links(sub_id) if sub_id else []
                    db.update_order_xui(
                        order_id=order_id,
                        email=new_panel_id,
                        sub_id=sub_id,
                        client_uuid=client_uuid or row["xui_client_uuid"],
                        sub_links=links or json.loads(row["sub_links"] or "[]"),
                    )
        except XuiError as exc:
            await message.answer(
                texts.RENAME_PANEL_FAILED.format(error=escape(str(exc)))
            )
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("Rename panel email failed for order %s", order_id)
            await message.answer(
                texts.RENAME_PANEL_FAILED.format(error=escape(str(exc)))
            )
            return

    db.set_order_nickname(order_id, nick or None)
    await state.clear()
    if new_panel_id:
        await message.answer(
            texts.RENAME_OK_PANEL.format(
                label=escape(nick), panel_id=escape(new_panel_id)
            ),
            reply_markup=keyboards.main_reply_keyboard(),
        )
    else:
        await message.answer(
            texts.RENAME_OK, reply_markup=keyboards.main_reply_keyboard()
        )


# ---------- regenerate (destructive) ----------
@router.callback_query(F.data.startswith(keyboards.CB_MY_REGEN_PREFIX)
                       & ~F.data.startswith(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
async def cb_regen_ask(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_REGEN_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return
    if _is_test_order(row):
        await callback.answer(texts.TEST_SERVICE_ACTION_BLOCKED, show_alert=True)
        return
    if not row["xui_email"]:
        await callback.answer(texts.REGEN_NOT_SUPPORTED, show_alert=True)
        return

    await _edit_or_answer(callback, texts.REGEN_CONFIRM, keyboards.regen_confirm(order_id))
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
async def cb_regen_confirm(callback: CallbackQuery, db: Database) -> None:
    user = callback.from_user
    if user is None:
        await callback.answer()
        return
    try:
        order_id = int((callback.data or "").removeprefix(keyboards.CB_MY_REGEN_CONFIRM_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = await _own_order_or_none(db, order_id, user.id)
    if row is None or row["status"] != "provisioned":
        await callback.answer("این سرویس فعال نیست.", show_alert=True)
        return
    if _is_test_order(row):
        await callback.answer(texts.TEST_SERVICE_ACTION_BLOCKED, show_alert=True)
        return

    location = db.get_location(int(row["location_id"]))
    if location is None or not row["xui_email"]:
        await callback.answer(texts.REGEN_NOT_SUPPORTED, show_alert=True)
        return

    await _edit_or_answer(callback, texts.REGEN_IN_PROGRESS)
    await callback.answer()

    old_email = str(row["xui_email"])
    user_id = int(row["user_id"])
    is_test = bool(row["is_test"]) if "is_test" in row.keys() else False

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            result = await xui.regenerate_client(
                old_email=old_email,
                order_id=order_id,
                inbound_ids=location.inbound_ids,
                tg_user_id=user_id,
                volume_gb_fallback=int(row["volume_gb"]) or 1,
                duration_days_fallback=int(row["duration_days"]),
                is_test=is_test,
            )
    except Exception as exc:  # noqa: BLE001 — any failure → tell user, leave DB alone
        log.exception("Regen failed for order %s", order_id)
        await _edit_or_answer(
            callback,
            texts.REGEN_FAILED.format(error=escape(str(exc))),
            keyboards.back_to_service(order_id),
        )
        return

    db.update_order_xui(
        order_id=order_id,
        email=result.email,
        sub_id=result.sub_id,
        client_uuid=result.client_uuid,
        sub_links=result.sub_links,
    )
    new_sub_id = result.sub_id
    new_links = result.sub_links

    sub_url = location.render_sub_url(new_sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url, sub_links=[escape(x) for x in new_links]
    )
    await _edit_or_answer(
        callback,
        texts.REGEN_OK.format(configs_block=configs_block),
        keyboards.back_to_service(order_id),
    )

@router.callback_query(F.data.startswith(keyboards.CB_MY_RENEW_PREFIX))
async def cb_my_service_renew(
    callback: CallbackQuery, state: FSMContext, db: Database
) -> None:
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return

    try:
        order_id = int((callback.data or '').removeprefix(keyboards.CB_MY_RENEW_PREFIX))
    except ValueError:
        await callback.answer()
        return

    row = db.get_order(order_id)
    if row is None or row['user_id'] != callback.from_user.id:
        await callback.answer('سرویس یافت نشد.', show_alert=True)
        return

    if row['status'] != 'provisioned':
        await callback.answer('فقط سرویس‌های فعال یا تحویل‌داده‌شده قابل تمدید هستند.', show_alert=True)
        return

    await state.clear()
    await state.update_data(renew_of_order_id=order_id)
    
    from app.handlers.order import _begin_buy_message
    await _begin_buy_message(callback.message, state, db)
    await callback.answer()
