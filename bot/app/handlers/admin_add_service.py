"""Admin wizard: add a predefined service package (buttons + price input)."""

from __future__ import annotations

from html import escape

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import SERVICES
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_panel import send_services
from app.ui_reply import answer_with_inline_keyboard

router = Router(name="admin_add_service")

_DAYS_MAX = 3650


class AdminAddServiceFlow(StatesGroup):
    picking_location = State()
    picking_volume = State()
    waiting_custom_volume = State()
    picking_duration = State()
    waiting_custom_duration = State()
    waiting_price = State()


def _add_service_error_text(reason: str) -> str:
    return {
        "not_found": texts.ADD_SERVICE_NOT_FOUND,
        "invalid": texts.ADD_SERVICE_INVALID,
        "duplicate": texts.ADD_SERVICE_DUPLICATE,
        "test_location": texts.ADD_SERVICE_TEST_LOC,
        "disabled": texts.ADD_SERVICE_DISABLED,
    }.get(reason, texts.ADD_SERVICE_INVALID)


def _parse_positive_int(raw: str) -> int | None:
    s = (raw or "").strip().replace(",", "").replace("،", "")
    if not s.isdigit():
        return None
    value = int(s)
    return value if value > 0 else None


def _parse_price(raw: str) -> int | None:
    s = (raw or "").strip().replace(",", "").replace("،", "")
    if not s.isdigit():
        return None
    return int(s)


async def _commit_package(
    message: Message, state: FSMContext, db: Database, settings: Settings
) -> None:
    data = await state.get_data()
    try:
        loc_id = int(data["location_id"])
        volume_gb = int(data["volume_gb"])
        duration_days = int(data["duration_days"])
        price = int(data["price"])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await message.answer(texts.ORDER_INCOMPLETE)
        return

    ok, reason, pkg_id = db.add_service_package(
        loc_id, volume_gb, duration_days, price
    )
    await state.clear()
    if not ok:
        await message.answer(_add_service_error_text(reason))
        return

    loc = db.get_location(loc_id)
    loc_name = escape(loc.name) if loc else "—"
    await message.answer(
        texts.ADD_SERVICE_OK.format(
            id=pkg_id or 0,
            loc_id=loc_id,
            volume=volume_gb,
            days=duration_days,
            price=texts.format_price(price),
        )
        + f"\n📍 {loc_name}",
    )
    user = message.from_user
    if user is not None:
        await send_services(message, db, settings, user.id, edit_in_place=False)


def _eligible_locations(db: Database):
    return db.list_locations(only_enabled=True, exclude_test=True)


async def _prompt_location(message: Message, state: FSMContext, db: Database) -> None:
    locs = _eligible_locations(db)
    if not locs:
        await state.clear()
        await message.answer(texts.ADD_SERVICE_WIZARD_NO_LOCATIONS)
        return
    await state.set_state(AdminAddServiceFlow.picking_location)
    await answer_with_inline_keyboard(
        message,
        texts.ADD_SERVICE_WIZARD_LOCATION,
        keyboards.admin_add_service_locations(locs),
    )


async def _prompt_volume(
    message: Message, state: FSMContext, db: Database, *, location_name: str
) -> None:
    await state.set_state(AdminAddServiceFlow.picking_volume)
    await answer_with_inline_keyboard(
        message,
        texts.ADD_SERVICE_WIZARD_VOLUME.format(location=escape(location_name)),
        keyboards.admin_add_service_volumes(db.get_volume_presets()),
    )


async def _prompt_duration(
    message: Message,
    state: FSMContext,
    db: Database,
    *,
    location_name: str,
    volume_gb: int,
) -> None:
    await state.set_state(AdminAddServiceFlow.picking_duration)
    await answer_with_inline_keyboard(
        message,
        texts.ADD_SERVICE_WIZARD_DURATION.format(
            location=escape(location_name),
            volume=volume_gb,
        ),
        keyboards.admin_add_service_durations(db.get_duration_presets()),
    )


async def _prompt_price(
    message: Message,
    state: FSMContext,
    *,
    location_name: str,
    volume_gb: int,
    duration_days: int,
) -> None:
    await state.set_state(AdminAddServiceFlow.waiting_price)
    await message.answer(
        texts.ADD_SERVICE_WIZARD_PRICE.format(
            location=escape(location_name),
            volume=volume_gb,
            days=duration_days,
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_ADD_SVC_BACK_DUR
        ),
    )


async def start_add_service_wizard(
    message: Message, state: FSMContext, db: Database
) -> None:
    """Start add-plan wizard; always clears a previous unfinished flow."""
    await state.clear()
    await _prompt_location(message, state, db)


@router.callback_query(F.data == keyboards.CB_ADM_ADD_SVC)
async def cb_add_service_start(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await start_add_service_wizard(callback.message, state, db)
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminAddServiceFlow))
async def add_service_cancel_msg(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    if message.from_user is None:
        return
    await state.clear()
    await message.answer(texts.CANCELLED)
    await send_services(message, db, settings, message.from_user.id)


@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminAddServiceFlow)
)
async def add_service_cancel_cb(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await state.clear()
    await send_services(
        callback.message,
        db,
        settings,
        callback.from_user.id,
        edit_in_place=False,
    )
    await callback.answer(texts.CANCELLED)


# ---------- location ----------
@router.callback_query(
    StateFilter(AdminAddServiceFlow.picking_location),
    F.data.startswith(keyboards.CB_ADM_ADD_SVC_LOC_PREFIX),
)
async def cb_pick_location(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ADD_SVC_LOC_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    loc = db.get_location(loc_id)
    if loc is None or loc.is_test or not loc.enabled:
        await callback.answer("لوکیشن در دسترس نیست.", show_alert=True)
        return

    await state.update_data(location_id=loc_id, location_name=loc.name)
    await callback.answer()
    await _prompt_volume(callback.message, state, db, location_name=loc.name)


# ---------- volume ----------
@router.callback_query(
    StateFilter(AdminAddServiceFlow.picking_volume),
    F.data.startswith(keyboards.CB_ADM_ADD_SVC_VOL_PREFIX),
)
async def cb_pick_volume_preset(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ADD_SVC_VOL_PREFIX)
    try:
        volume_gb = int(raw)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    await state.update_data(volume_gb=volume_gb)
    await callback.answer()
    await _prompt_duration(
        callback.message,
        state,
        db,
        location_name=location_name,
        volume_gb=volume_gb,
    )


@router.callback_query(
    StateFilter(AdminAddServiceFlow.picking_volume),
    F.data == keyboards.CB_ADM_ADD_SVC_VOL_CUSTOM,
)
async def cb_pick_volume_custom(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    await state.set_state(AdminAddServiceFlow.waiting_custom_volume)
    await callback.message.answer(
        texts.ADD_SERVICE_WIZARD_VOLUME_CUSTOM.format(
            location=escape(location_name),
            min_gb=texts.CUSTOM_VOLUME_MIN_GB,
            max_gb=texts.CUSTOM_VOLUME_MAX_GB,
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_ADD_SVC_BACK_LOC
        ),
    )
    await callback.answer()


@router.message(StateFilter(AdminAddServiceFlow.waiting_custom_volume))
async def msg_custom_volume(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        await state.clear()
        return

    gb = _parse_positive_int(message.text or "")
    if gb is None or not (
        texts.CUSTOM_VOLUME_MIN_GB <= gb <= texts.CUSTOM_VOLUME_MAX_GB
    ):
        await message.answer(
            texts.ADD_SERVICE_WIZARD_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            )
        )
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    await state.update_data(volume_gb=gb)
    await _prompt_duration(
        message, state, db, location_name=location_name, volume_gb=gb
    )


@router.callback_query(
    StateFilter(AdminAddServiceFlow),
    F.data == keyboards.CB_ADM_ADD_SVC_BACK_LOC,
)
async def cb_back_to_location(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await callback.answer()
    await _prompt_location(callback.message, state, db)


# ---------- duration ----------
@router.callback_query(
    StateFilter(AdminAddServiceFlow.picking_duration),
    F.data.startswith(keyboards.CB_ADM_ADD_SVC_DUR_PREFIX),
)
async def cb_pick_duration_preset(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_ADD_SVC_DUR_PREFIX)
    try:
        duration_days = int(raw)
    except ValueError:
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    try:
        volume_gb = int(data["volume_gb"])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await callback.answer("اطلاعات ناقص است.", show_alert=True)
        return

    await state.update_data(duration_days=duration_days)
    await callback.answer()
    await _prompt_price(
        callback.message,
        state,
        location_name=location_name,
        volume_gb=volume_gb,
        duration_days=duration_days,
    )


@router.callback_query(
    StateFilter(AdminAddServiceFlow.picking_duration),
    F.data == keyboards.CB_ADM_ADD_SVC_DUR_CUSTOM,
)
async def cb_pick_duration_custom(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    try:
        volume_gb = int(data["volume_gb"])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await callback.answer("اطلاعات ناقص است.", show_alert=True)
        return

    await state.set_state(AdminAddServiceFlow.waiting_custom_duration)
    await callback.message.answer(
        texts.ADD_SERVICE_WIZARD_DURATION_CUSTOM.format(
            location=escape(location_name),
            volume=volume_gb,
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_ADD_SVC_BACK_VOL
        ),
    )
    await callback.answer()


@router.message(StateFilter(AdminAddServiceFlow.waiting_custom_duration))
async def msg_custom_duration(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        await state.clear()
        return

    days = _parse_positive_int(message.text or "")
    if days is None or days > _DAYS_MAX:
        await message.answer(texts.ADD_SERVICE_WIZARD_DURATION_INVALID)
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    try:
        volume_gb = int(data["volume_gb"])
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await message.answer(texts.ORDER_INCOMPLETE)
        return

    await state.update_data(duration_days=days)
    await _prompt_price(
        message,
        state,
        location_name=location_name,
        volume_gb=volume_gb,
        duration_days=days,
    )


@router.callback_query(
    StateFilter(AdminAddServiceFlow),
    F.data == keyboards.CB_ADM_ADD_SVC_BACK_VOL,
)
async def cb_back_to_volume(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    await callback.answer()
    await _prompt_volume(callback.message, state, db, location_name=location_name)


@router.callback_query(
    StateFilter(AdminAddServiceFlow),
    F.data == keyboards.CB_ADM_ADD_SVC_BACK_DUR,
)
async def cb_back_to_duration(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, SERVICES):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    data = await state.get_data()
    location_name = str(data.get("location_name") or "—")
    try:
        volume_gb = int(data["volume_gb"])
    except (KeyError, TypeError, ValueError):
        await callback.answer()
        await _prompt_location(callback.message, state, db)
        return

    await callback.answer()
    await _prompt_duration(
        callback.message,
        state,
        db,
        location_name=location_name,
        volume_gb=volume_gb,
    )


# ---------- price ----------
@router.message(StateFilter(AdminAddServiceFlow.waiting_price))
async def msg_price(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        await state.clear()
        return

    price = _parse_price(message.text or "")
    if price is None:
        await message.answer(texts.ADD_SERVICE_WIZARD_PRICE_INVALID)
        return

    await state.update_data(price=price)
    await _commit_package(message, state, db, settings)
