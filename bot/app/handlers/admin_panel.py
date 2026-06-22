"""Admin panel: reply keyboard + inline dashboards (Persian UI)."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import (
    CUSTOMERS,
    LOCATIONS,
    OFFER,
    ORDERS_MANAGE,
    ORDERS_REVIEW,
    PANEL,
    SERVICES,
    SETTINGS,
    TOOLS_BROADCAST,
    TOOLS_MISC,
    TOOLS_SYNC,
    USERS,
)
from app.handlers.admin_helpers import (
    admin_can,
    admin_from_message,
    admin_panel_access,
    format_base_plans_text,
    format_settings_text,
    format_stats_text,
    is_admin,
    location_pricing_label,
    run_clear_declined,
    run_sync_panel,
)
from app.handlers.admin_order import send_admin_order_view
from app.handlers.admin_ui_helpers import (
    admin_edit_or_answer,
    callback_inline_ids,
    format_services_list_text,
    format_tools_menu_text,
    present_inline_screen,
)

from app.channel_gate import is_gate_enabled
from app.handlers.admin_users_ui import format_user_detail, format_users_page
from app.handlers.log_channel import start_log_channel_wizard
from app.handlers.required_channel import start_required_channel_wizard

log = logging.getLogger(__name__)

router = Router(name="admin_panel")


class AdminPanelFlow(StatesGroup):
    waiting_order_id = State()


async def _guard_cb(
    callback: CallbackQuery, settings: Settings, db: Database, perm: str
) -> int | None:
    if callback.from_user is None:
        await callback.answer()
        return None
    uid = callback.from_user.id
    if not is_admin(uid, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return None
    if not admin_can(uid, perm, settings, db):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return None
    return uid


async def _guard_cb_any(
    callback: CallbackQuery, settings: Settings, db: Database, *perms: str
) -> int | None:
    if callback.from_user is None:
        await callback.answer()
        return None
    uid = callback.from_user.id
    if not is_admin(uid, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return None
    if not any(admin_can(uid, p, settings, db) for p in perms):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return None
    return uid


def _admin_home_body(db: Database) -> str:
    return f"{texts.ADMIN_PANEL_HOME}\n\n{format_stats_text(db)}"


async def send_admin_home(
    message: Message,
    settings: Settings,
    db: Database,
    *,
    admin_user_id: int | None = None,
    edit_in_place: bool = False,
) -> None:
    uid = admin_user_id
    if uid is None:
        user = message.from_user
        # callback.message is from the bot — caller must pass admin_user_id
        if user is None or user.is_bot:
            return
        if not admin_panel_access(user.id, settings, db):
            return
        uid = user.id
    elif not admin_panel_access(uid, settings, db):
        return
    markup = keyboards.admin_reply_keyboard(uid, settings, db)
    if edit_in_place:
        await admin_edit_or_answer(
            message,
            _admin_home_body(db),
            keyboards.admin_home_inline(uid, settings, db),
            edit_in_place=True,
        )
        return
    await message.answer(
        texts.ADMIN_PANEL_HOME,
        reply_markup=markup,
    )
    await message.answer(
        format_stats_text(db),
        reply_markup=keyboards.admin_home_inline(uid, settings, db),
    )


async def send_pending_list(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> None:
    rows = db.pending_orders(limit=20)
    footer = keyboards.admin_pending_footer(user_id, settings, db)
    if not rows:
        await admin_edit_or_answer(
            message,
            texts.ADMIN_PENDING_EMPTY,
            footer,
            edit_in_place=edit_in_place,
        )
        return

    buttons: list[dict] = []
    for r in rows:
        buttons.append({
            "id": r["id"],
            "label": texts.ADMIN_PENDING_BTN.format(
                id=r["id"],
                price=texts.format_price(int(r["price"])),
                user_id=r["user_id"],
            ),
        })
    await admin_edit_or_answer(
        message,
        texts.ADMIN_PENDING_HEADER.format(count=len(rows)),
        keyboards.admin_pending_list(buttons, user_id, settings, db),
        edit_in_place=edit_in_place,
    )


async def send_settings(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
    bot: Bot | None = None,
    chat_id: int | None = None,
    message_id: int | None = None,
) -> bool:
    body = texts.ADMIN_SETTINGS_MENU.format(
        settings_block=format_settings_text(db)
    )
    markup = keyboards.admin_settings_inline(user_id, settings, db)
    cid = chat_id if chat_id is not None else message.chat.id
    mid = message_id
    if mid is None and edit_in_place:
        mid = message.message_id
    if bot is not None:
        return await present_inline_screen(
            bot,
            chat_id=cid,
            message_id=mid if edit_in_place else None,
            text=body,
            reply_markup=markup,
            prefer_edit=edit_in_place,
        )
    await admin_edit_or_answer(
        message,
        body,
        markup,
        edit_in_place=edit_in_place,
    )
    return True


async def _present_settings_on_callback(
    callback: CallbackQuery,
    bot: Bot,
    settings: Settings,
    db: Database,
    user_id: int,
) -> bool:
    target = callback_inline_ids(callback)
    if target is None:
        return False
    chat_id, msg_id = target
    body = texts.ADMIN_SETTINGS_MENU.format(
        settings_block=format_settings_text(db)
    )
    markup = keyboards.admin_settings_inline(user_id, settings, db)
    return await present_inline_screen(
        bot,
        chat_id=chat_id,
        message_id=msg_id,
        text=body,
        reply_markup=markup,
        prefer_edit=True,
    )


def _services_menu_body(db: Database) -> str:
    body = format_services_list_text(db)
    if len(body) <= 3900:
        return body
    mode = "روشن ✅" if db.is_manual_purchase_enabled() else "خاموش ❌"
    return texts.ADMIN_SERVICES_MENU.format(
        manual_mode=mode,
        packages_block=(
            "ℹ️ لیست خیلی طولانی است — "
            "<code>/listservices</code> را بزنید."
        ),
    )


async def send_services(
    message: Message,
    db: Database,
    settings: Settings,
    user_id: int,
    *,
    edit_in_place: bool = False,
    bot: Bot | None = None,
) -> None:
    body = _services_menu_body(db)
    markup = keyboards.admin_services_inline(
        manual_enabled=db.is_manual_purchase_enabled()
    )
    if bot is not None:
        await present_inline_screen(
            bot,
            chat_id=message.chat.id,
            message_id=message.message_id if edit_in_place else None,
            text=body,
            reply_markup=markup,
            prefer_edit=edit_in_place,
        )
        return
    await admin_edit_or_answer(
        message,
        body,
        markup,
        edit_in_place=edit_in_place,
    )


async def send_base_plans(
    message: Message,
    db: Database,
    settings: Settings,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> None:
    await admin_edit_or_answer(
        message,
        format_base_plans_text(db),
        keyboards.admin_plans_keyboard(
            db.get_volume_presets(),
            db.get_duration_presets(),
        ),
        edit_in_place=edit_in_place,
    )


async def send_tools(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> None:
    await admin_edit_or_answer(
        message,
        format_tools_menu_text(db, settings),
        keyboards.admin_tools_inline(
            user_id,
            settings,
            db,
            has_log_channel=bool(db.get_log_channel_id()),
            has_req_channel=is_gate_enabled(db, settings),
        ),
        edit_in_place=edit_in_place,
    )


async def send_locations(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    edit_in_place: bool = False,
) -> None:
    locs = db.list_locations(only_enabled=False)
    if not locs:
        await admin_edit_or_answer(
            message,
            texts.ADMIN_LOC_EMPTY,
            keyboards.admin_home_inline(user_id, settings, db),
            edit_in_place=edit_in_place,
        )
        return
    await admin_edit_or_answer(
        message,
        texts.ADMIN_LOCATIONS_MENU.format(count=len(locs)),
        keyboards.admin_locations_list(locs),
        edit_in_place=edit_in_place,
    )


async def send_location_detail(
    message: Message,
    db: Database,
    loc_id: int,
    *,
    edit_in_place: bool = False,
) -> bool:
    loc = db.get_location(loc_id)
    if loc is None:
        return False

    sub = escape(loc.sub_url_template) if loc.sub_url_template else "—"
    test_line = ""
    if loc.is_test:
        test_line = (
            f"\n🧪 <b>لوکیشن تست</b> — {texts.format_test_volume()} · "
            f"{texts.format_test_duration()} · رایگان · "
            f"دکمه تست: {'روشن' if db.is_test_feature_enabled() else 'خاموش'}\n"
        )
    purchase_state = (
        "باز ✅"
        if loc.purchase_enabled
        else "بسته ⛔ (فقط سرویس‌های قبلی)"
    )
    if loc.is_test:
        purchase_state = "— (لوکیشن تست)"
    text = texts.ADMIN_LOC_DETAIL.format(
        id=loc.id,
        state_emoji="🟢" if loc.enabled else "🔴",
        name=escape(loc.name),
        test_line=test_line,
        purchase_state=purchase_state,
        base_url=escape(loc.base_url),
        inbounds=",".join(str(i) for i in loc.inbound_ids) or "—",
        sub=sub,
        pricing=escape(location_pricing_label(db, loc)),
    )
    await admin_edit_or_answer(
        message,
        text,
        keyboards.admin_location_detail(
            loc.id,
            enabled=loc.enabled,
            purchase_enabled=loc.purchase_enabled,
            is_test=loc.is_test,
        ),
        edit_in_place=edit_in_place,
    )
    return True


async def send_users(
    message: Message,
    settings: Settings,
    db: Database,
    page: int = 0,
    *,
    user_id: int,
    edit_in_place: bool = False,
) -> None:
    text, total_pages, users = await format_users_page(db, page)
    if not users:
        markup = keyboards.admin_home_inline(user_id, settings, db)
        if edit_in_place:
            try:
                await message.edit_text(
                    text, reply_markup=markup, parse_mode=ParseMode.HTML
                )
            except Exception:  # noqa: BLE001
                await message.answer(
                    text, reply_markup=markup, parse_mode=ParseMode.HTML
                )
        else:
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        return

    markup = keyboards.admin_users_keyboard(
        users, page=page, total_pages=total_pages
    )
    if edit_in_place:
        try:
            await message.edit_text(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        except Exception:  # noqa: BLE001
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    else:
        await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)


async def send_user_detail(
    message: Message,
    settings: Settings,
    db: Database,
    user_id: int,
    *,
    actor_id: int,
    edit_in_place: bool = False,
) -> bool:
    row = db.get_user(user_id)
    text = await format_user_detail(db, user_id)
    if text is None or row is None:
        return False
    is_banned = bool(row["is_banned"])
    orders = db.list_user_orders_admin(user_id, limit=30)
    order_ids = [int(o["id"]) for o in orders][:6]
    markup = keyboards.admin_user_detail_keyboard(
        user_id,
        actor_id,
        settings,
        db,
        is_banned=is_banned,
        order_ids=order_ids,
    )
    if edit_in_place:
        try:
            await message.edit_text(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
        except Exception:  # noqa: BLE001
            await message.answer(
                text, reply_markup=markup, parse_mode=ParseMode.HTML
            )
    else:
        await message.answer(text, reply_markup=markup, parse_mode=ParseMode.HTML)
    return True


def _order_receipt_caption(db: Database, order) -> str | None:
    if order is None or order["status"] != "awaiting_review":
        return None
    loc = db.get_location(int(order["location_id"]))
    loc_name = loc.name if loc else "—"
    user_row = db.get_user(int(order["user_id"]))
    if user_row:
        full_name = escape(
            " ".join(
                p
                for p in [user_row["first_name"], user_row["last_name"]]
                if p
            )
            or "—"
        )
    else:
        full_name = "—"
    return texts.NEW_RECEIPT_NOTIFY.format(
        order_id=order["id"],
        user_id=order["user_id"],
        full_name=full_name,
        location=escape(loc_name),
        volume=int(order["volume_gb"]),
        days=int(order["duration_days"]),
        price=texts.format_price(int(order["price"])),
    )


# ---------- /admin opens panel ----------
@router.message(Command("clear"))
async def cmd_clear(message: Message, settings: Settings, db: Database) -> None:
    if message.from_user is None:
        return
    if not is_admin(message.from_user.id, settings):
        return

    try:
        count = int(message.text.split()[1])
    except (IndexError, ValueError, AttributeError):
        count = 100
        
    msg = await message.answer(f"🧹 در حال پاکسازی {count} پیام اخیر...")
    
    deleted = 0
    import asyncio
    for i in range(message.message_id, max(0, message.message_id - count), -1):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=i)
            deleted += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
            
    try:
        await msg.edit_text(f"✅ پاکسازی انجام شد. {deleted} پیام حذف شد.")
    except Exception:
        pass


@router.message(Command("admin"))
@router.message(Command("panel"))
async def cmd_admin_panel(message: Message, settings: Settings, db: Database) -> None:
    if message.from_user is None:
        return
    if not admin_panel_access(message.from_user.id, settings, db):
        await message.answer(
            texts.NOT_ADMIN
            if not is_admin(message.from_user.id, settings)
            else texts.NOT_PERMITTED
        )
        return
    await send_admin_home(message, settings, db)


# ---------- reply keyboard ----------
@router.message(F.text.in_(keyboards.ADMIN_MENU_BUTTONS), StateFilter(None))
async def admin_menu_buttons(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not admin_from_message(message, settings):
        return
    user = message.from_user
    if user is None:
        return
    uid = user.id

    text = message.text or ""
    if text == texts.ADMIN_BTN_PANEL:
        if not admin_panel_access(uid, settings, db):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_admin_home(message, settings, db)
    elif text == texts.ADMIN_BTN_DASHBOARD:
        if not admin_panel_access(uid, settings, db):
            await message.answer(texts.NOT_PERMITTED)
            return
        await state.clear()
        await send_admin_home(message, settings, db, admin_user_id=uid)
    elif text == texts.ADMIN_BTN_PENDING:
        if not admin_can(uid, ORDERS_REVIEW, settings, db):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_pending_list(message, settings, db, uid)
    elif text == texts.ADMIN_BTN_SETTINGS:
        if not (
            admin_can(uid, SETTINGS, settings, db)
            or admin_can(uid, SERVICES, settings, db)
            or admin_can(uid, OFFER, settings, db)
        ):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_settings(message, settings, db, uid)
    elif text == texts.ADMIN_BTN_LOCATIONS:
        if not admin_can(uid, LOCATIONS, settings, db):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_locations(message, settings, db, uid)
    elif text == texts.ADMIN_BTN_TOOLS:
        if not (
            admin_can(uid, TOOLS_BROADCAST, settings, db)
            or admin_can(uid, TOOLS_SYNC, settings, db)
            or admin_can(uid, TOOLS_MISC, settings, db)
        ):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_tools(message, settings, db, uid)
    elif text == texts.ADMIN_BTN_USERS:
        if not admin_can(uid, USERS, settings, db):
            await message.answer(texts.NOT_PERMITTED)
            return
        await send_users(message, settings, db, page=0, user_id=uid)


# ---------- inline navigation ----------
@router.callback_query(F.data == keyboards.CB_ADM_HOME)
async def cb_admin_home(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if await _guard_cb(callback, settings, db, PANEL) is None:
        return
    await state.clear()
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await send_admin_home(
        callback.message,
        settings,
        db,
        admin_user_id=callback.from_user.id,
        edit_in_place=True,
    )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_DASH)
async def cb_admin_dash(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    """Legacy callback — same as refreshing admin home."""
    if await _guard_cb(callback, settings, db, PANEL) is None:
        return
    await state.clear()
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await send_admin_home(
        callback.message,
        settings,
        db,
        admin_user_id=callback.from_user.id,
        edit_in_place=True,
    )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_ORDERS)
async def cb_admin_orders(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    """Legacy callback — open pending review (or order lookup)."""
    if await _guard_cb_any(callback, settings, db, ORDERS_REVIEW, ORDERS_MANAGE) is None:
        return
    await state.clear()
    if not isinstance(callback.message, Message) or callback.from_user is None:
        await callback.answer()
        return
    uid = callback.from_user.id
    if admin_can(uid, ORDERS_REVIEW, settings, db):
        await send_pending_list(
            callback.message, settings, db, uid, edit_in_place=True
        )
    else:
        await admin_edit_or_answer(
            callback.message,
            texts.ADMIN_ORDER_LOOKUP_PROMPT,
            keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_HOME),
            edit_in_place=True,
        )
        await state.set_state(AdminPanelFlow.waiting_order_id)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_PENDING_LIST)
async def cb_admin_pending(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if await _guard_cb(callback, settings, db, ORDERS_REVIEW) is None:
        return
    await state.clear()
    if isinstance(callback.message, Message) and callback.from_user is not None:
        await send_pending_list(
            callback.message,
            settings,
            db,
            callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_SETTINGS)
async def cb_admin_settings(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    uid = callback.from_user.id
    if not (
        admin_can(uid, SETTINGS, settings, db)
        or admin_can(uid, SERVICES, settings, db)
        or admin_can(uid, OFFER, settings, db)
    ):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    await state.clear()
    if callback.from_user is None:
        await callback.answer()
        return
    if not await _present_settings_on_callback(
        callback, bot, settings, db, callback.from_user.id
    ):
        await callback.answer("پیام یافت نشد.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_SETTINGS_REFRESH)
async def cb_admin_settings_refresh(
    callback: CallbackQuery,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    if await _guard_cb(callback, settings, db, SETTINGS) is None:
        return
    if callback.from_user is not None:
        await _present_settings_on_callback(
            callback, bot, settings, db, callback.from_user.id
        )
    await callback.answer(texts.ADMIN_BTN_REFRESH)


@router.callback_query(F.data == keyboards.CB_ADM_SERVICES)
async def cb_admin_services(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    """Open sales plans — replace the current inline message (e.g. from تنظیمات)."""
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    await state.clear()

    target = callback_inline_ids(callback)
    if target is None or callback.from_user is None:
        log.warning("cb_admin_services: no callback.message")
        await callback.answer("پیام یافت نشد.", show_alert=True)
        return

    chat_id, msg_id = target
    body = _services_menu_body(db)
    markup = keyboards.admin_services_inline(
        manual_enabled=db.is_manual_purchase_enabled()
    )
    try:
        await present_inline_screen(
            bot,
            chat_id=chat_id,
            message_id=msg_id,
            text=body,
            reply_markup=markup,
            prefer_edit=True,
        )
        await callback.answer()
    except Exception:  # noqa: BLE001
        log.exception(
            "cb_admin_services failed chat=%s msg=%s", chat_id, msg_id
        )
        try:
            await present_inline_screen(
                bot,
                chat_id=chat_id,
                message_id=None,
                text=body,
                reply_markup=markup,
                prefer_edit=False,
            )
            await callback.answer()
        except Exception:  # noqa: BLE001
            log.exception("cb_admin_services fallback failed")
            await callback.answer(
                "باز کردن پلن‌های فروش ممکن نشد. /admin را بزنید و دوباره امتحان کنید.",
                show_alert=True,
            )


@router.callback_query(F.data == keyboards.CB_ADM_SERVICES_REFRESH)
async def cb_admin_services_refresh(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    """Refresh list — always post a new message so updates are visible."""
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    await state.clear()
    await callback.answer(texts.ADMIN_BTN_REFRESH)
    if callback.message is None or callback.from_user is None:
        return
    await send_services(
        callback.message,
        db,
        settings,
        callback.from_user.id,
        edit_in_place=False,
        bot=bot,
    )


@router.callback_query(F.data == keyboards.CB_ADM_ADDSVC_HELP)
async def cb_admin_services_legacy_hint(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    """Old inline keyboards used adm:hsvc — open the sales-plans menu."""
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    await state.clear()
    target = callback_inline_ids(callback)
    if target is None or callback.from_user is None:
        await callback.answer("پیام یافت نشد.", show_alert=True)
        return
    chat_id, msg_id = target
    body = _services_menu_body(db)
    markup = keyboards.admin_services_inline(
        manual_enabled=db.is_manual_purchase_enabled()
    )
    await present_inline_screen(
        bot,
        chat_id=chat_id,
        message_id=msg_id,
        text=body,
        reply_markup=markup,
        prefer_edit=True,
    )
    await callback.answer()


@router.message(F.text == texts.ADMIN_BTN_SERVICES)
async def msg_admin_services(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    """Reply-keyboard «پلن‌های فروش» — works even during other admin wizards."""
    if not admin_from_message(message, settings):
        return
    user = message.from_user
    if user is None:
        return
    if not admin_can(user.id, SERVICES, settings, db):
        await message.answer(texts.NOT_PERMITTED)
        return
    await state.clear()
    await send_services(message, db, settings, user.id)


@router.callback_query(F.data == keyboards.CB_ADM_TOGGLE_MANUAL)
async def cb_admin_toggle_manual(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    await state.clear()
    enabled = not db.is_manual_purchase_enabled()
    db.set_manual_purchase_enabled(enabled)
    mode = "پلن ازپیش‌تعریف ✅" if enabled else "فرمول قیمت ❌"
    await callback.answer(f"خرید دستی: {mode}")
    if callback.message is not None and callback.from_user is not None:
        await send_services(
            callback.message,
            db,
            settings,
            callback.from_user.id,
            edit_in_place=True,
            bot=bot,
        )


@router.callback_query(F.data == keyboards.CB_ADM_PLANS)
async def cb_admin_plans(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    if isinstance(callback.message, Message) and callback.from_user is not None:
        await send_base_plans(
            callback.message,
            db,
            settings,
            callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_VOL_DEL_PREFIX))
async def cb_admin_del_volume(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_VOL_DEL_PREFIX)
    try:
        gb = int(raw)
    except ValueError:
        await callback.answer()
        return
    ok, reason = db.remove_volume_preset(gb)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await callback.answer(msg, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_base_plans_text(db),
            reply_markup=keyboards.admin_plans_keyboard(
                db.get_volume_presets(),
                db.get_duration_presets(),
            ),
        )
    await callback.answer(texts.ADMIN_PLAN_VOL_REMOVED.format(gb=gb))


@router.callback_query(F.data.startswith(keyboards.CB_ADM_DUR_DEL_PREFIX))
async def cb_admin_del_duration(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, SERVICES) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_DUR_DEL_PREFIX)
    try:
        days = int(raw)
    except ValueError:
        await callback.answer()
        return
    ok, reason = db.remove_duration_preset(days)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await callback.answer(msg, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            format_base_plans_text(db),
            reply_markup=keyboards.admin_plans_keyboard(
                db.get_volume_presets(),
                db.get_duration_presets(),
            ),
        )
    await callback.answer(texts.ADMIN_PLAN_DUR_REMOVED.format(days=days))


@router.callback_query(F.data == keyboards.CB_ADM_TOOLS)
async def cb_admin_tools(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    uid = callback.from_user.id
    if not is_admin(uid, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return
    if not (
        admin_can(uid, TOOLS_BROADCAST, settings, db)
        or admin_can(uid, TOOLS_SYNC, settings, db)
        or admin_can(uid, TOOLS_MISC, settings, db)
    ):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return
    if isinstance(callback.message, Message):
        await send_tools(callback.message, settings, db, callback.from_user.id, edit_in_place=True)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_LOCATIONS_LIST)
async def cb_admin_locations(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, LOCATIONS) is None:
        return
    if isinstance(callback.message, Message):
        await send_locations(
            callback.message, settings, db, callback.from_user.id, edit_in_place=True
        )
    await callback.answer()


# ---------- order lookup FSM ----------
@router.callback_query(F.data == keyboards.CB_ADM_ORDER_LOOKUP)
async def cb_admin_order_lookup_start(callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, ORDERS_MANAGE) is None:
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await state.set_state(AdminPanelFlow.waiting_order_id)
    await admin_edit_or_answer(
        callback.message,
        texts.ADMIN_ORDER_LOOKUP_PROMPT,
        keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_PENDING_LIST),
        edit_in_place=True,
    )
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminPanelFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminPanelFlow)
)
async def admin_panel_flow_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    user_id = event.from_user.id if event.from_user else None
    if user_id is None or not admin_can(user_id, ORDERS_MANAGE, settings, db):
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
            if admin_can(user_id, ORDERS_REVIEW, settings, db):
                await send_pending_list(
                    event.message, settings, db, user_id, edit_in_place=True
                )
            else:
                await send_admin_home(
                    event.message,
                    settings,
                    db,
                    admin_user_id=user_id,
                    edit_in_place=True,
                )
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)
        if isinstance(event, Message):
            await send_admin_home(event, settings, db)


@router.message(StateFilter(AdminPanelFlow.waiting_order_id))
async def admin_panel_order_id_input(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    user = message.from_user
    if user is None or not admin_can(user.id, ORDERS_MANAGE, settings, db):
        await state.clear()
        await message.answer(
            texts.NOT_ADMIN
            if user is None or not is_admin(user.id, settings)
            else texts.NOT_PERMITTED
        )
        return

    raw = (message.text or "").strip()
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(
            texts.ADMIN_ORDER_LOOKUP_NOTFOUND.format(order_id=escape(raw or "—")),
            reply_markup=keyboards.admin_flow_cancel_inline(
                back_data=keyboards.CB_ADM_PENDING_LIST
            ),
        )
        return

    await state.clear()
    if not await send_admin_order_view(
        message, db, order_id, manage_header=True
    ):
        await message.answer(
            texts.ADMIN_ORDER_LOOKUP_NOTFOUND.format(order_id=order_id),
            reply_markup=keyboards.admin_pending_footer(user.id, settings, db),
        )


_HINT_CALLBACKS = frozenset({
    keyboards.CB_ADM_SETCARD_HELP,
    keyboards.CB_ADM_SETPRICE_HELP,
    keyboards.CB_ADM_ADDLOC_HELP,
    keyboards.CB_ADM_EDITSVC_HELP,
    keyboards.CB_ADM_PLAN_ADD_HINT,
})


@router.callback_query(F.data.in_(_HINT_CALLBACKS))
async def cb_admin_hint(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, SETTINGS) is None:
        return
    hints = {
        keyboards.CB_ADM_SETCARD_HELP: texts.SET_CARD_USAGE,
        keyboards.CB_ADM_SETPRICE_HELP: texts.SET_PRICE_USAGE,
        keyboards.CB_ADM_ADDLOC_HELP: texts.ADD_LOC_USAGE,
        keyboards.CB_ADM_EDITSVC_HELP: texts.EDIT_SERVICE_USAGE,
        keyboards.CB_ADM_PLAN_ADD_HINT: texts.ADMIN_PLAN_USAGE,
    }
    if isinstance(callback.message, Message):
        await callback.message.answer(hints.get(callback.data or "", texts.ADMIN_HELP))
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_LOG_CHANNEL)
async def cb_admin_log_channel(callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await start_log_channel_wizard(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_LOG_CHANNEL_OFF)
async def cb_admin_log_channel_off(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    db.set_log_channel_id(None)
    if isinstance(callback.message, Message):
        await send_tools(callback.message, settings, db, callback.from_user.id, edit_in_place=True)
    await callback.answer(texts.LOG_CHANNEL_CLEARED)


@router.callback_query(F.data == keyboards.CB_ADM_REQ_CHANNEL)
async def cb_admin_req_channel(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await start_required_channel_wizard(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == keyboards.CB_ADM_REQ_CHANNEL_OFF)
async def cb_admin_req_channel_off(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    db.set_required_channel(None)
    if isinstance(callback.message, Message):
        await send_tools(
            callback.message, settings, db, callback.from_user.id, edit_in_place=True
        )
    await callback.answer(texts.REQ_CHANNEL_CLEARED)


@router.callback_query(F.data == keyboards.CB_ADM_TOGGLE_TEST)
async def cb_admin_toggle_test(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    enabled = not db.is_test_feature_enabled()
    db.set_test_feature_enabled(enabled)
    state_word = "روشن ✅" if enabled else "خاموش ❌"
    if isinstance(callback.message, Message):
        await send_tools(callback.message, settings, db, callback.from_user.id, edit_in_place=True)
    await callback.answer(f"دکمه تست: {state_word}")


@router.callback_query(F.data.startswith(keyboards.CB_ADM_TOGGLE_TEST_LOC_PREFIX))
async def cb_admin_toggle_test_from_loc(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_MISC) is None:
        return
    raw = (callback.data or "").removeprefix(
        keyboards.CB_ADM_TOGGLE_TEST_LOC_PREFIX
    )
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    enabled = not db.is_test_feature_enabled()
    db.set_test_feature_enabled(enabled)
    state_word = "روشن ✅" if enabled else "خاموش ❌"
    if isinstance(callback.message, Message):
        await send_location_detail(
            callback.message,
            db,
            loc_id,
            edit_in_place=True,
        )
    await callback.answer(f"دکمه تست: {state_word}")


@router.callback_query(F.data == keyboards.CB_ADM_USERS)
async def cb_admin_users(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    if isinstance(callback.message, Message):
        await send_users(
            callback.message,
            settings,
            db,
            page=0,
            user_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USERS_PAGE_PREFIX))
async def cb_admin_users_page(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USERS_PAGE_PREFIX)
    try:
        page = int(raw)
    except ValueError:
        await callback.answer()
        return
    if isinstance(callback.message, Message):
        await send_users(
            callback.message,
            settings,
            db,
            page=page,
            user_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_INFO_PREFIX))
async def cb_admin_user_info(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if await _guard_cb_any(
        callback, settings, db, CUSTOMERS, USERS, ORDERS_REVIEW
    ) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USER_INFO_PREFIX)
    try:
        user_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    row = db.get_user(user_id)
    if row is None:
        await callback.answer("کاربر یافت نشد.", show_alert=True)
        return
    full_name = " ".join(
        p for p in [row["first_name"], row["last_name"]] if p
    ) or "—"
    username = f"@{row['username']}" if row["username"] else "—"
    await callback.answer(
        texts.ADMIN_USER_INFO_ALERT.format(
            user_id=user_id,
            full_name=full_name,
            username=username,
        ),
        show_alert=True,
    )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_DETAIL_PREFIX))
async def cb_admin_user_detail(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USER_DETAIL_PREFIX)
    try:
        user_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await send_user_detail(
        callback.message,
        settings,
        db,
        user_id,
        actor_id=callback.from_user.id,
        edit_in_place=True,
    ):
        await callback.answer("کاربر یافت نشد.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_UPDATE_PREFIX))
async def cb_admin_update_user(callback: CallbackQuery, bot: Bot, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_USER_UPDATE_PREFIX)
    try:
        user_id = int(raw)
    except ValueError:
        await callback.answer()
        return
    
    try:
        chat = await bot.get_chat(user_id)
        db.upsert_user(
            user_id=user_id,
            username=chat.username,
            first_name=chat.first_name,
            last_name=chat.last_name,
            lang_code=None,
        )
        await callback.answer("✅ اطلاعات کاربر از تلگرام بروزرسانی شد.", show_alert=True)
    except Exception:
        await callback.answer("❌ امکان دریافت اطلاعات از تلگرام وجود ندارد (کاربر ربات را استارت نکرده است).", show_alert=True)
        return

    if not isinstance(callback.message, Message):
        return

    # Refresh the view
    if not await send_user_detail(
        callback.message,
        settings,
        db,
        user_id,
        actor_id=callback.from_user.id,
        edit_in_place=True,
    ):
        pass


@router.callback_query(F.data == keyboards.CB_ADM_CMD_HELP)
async def cb_admin_cmd_help(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, PANEL) is None:
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(texts.ADMIN_HELP)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_BAN_PREFIX))
async def cb_admin_ban_user(callback: CallbackQuery, bot: Bot, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_USER_BAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if user_id == callback.from_user.id:
        await callback.answer(texts.BAN_SELF, show_alert=True)
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, True)
    if isinstance(callback.message, Message):
        await send_user_detail(
            callback.message,
            settings,
            db,
            user_id,
            actor_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer(texts.BAN_OK.format(user_id=user_id))
    await _log_ban_from_callback(bot, db, callback, user_id, banned=True)


@router.callback_query(F.data.startswith(keyboards.CB_ADM_USER_UNBAN_PREFIX))
async def cb_admin_unban_user(callback: CallbackQuery, bot: Bot, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, USERS) is None:
        return
    try:
        user_id = int(
            (callback.data or "").removeprefix(keyboards.CB_ADM_USER_UNBAN_PREFIX)
        )
    except ValueError:
        await callback.answer()
        return
    if db.get_user(user_id) is None:
        await callback.answer(texts.BAN_USER_NOTFOUND, show_alert=True)
        return
    db.set_user_banned(user_id, False)
    if isinstance(callback.message, Message):
        await send_user_detail(
            callback.message,
            settings,
            db,
            user_id,
            actor_id=callback.from_user.id,
            edit_in_place=True,
        )
    await callback.answer(texts.UNBAN_OK.format(user_id=user_id))
    await _log_ban_from_callback(bot, db, callback, user_id, banned=False)


async def _log_ban_from_callback(
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


# ---------- pending order → resend receipt ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_ORDER_VIEW_PREFIX))
async def cb_admin_view_order(callback: CallbackQuery, bot: Bot, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, ORDERS_REVIEW) is None:
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ORDER_VIEW_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    order = db.get_order(order_id)
    caption = _order_receipt_caption(db, order)
    if caption is None:
        await callback.answer("سفارش در انتظار بررسی نیست.", show_alert=True)
        return

    user_id = int(order["user_id"])
    review_kb = keyboards.admin_review(order_id=order_id, user_id=user_id)
    file_id = order["screenshot_file_id"]
    admin_chat = callback.from_user.id

    try:
        if file_id:
            sent = await bot.send_photo(
                admin_chat,
                photo=file_id,
                caption=caption,
                reply_markup=review_kb,
            )
            if sent:
                db.add_admin_receipt_message(order_id, admin_chat, sent.message_id)
        else:
            sent = await bot.send_message(
                admin_chat, caption, reply_markup=review_kb
            )
            if sent:
                db.add_admin_receipt_message(order_id, admin_chat, sent.message_id)
    except Exception:  # noqa: BLE001
        await callback.answer("ارسال رسید ناموفق بود.", show_alert=True)
        return
    await callback.answer("رسید ارسال شد ✅")


# ---------- locations detail / toggle / purge prompt ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_DETAIL_PREFIX))
async def cb_admin_loc_detail(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, LOCATIONS) is None:
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_DETAIL_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    if not await send_location_detail(
        callback.message,
        db,
        loc_id,
        edit_in_place=True,
    ):
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_TOGGLE_PREFIX))
async def cb_admin_loc_toggle(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, LOCATIONS) is None:
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_TOGGLE_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return

    new_state = not loc.enabled
    db.set_location_enabled(loc_id, new_state)
    state_word = "فعال" if new_state else "غیرفعال"
    await callback.answer(f"لوکیشن {state_word} شد ✅")
    if isinstance(callback.message, Message):
        await send_location_detail(
            callback.message,
            db,
            loc_id,
            edit_in_place=True,
        )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_PURCHASE_PREFIX))
async def cb_admin_loc_purchase_toggle(
    callback: CallbackQuery, settings: Settings, db: Database
) -> None:
    if await _guard_cb(callback, settings, db, LOCATIONS) is None:
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_PURCHASE_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return
    if loc.is_test:
        await callback.answer("لوکیشن تست قابل تغییر نیست.", show_alert=True)
        return

    new_state = not loc.purchase_enabled
    db.set_location_purchase_enabled(loc_id, new_state)
    state_word = "باز" if new_state else "بسته"
    await callback.answer(f"خرید جدید {state_word} شد ✅")
    if isinstance(callback.message, Message):
        await send_location_detail(
            callback.message,
            db,
            loc_id,
            edit_in_place=True,
        )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_PURGE_PREFIX))
async def cb_admin_loc_purge_prompt(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, LOCATIONS) is None:
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_PURGE_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await callback.answer("لوکیشن یافت نشد.", show_alert=True)
        return

    count = db.count_orders_for_location(loc_id)
    if isinstance(callback.message, Message):
        await callback.message.answer(
            texts.PURGE_CONFIRM.format(
                id=loc_id, name=escape(loc.name), count=count
            ),
            reply_markup=keyboards.purge_confirm(loc_id),
        )
    await callback.answer()


# ---------- tools ----------
@router.callback_query(F.data == keyboards.CB_ADM_TOOL_SYNC)
async def cb_admin_tool_sync(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_SYNC) is None:
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    await callback.answer()
    await callback.message.answer(texts.SYNC_PANEL_START)
    for chunk in await run_sync_panel(db):
        await callback.message.answer(chunk)


@router.callback_query(F.data == keyboards.CB_ADM_TOOL_CLEAR)
async def cb_admin_tool_clear(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_SYNC) is None:
        return
    if isinstance(callback.message, Message):
        await callback.message.answer(run_clear_declined(db))
    await callback.answer("انجام شد ✅")

@router.callback_query(F.data == keyboards.CB_ADM_TOOL_CLEAR_TEST)
async def cb_admin_tool_clear_test(callback: CallbackQuery, settings: Settings, db: Database) -> None:
    if await _guard_cb(callback, settings, db, TOOLS_SYNC) is None:
        return
    count = db.clear_test_clients()
    if isinstance(callback.message, Message):
        await callback.message.answer(f"✅ تعداد {count} اکانت تست از دیتابیس ربات پاکسازی شد. اکنون کاربران قدیمی می‌توانند مجددا تست دریافت کنند.")
    await callback.answer("انجام شد ✅")
