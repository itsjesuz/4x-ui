"""Admin wizard: manually provision a client (buttons + numeric input)."""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message

from app import keyboards, texts
from app.admin_perms import ORDERS_MANAGE
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.admin_panel import send_admin_home
from app.handlers.admin_ui_helpers import admin_edit_or_answer
from app.logs import Actor, make_logger
from app.xui import XuiClient, XuiError, build_client_email

router = Router(name="admin_add_client")
log = logging.getLogger(__name__)

_DAYS_MIN = 1
_DAYS_MAX = 3650
_SKIP_USER_TEXT = frozenset({"-", "—", "skip", "none"})
_WIZARD_MSG_IDS_KEY = "wizard_msg_ids"


class AdminAddClientFlow(StatesGroup):
    waiting_user_id = State()
    waiting_volume = State()
    waiting_days = State()
    picking_location = State()


def _calc_order_price(
    db: Database, volume_gb: int, duration_days: int, location_id: int
) -> int:
    base, per_gb, per_day = db.get_pricing_for_location(location_id)
    base_price = texts.calc_price(volume_gb, duration_days, base, per_gb, per_day)
    return db.resolve_price(base_price)


async def _track_wizard_message(state: FSMContext, sent: Message) -> None:
    data = await state.get_data()
    ids: list[int] = list(data.get(_WIZARD_MSG_IDS_KEY) or [])
    ids.append(sent.message_id)
    await state.update_data(**{_WIZARD_MSG_IDS_KEY: ids})


async def _wizard_reply(
    message: Message,
    state: FSMContext,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> Message:
    sent = await message.answer(text, reply_markup=reply_markup)
    await _track_wizard_message(state, sent)
    return sent


async def _delete_wizard_messages(
    bot: Bot, chat_id: int, message_ids: list[int]
) -> None:
    for mid in message_ids:
        try:
            await bot.delete_message(chat_id=chat_id, message_id=mid)
        except Exception:  # noqa: BLE001 — already gone or too old
            log.debug("Could not delete wizard message %s in %s", mid, chat_id)


def _parse_positive_int(raw: str) -> int | None:
    s = (raw or "").strip()
    if not s.isdigit():
        return None
    value = int(s)
    return value if value > 0 else None


async def _prompt_volume(message: Message, state: FSMContext) -> None:
    await state.set_state(AdminAddClientFlow.waiting_volume)
    await _wizard_reply(
        message,
        state,
        texts.ADMIN_ADD_CLIENT_VOLUME_PROMPT.format(
            min_gb=texts.CUSTOM_VOLUME_MIN_GB,
            max_gb=texts.CUSTOM_VOLUME_MAX_GB,
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_HOME
        ),
    )


async def _start_add_client(
    message: Message, state: FSMContext, db: Database
) -> None:
    from app.ui_reply import answer_with_inline_keyboard

    await state.clear()
    await state.set_state(AdminAddClientFlow.waiting_user_id)
    sent = await answer_with_inline_keyboard(
        message,
        texts.ADMIN_ADD_CLIENT_USER_PROMPT,
        keyboards.admin_add_client_user_keyboard(),
    )
    await _track_wizard_message(state, sent)


@router.callback_query(F.data == keyboards.CB_ADM_ADD_CLIENT)
async def cb_admin_add_client_start(
    callback: CallbackQuery, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return
    await _start_add_client(callback.message, state, db)
    await callback.answer()


async def _cancel_wizard_and_cleanup(
    event: Message | CallbackQuery, state: FSMContext, bot: Bot
) -> tuple[int | None, list[int]]:
    data = await state.get_data()
    msg_ids: list[int] = list(data.get(_WIZARD_MSG_IDS_KEY) or [])
    chat_id: int | None = None

    if isinstance(event, CallbackQuery):
        if isinstance(event.message, Message):
            chat_id = event.message.chat.id
            if event.message.message_id not in msg_ids:
                msg_ids.append(event.message.message_id)
    elif isinstance(event, Message):
        chat_id = event.chat.id

    await state.clear()
    if chat_id is not None and msg_ids:
        await _delete_wizard_messages(bot, chat_id, msg_ids)
    return chat_id, msg_ids


@router.callback_query(
    F.data == keyboards.CB_ADM_HOME, StateFilter(AdminAddClientFlow)
)
async def add_client_back_home(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_MANAGE):
        return
    await _cancel_wizard_and_cleanup(callback, state, bot)
    if callback.from_user is None or not isinstance(callback.message, Message):
        await callback.answer()
        return
    await send_admin_home(
        callback.message,
        settings,
        db,
        admin_user_id=callback.from_user.id,
        edit_in_place=False,
    )
    await callback.answer()


@router.message(Command("cancel"), StateFilter(AdminAddClientFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(AdminAddClientFlow)
)
async def add_client_flow_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    bot: Bot,
    settings: Settings,
    db: Database,
) -> None:
    await _cancel_wizard_and_cleanup(event, state, bot)

    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
    else:
        uid = event.from_user.id if event.from_user else None
        markup = (
            keyboards.admin_reply_keyboard(uid, settings, db)
            if uid is not None
            else None
        )
        await event.answer(texts.CANCELLED, reply_markup=markup)
        try:
            await event.delete()
        except Exception:  # noqa: BLE001
            pass


@router.message(StateFilter(AdminAddClientFlow.waiting_user_id))
async def add_client_user_id(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    user_id = None
    if getattr(message, "forward_origin", None) and getattr(message.forward_origin, "type", None) == "user":
        user_id = getattr(getattr(message.forward_origin, "sender_user", None), "id", None)
    
    if not user_id and getattr(message, "forward_from", None):
        user_id = getattr(message.forward_from, "id", None)

    if not user_id:
        raw = (message.text or "").strip()
        user_id = _parse_positive_int(raw)

    if user_id is None:
        await _wizard_reply(message, state, texts.ADMIN_ADD_CLIENT_USER_INVALID)
        return

    try:
        chat = await message.bot.get_chat(user_id)
        username = chat.username
        first_name = chat.first_name
        last_name = chat.last_name
    except Exception:
        existing = db.get_user(user_id)
        if existing:
            username = existing["username"]
            first_name = existing["first_name"]
            last_name = existing["last_name"]
        else:
            username = None
            first_name = None
            last_name = None

    db.upsert_user(
        user_id=user_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        lang_code=None,
    )
    await state.update_data(target_user_id=user_id)
    await _prompt_volume(message, state)


@router.message(StateFilter(AdminAddClientFlow.waiting_volume))
async def add_client_volume(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    gb = _parse_positive_int(message.text or "")
    if gb is None or not (
        texts.CUSTOM_VOLUME_MIN_GB <= gb <= texts.CUSTOM_VOLUME_MAX_GB
    ):
        await _wizard_reply(
            message,
            state,
            texts.ADMIN_ADD_CLIENT_VOLUME_INVALID.format(
                min_gb=texts.CUSTOM_VOLUME_MIN_GB,
                max_gb=texts.CUSTOM_VOLUME_MAX_GB,
            ),
        )
        return

    await state.update_data(volume_gb=gb)
    await state.set_state(AdminAddClientFlow.waiting_days)
    await _wizard_reply(
        message,
        state,
        texts.ADMIN_ADD_CLIENT_DAYS_PROMPT,
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_HOME
        ),
    )


@router.message(StateFilter(AdminAddClientFlow.waiting_days))
async def add_client_days(
    message: Message, state: FSMContext, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        await state.clear()
        return

    days = _parse_positive_int(message.text or "")
    if days is None or not (_DAYS_MIN <= days <= _DAYS_MAX):
        await _wizard_reply(
            message,
            state,
            texts.ADMIN_ADD_CLIENT_DAYS_INVALID.format(
                min_days=_DAYS_MIN, max_days=_DAYS_MAX
            ),
        )
        return

    locs = db.list_locations(only_enabled=True, exclude_test=True)
    if not locs:
        chat_id = message.chat.id
        msg_ids = list((await state.get_data()).get(_WIZARD_MSG_IDS_KEY) or [])
        await state.clear()
        if msg_ids:
            await _delete_wizard_messages(bot, chat_id, msg_ids)
        await message.answer(texts.ADMIN_ADD_CLIENT_NO_LOCATIONS)
        return

    await state.update_data(duration_days=days)
    
    loc = locs[0]
    await state.update_data(location_id=loc.id)
    data = await state.get_data()

    target_user_id = data.get("target_user_id")
    if target_user_id is not None:
        try:
            target_user_id = int(target_user_id)
        except (TypeError, ValueError):
            target_user_id = None

    if not loc.inbound_ids:
        await message.answer("inbound برای این لوکیشن تنظیم نشده.")
        return

    await admin_edit_or_answer(
        message,
        texts.ADMIN_ADD_CLIENT_PROVISIONING,
        edit_in_place=True,
    )
    
    admin_id = message.from_user.id
    volume_gb = int(data["volume_gb"])
    duration_days = int(data["duration_days"])

    price = _calc_order_price(db, volume_gb, duration_days, loc.id)
    panel_only = target_user_id is None
    if panel_only:
        db.upsert_user(
            user_id=admin_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            lang_code=message.from_user.language_code,
        )
        order_user_id = admin_id
    else:
        order_user_id = target_user_id

    order_id = db.create_order(
        user_id=order_user_id,
        location_id=loc.id,
        location_name=loc.name,
        volume_gb=volume_gb,
        duration_days=duration_days,
        price=price,
        admin_manual_only=panel_only,
    )
    panel_email = build_client_email(order_id, is_test=False)
    tg_user_id = target_user_id if target_user_id is not None else admin_id

    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            result = await xui.provision(
                email=panel_email,
                volume_gb=volume_gb,
                duration_days=duration_days,
                inbound_ids=loc.inbound_ids,
                tg_user_id=tg_user_id,
            )
    except XuiError as exc:
        log.warning("Admin manual provision failed order %s: %s", order_id, exc)
        db.set_order_status(order_id, "failed", admin_id=admin_id)
        await state.clear()
        order_hint = f" (سفارش <code>#{order_id}</code>)"
        await message.answer(
            texts.ADMIN_ADD_CLIENT_FAILED.format(
                order_hint=order_hint, error=escape(str(exc))
            )
        )
        return
    except Exception as exc:  # noqa: BLE001
        log.exception("Unexpected admin manual provision order %s", order_id)
        db.set_order_status(order_id, "failed", admin_id=admin_id)
        await state.clear()
        order_hint = f" (سفارش <code>#{order_id}</code>)"
        await message.answer(
            texts.ADMIN_ADD_CLIENT_FAILED.format(
                order_hint=order_hint, error=escape(str(exc))
            )
        )
        return

    db.set_order_provisioned(
        order_id=order_id,
        email=result.email,
        sub_id=result.sub_id,
        client_uuid=result.client_uuid,
        sub_links=result.sub_links,
    )
    await state.clear()

    sub_url = loc.render_sub_url(result.sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url,
        sub_links=[escape(x) for x in result.sub_links],
    )

    if not panel_only:
        await message.answer(
            texts.ADMIN_ADD_CLIENT_OK.format(
                order_id=order_id,
                user_id=target_user_id,
                location=escape(loc.name),
                volume=volume_gb,
                days=duration_days,
                panel_email=escape(result.email),
                configs_block=configs_block,
            ),
            reply_markup=keyboards.admin_add_client_done_keyboard(),
        )
        try:
            await bot.send_message(
                target_user_id,
                texts.ADMIN_ADD_CLIENT_USER_NOTIFY.format(
                    order_id=order_id,
                    location=escape(loc.name),
                    volume=volume_gb,
                    days=duration_days,
                    configs_block=configs_block,
                ),
            )
        except Exception:  # noqa: BLE001
            log.debug(
                "Could not notify user %s about manual provision", target_user_id
            )
    else:
        await message.answer(
            texts.ADMIN_ADD_CLIENT_OK_PANEL_ONLY.format(
                order_id=order_id,
                location=escape(loc.name),
                volume=volume_gb,
                days=duration_days,
                panel_email=escape(result.email),
                configs_block=configs_block,
            ),
            reply_markup=keyboards.admin_add_client_done_keyboard(),
        )

    admin = Actor.from_user(message.from_user)
    if admin is not None:
        await make_logger(bot, db).log_manual_client_created(
            order_id=order_id,
            admin=admin,
            location=loc.name,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            panel_email=result.email,
            buyer_id=target_user_id,
        )
