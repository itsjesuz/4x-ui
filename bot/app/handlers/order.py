"""Multi-step order flow:

  location -> volume (preset or custom) -> duration -> review/confirm
           -> payment instructions (awaiting_payment)
           -> user uploads receipt photo (awaiting_review)
           -> admin gets notified with Accept/Decline buttons
"""

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
from app.handlers.buyer_ui import buyer_reply_keyboard
from app.logs import Actor, make_logger


router = Router(name="order")
log = logging.getLogger(__name__)


class OrderFlow(StatesGroup):
    picking_location    = State()
    picking_package     = State()
    picking_volume      = State()
    entering_custom_vol = State()
    picking_duration    = State()
    reviewing           = State()
    awaiting_receipt    = State()


PURCHASE_MODE_PACKAGES = "packages"
PURCHASE_MODE_LEGACY = "legacy"


# ---------- helpers ----------
async def _edit_or_answer(callback: CallbackQuery, text: str, reply_markup=None) -> None:
    if isinstance(callback.message, Message):
        try:
            await callback.message.edit_text(
                text,
                reply_markup=reply_markup,
                parse_mode=ParseMode.HTML,
            )
            return
        except Exception:  # noqa: BLE001 — message may be uneditable (e.g. has a photo)
            pass
    if callback.message is not None:
        await callback.message.answer(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.HTML,
        )


def _calc_base_price_for(
    db: Database, volume_gb: int, duration_days: int, location_id: int
) -> int:
    base, per_gb, per_day = db.get_pricing_for_location(location_id)
    return texts.calc_price(volume_gb, duration_days, base, per_gb, per_day)


def _calc_price_for(
    db: Database, volume_gb: int, duration_days: int, location_id: int
) -> int:
    return db.resolve_price(
        _calc_base_price_for(db, volume_gb, duration_days, location_id)
    )


async def _clear_plan_selection(state: FSMContext) -> None:
    data = await state.get_data()
    for key in ("volume_gb", "duration_days", "price", "package_id"):
        data.pop(key, None)
    await state.set_data(data)


def _resolve_order_terms(
    data: dict, db: Database
) -> tuple[int, str, int, int, int] | None:
    """Validate FSM data; re-read package price from DB before creating order."""
    try:
        location_id = int(data["location_id"])
        location_name = str(data["location_name"])
    except (KeyError, TypeError, ValueError):
        return None

    loc = db.get_location(location_id)
    if loc is None or not loc.enabled or not loc.purchase_enabled or loc.is_test:
        return None

    mode = str(data.get("purchase_mode", PURCHASE_MODE_LEGACY))
    if mode == PURCHASE_MODE_PACKAGES:
        try:
            package_id = int(data["package_id"])
        except (KeyError, TypeError, ValueError):
            return None
        pkg = db.get_service_package(package_id)
        if pkg is None or not pkg.enabled or pkg.location_id != location_id:
            return None
        final_price = db.resolve_price(pkg.price)
        return (
            location_id,
            location_name,
            pkg.volume_gb,
            pkg.duration_days,
            final_price,
        )

    try:
        volume_gb = int(data["volume_gb"])
        duration_days = int(data["duration_days"])
    except (KeyError, TypeError, ValueError):
        return None
    if volume_gb <= 0 or duration_days <= 0:
        return None

    price = _calc_price_for(db, volume_gb, duration_days, location_id)
    return location_id, location_name, volume_gb, duration_days, price


async def _abort_order_flow(
    message: Message, state: FSMContext, db: Database, bot: Bot | None = None
) -> None:
    """User cancelled mid-purchase — drop the unpaid order row if one was created."""
    data = await state.get_data()
    order_id = int(data.get("order_id") or 0)
    if order_id:
        row = db.get_order(order_id)
        # Only delete while still waiting for payment (not after receipt sent).
        if row is not None and str(row["status"]) == "awaiting_payment":
            if bot is not None:
                buyer = Actor.from_user(message.from_user)
                if buyer is not None:
                    await make_logger(bot, db).log_order_cancelled(
                        order_id=order_id,
                        user=buyer,
                        had_receipt=False,
                    )
            db.delete_order(order_id)
    await state.clear()
    await message.answer(
        texts.CANCELLED, reply_markup=buyer_reply_keyboard(message, db)
    )


async def _show_locations(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    await _clear_plan_selection(state)
    locs = db.list_locations(
        only_enabled=True, exclude_test=True, only_purchase_open=True
    )
    if not locs:
        await _edit_or_answer(callback, texts.NO_LOCATIONS_USER, keyboards.back_to_menu())
        await state.clear()
        return

    # Skip picking location, just pick the first available location
    loc = locs[0]
    await state.update_data(
        location_id=loc.id,
        location_name=loc.name,
        inbound_ids=loc.inbound_ids,
    )
    if db.is_manual_purchase_enabled():
        await _show_packages(callback, state, loc.id, loc.name, db)
    else:
        await _show_volumes(callback, state, loc.name, db)


async def _show_packages(
    callback: CallbackQuery,
    state: FSMContext,
    location_id: int,
    location_name: str,
    db: Database,
) -> None:
    packages = db.list_service_packages(location_id)
    if not packages:
        await _edit_or_answer(
            callback,
            texts.ORDER_NO_PACKAGES,
            keyboards.locations(
                db.list_locations(
                    only_enabled=True,
                    exclude_test=True,
                    only_purchase_open=True,
                )
            ),
        )
        await state.set_state(OrderFlow.picking_location)
        return

    await state.update_data(purchase_mode=PURCHASE_MODE_PACKAGES)
    await state.set_state(OrderFlow.picking_package)
    await _edit_or_answer(
        callback,
        texts.ORDER_PICK_PACKAGE.format(location=escape(location_name)),
        keyboards.service_packages(packages, db),
    )


async def _show_volumes(
    callback: CallbackQuery, state: FSMContext, location_name: str, db: Database
) -> None:
    await state.update_data(purchase_mode=PURCHASE_MODE_LEGACY)
    await state.set_state(OrderFlow.picking_volume)
    await _edit_or_answer(
        callback,
        texts.ORDER_PICK_VOLUME.format(location=escape(location_name)),
        keyboards.volumes(db.get_volume_presets()),
    )


async def _show_durations(
    callback: CallbackQuery,
    state: FSMContext,
    location_name: str,
    volume_gb: int,
    db: Database,
) -> None:
    await state.set_state(OrderFlow.picking_duration)
    await _edit_or_answer(
        callback,
        texts.ORDER_PICK_DURATION.format(
            location=escape(location_name),
            volume=volume_gb,
        ),
        keyboards.durations(db.get_duration_presets()),
    )


async def _show_review(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    mode = str(data.get("purchase_mode", PURCHASE_MODE_LEGACY))
    loc_id = int(data["location_id"])
    vol = int(data["volume_gb"])
    days = int(data["duration_days"])

    if mode == PURCHASE_MODE_PACKAGES:
        pkg_id = int(data.get("package_id") or 0)
        pkg = db.get_service_package(pkg_id) if pkg_id else None
        base_price = pkg.price if pkg else int(data.get("price") or 0)
        back_cb = keyboards.CB_ORDER_BACK_PKG
    else:
        base_price = _calc_base_price_for(db, vol, days, loc_id)
        back_cb = keyboards.CB_ORDER_BACK_DUR

    price = db.resolve_price(base_price)
    await state.update_data(price=price)

    await state.set_state(OrderFlow.reviewing)
    await _edit_or_answer(
        callback,
        texts.ORDER_REVIEW.format(
            location=escape(str(data["location_name"])),
            volume=vol,
            days=days,
            price=texts.format_price(price),
        ),
        keyboards.confirm_order(back_callback=back_cb),
    )


async def _begin_buy_message(message: Message, state: FSMContext, db: Database) -> None:
    """Start buy flow (skips location picking and goes straight to volume/package)."""
    # If we are starting fresh (not renewing), clear state
    data = await state.get_data()
    renew_order_id = data.get("renew_of_order_id")
    await state.clear()
    if renew_order_id:
        await state.update_data(renew_of_order_id=renew_order_id)

    locs = db.list_locations(
        only_enabled=True, exclude_test=True, only_purchase_open=True
    )
    if not locs:
        await message.answer(
            texts.NO_LOCATIONS_USER,
            reply_markup=buyer_reply_keyboard(message, db),
        )
        return
    
    # Pick the first location automatically
    loc = locs[0]
    await state.update_data(
        location_id=loc.id,
        location_name=loc.name,
        inbound_ids=loc.inbound_ids,
    )

    from app.ui_reply import answer_with_inline_keyboard

    if db.is_manual_purchase_enabled():
        packages = db.list_service_packages(loc.id)
        if not packages:
            await message.answer(texts.ORDER_NO_PACKAGES, reply_markup=buyer_reply_keyboard(message, db))
            return
        await state.update_data(purchase_mode=PURCHASE_MODE_PACKAGES)
        await state.set_state(OrderFlow.picking_package)
        await answer_with_inline_keyboard(
            message,
            texts.ORDER_PICK_PACKAGE.format(location=escape(loc.name)),
            keyboards.service_packages(packages, db),
            parse_mode=ParseMode.HTML,
        )
    else:
        await state.update_data(purchase_mode=PURCHASE_MODE_LEGACY)
        await state.set_state(OrderFlow.picking_volume)
        await answer_with_inline_keyboard(
            message,
            texts.ORDER_PICK_VOLUME.format(location=escape(loc.name)),
            keyboards.volumes(db.get_volume_presets()),
            parse_mode=ParseMode.HTML,
        )


# ---------- entry ----------
@router.message(F.text == texts.BTN_BUY, StateFilter(None))
async def msg_start_order(message: Message, state: FSMContext, db: Database) -> None:
    await _begin_buy_message(message, state, db)


@router.callback_query(F.data == keyboards.CB_MAIN_BUY)
async def cb_start_order(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    if isinstance(callback.message, Message):
        await _begin_buy_message(callback.message, state, db)
    await callback.answer()


# ---------- pick location ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_location),
    F.data.startswith(keyboards.CB_LOC_PREFIX),
)
async def cb_pick_location(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    loc_id_str = (callback.data or "").removeprefix(keyboards.CB_LOC_PREFIX)
    try:
        loc_id = int(loc_id_str)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None or not loc.enabled or loc.is_test:
        await callback.answer("این لوکیشن دیگر در دسترس نیست.", show_alert=True)
        await _show_locations(callback, db, state)
        return
    if not loc.purchase_enabled:
        await callback.answer(texts.LOC_PURCHASE_CLOSED_USER, show_alert=True)
        await _show_locations(callback, db, state)
        return

    await _clear_plan_selection(state)
    await state.update_data(
        location_id=loc.id,
        location_name=loc.name,
        inbound_ids=loc.inbound_ids,
    )
    if db.is_manual_purchase_enabled():
        await _show_packages(callback, state, loc.id, loc.name, db)
    else:
        await _show_volumes(callback, state, loc.name, db)
    await callback.answer()


# ---------- pick predefined package (manual purchase mode) ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_package),
    F.data.startswith(keyboards.CB_SVC_PREFIX),
)
async def cb_pick_package(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    raw = (callback.data or "").removeprefix(keyboards.CB_SVC_PREFIX)
    try:
        package_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    pkg = db.get_service_package(package_id)
    data = await state.get_data()
    loc_id = int(data.get("location_id", 0))
    if pkg is None or not pkg.enabled or pkg.location_id != loc_id:
        await callback.answer("این پلن دیگر موجود نیست.", show_alert=True)
        await _show_packages(
            callback, state, loc_id, str(data.get("location_name", "—")), db
        )
        return

    await state.update_data(
        volume_gb=pkg.volume_gb,
        duration_days=pkg.duration_days,
        price=db.resolve_price(pkg.price),
        package_id=pkg.id,
        purchase_mode=PURCHASE_MODE_PACKAGES,
    )
    await _show_review(callback, state, db)
    await callback.answer()


# ---------- pick volume ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_volume),
    F.data == keyboards.CB_VOL_CUSTOM,
)
async def cb_volume_custom(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(OrderFlow.entering_custom_vol)
    await _edit_or_answer(
        callback,
        texts.ORDER_ASK_CUSTOM_VOLUME.format(
            min_gb=texts.CUSTOM_VOLUME_MIN_GB,
            max_gb=texts.CUSTOM_VOLUME_MAX_GB,
        ),
        keyboards.cancel_only(),
    )
    await callback.answer()


@router.callback_query(
    StateFilter(OrderFlow.picking_volume),
    F.data.startswith(keyboards.CB_VOL_PREFIX),
)
async def cb_volume_preset(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    raw = (callback.data or "").removeprefix(keyboards.CB_VOL_PREFIX)
    if raw == "custom":
        return  # handled by the other callback above
    try:
        gb = int(raw)
    except ValueError:
        await callback.answer()
        return
    if gb not in db.get_volume_presets():
        await callback.answer()
        return

    await state.update_data(volume_gb=gb)
    data = await state.get_data()
    await _show_durations(callback, state, str(data["location_name"]), gb, db)
    await callback.answer()


@router.message(StateFilter(OrderFlow.entering_custom_vol))
async def on_custom_volume(message: Message, state: FSMContext, db: Database) -> None:
    raw = (message.text or "").strip()
    try:
        gb = int(raw)
    except ValueError:
        await message.answer(
            texts.ORDER_CUSTOM_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return
    if not (texts.CUSTOM_VOLUME_MIN_GB <= gb <= texts.CUSTOM_VOLUME_MAX_GB):
        await message.answer(
            texts.ORDER_CUSTOM_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return

    await state.update_data(volume_gb=gb)
    await state.set_state(OrderFlow.picking_duration)
    data = await state.get_data()
    await message.answer(
        texts.ORDER_PICK_DURATION.format(
            location=escape(str(data["location_name"])),
            volume=gb,
        ),
        reply_markup=keyboards.durations(db.get_duration_presets()),
    )


# ---------- pick duration ----------
@router.callback_query(
    StateFilter(OrderFlow.picking_duration),
    F.data.startswith(keyboards.CB_DUR_PREFIX),
)
async def cb_pick_duration(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    raw = (callback.data or "").removeprefix(keyboards.CB_DUR_PREFIX)
    try:
        days = int(raw)
    except ValueError:
        await callback.answer()
        return
    if days not in db.get_duration_presets():
        await callback.answer()
        return

    await state.update_data(duration_days=days)
    await _show_review(callback, state, db)
    await callback.answer()


# ---------- review & confirm ----------
@router.callback_query(
    StateFilter(OrderFlow.reviewing),
    F.data == keyboards.CB_ORDER_CONFIRM,
)
async def cb_confirm_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
) -> None:
    data = await state.get_data()
    user = callback.from_user
    if user is None:
        await callback.answer()
        return

    terms = _resolve_order_terms(data, db)
    if terms is None:
        await callback.answer(texts.ORDER_PLAN_CHANGED, show_alert=True)
        loc_id = int(data.get("location_id") or 0)
        if (
            data.get("purchase_mode") == PURCHASE_MODE_PACKAGES
            and loc_id
            and db.list_service_packages(loc_id)
        ):
            await _show_packages(
                callback,
                state,
                loc_id,
                str(data.get("location_name", "—")),
                db,
            )
        else:
            await _show_locations(callback, db, state)
        return

    location_id, location_name, volume_gb, duration_days, price_toman = terms
    await state.update_data(
        location_id=location_id,
        location_name=location_name,
        volume_gb=volume_gb,
        duration_days=duration_days,
        price=price_toman,
    )

    order_id = db.create_order(
        user_id=user.id,
        location_id=location_id,
        location_name=location_name,
        volume_gb=volume_gb,
        duration_days=duration_days,
        price=price_toman,
        renew_of_order_id=data.get("renew_of_order_id"),
    )
    await state.update_data(order_id=order_id)
    await state.set_state(OrderFlow.awaiting_receipt)

    buyer = Actor.from_user(user)
    if buyer is not None:
        await make_logger(bot, db).log_order_awaiting_payment(
            order_id=order_id,
            buyer=buyer,
            location=location_name,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price_toman,
        )

    card_raw = db.get_setting("card_number", "—") or "—"
    card_holder = db.get_setting("card_holder", "—") or "—"

    await _edit_or_answer(
        callback,
        texts.ORDER_PAYMENT_INSTRUCTIONS.format(
            order_id=order_id,
            amount=texts.format_payment_amount(price_toman),
            card_number=escape(texts.format_card_number(card_raw)),
            card_holder=escape(card_holder),
        ),
        keyboards.cancel_only(),
    )
    await callback.answer()


# ---------- back/cancel ----------
@router.message(Command("cancel"), StateFilter(OrderFlow))
async def cmd_cancel_order(
    message: Message, state: FSMContext, db: Database, bot: Bot
) -> None:
    await _abort_order_flow(message, state, db, bot)


@router.callback_query(
    F.data == keyboards.CB_ORDER_CANCEL,
    StateFilter(OrderFlow),
)
async def cb_cancel_anywhere(
    callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot
) -> None:
    if isinstance(callback.message, Message):
        await _abort_order_flow(callback.message, state, db, bot)
    else:
        await state.clear()
    await callback.answer()


@router.callback_query(
    F.data == keyboards.CB_ORDER_BACK_LOC,
    StateFilter(OrderFlow),
)
async def cb_back_to_locations(
    callback: CallbackQuery, state: FSMContext, db: Database, bot: Bot
) -> None:
    if isinstance(callback.message, Message):
        await _abort_order_flow(callback.message, state, db, bot)
    else:
        await state.clear()
    await callback.answer()


@router.callback_query(
    F.data == keyboards.CB_ORDER_BACK_VOL,
    StateFilter(OrderFlow),
)
async def cb_back_to_volumes(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    loc_id = int(data.get("location_id", 0))
    loc_name = str(data.get("location_name", "—"))
    if db.is_manual_purchase_enabled() and loc_id:
        await _show_packages(callback, state, loc_id, loc_name, db)
    else:
        await _show_volumes(callback, state, loc_name, db)
    await callback.answer()


@router.callback_query(
    F.data == keyboards.CB_ORDER_BACK_PKG,
    StateFilter(OrderFlow),
)
async def cb_back_to_packages(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    loc_id = int(data.get("location_id", 0))
    loc_name = str(data.get("location_name", "—"))
    await _show_packages(callback, state, loc_id, loc_name, db)
    await callback.answer()


@router.callback_query(
    F.data == keyboards.CB_ORDER_BACK_DUR,
    StateFilter(OrderFlow),
)
async def cb_back_to_duration(callback: CallbackQuery, state: FSMContext, db: Database) -> None:
    data = await state.get_data()
    if data.get("purchase_mode") == PURCHASE_MODE_PACKAGES:
        loc_id = int(data.get("location_id", 0))
        loc_name = str(data.get("location_name", "—"))
        await _show_packages(callback, state, loc_id, loc_name, db)
        await callback.answer()
        return
    loc_name = str(data.get("location_name", "—"))
    vol_gb = int(data.get("volume_gb", 0))
    await _show_durations(callback, state, loc_name, vol_gb, db)
    await callback.answer()


# ---------- receipt photo ----------
@router.message(StateFilter(OrderFlow.awaiting_receipt), F.photo)
async def on_receipt_photo(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    data = await state.get_data()
    order_id = int(data.get("order_id", 0))
    if not order_id or message.photo is None:
        await _abort_order_flow(message, state, db, bot)
        return

    # Highest-resolution photo size is last.
    file_id = message.photo[-1].file_id
    db.set_order_screenshot(order_id, file_id, new_status="awaiting_review")

    await state.clear()
    await message.answer(
        texts.ORDER_RECEIPT_RECEIVED,
        reply_markup=buyer_reply_keyboard(message, db),
    )

    user = message.from_user
    full_name = "—"
    user_id = 0
    if user is not None:
        full_name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
        user_id = user.id

    caption = texts.NEW_RECEIPT_NOTIFY.format(
        order_id=order_id,
        user_id=user_id,
        full_name=escape(full_name),
        location=escape(str(data["location_name"])),
        volume=int(data["volume_gb"]),
        days=int(data["duration_days"]),
        price=texts.format_price(int(data["price"])),
    )
    review_kb = keyboards.admin_review(order_id=order_id, user_id=user_id)

    buyer = Actor.from_user(user)
    if buyer is not None:
        await make_logger(bot, db).log_receipt_uploaded(
            order_id=order_id,
            buyer=buyer,
            photo_file_id=file_id,
            location=str(data["location_name"]),
            volume_gb=int(data["volume_gb"]),
            duration_days=int(data["duration_days"]),
            price=int(data["price"]),
        )

    for admin_id in settings.admin_ids:
        try:
            sent = await bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=caption,
                reply_markup=review_kb,
            )
            if sent:
                db.add_admin_receipt_message(order_id, admin_id, sent.message_id)
        except Exception:  # noqa: BLE001 — admin may have blocked the bot
            log.exception("Failed to send receipt to admin %s", admin_id)


@router.message(StateFilter(OrderFlow.awaiting_receipt))
async def on_receipt_non_photo(message: Message) -> None:
    await message.answer(texts.ORDER_RECEIPT_NEED_PHOTO)
