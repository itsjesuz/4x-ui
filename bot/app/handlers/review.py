"""Admin payment-review flow.

When an admin clicks Accept on a payment receipt:
  1) We re-check the order is still 'awaiting_review'.
  2) Look up the associated Location's panel credentials.
  3) Call XuiClient.provision() to create the client and fetch sub links.
  4) Notify the user with the links, save the result in the order row.

Decline flow: preset inline buttons or custom text (FSM), then notify buyer.
"""

from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, User

from app import keyboards, texts
from app.admin_perms import ORDERS_REVIEW
from app.config import Settings
from app.db import TEST_VOLUME_BYTES, Database
from app.handlers.admin_helpers import guard_admin_callback, guard_admin_message
from app.handlers.review_notify import clear_admin_receipt_buttons
from app.logs import Actor, make_logger
from app.xui import XuiClient, XuiError, build_client_email, test_expiry_time_ms


router = Router(name="review")
log = logging.getLogger(__name__)


class DeclineFlow(StatesGroup):
    waiting_reason = State()


def _status_label(status: str) -> str:
    return texts.STATUS_BADGE.get(status, status)


async def _edit_decline_prompt(
    bot: Bot,
    *,
    chat_id: int,
    message_id: int,
    text: str,
) -> None:
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=None,
            parse_mode=ParseMode.HTML,
        )
    except TelegramBadRequest:
        pass


async def _reject_if_not_reviewable(
    callback: CallbackQuery, db: Database, order_id: int
) -> bool:
    """Return True if order is still awaiting_review; else alert and return False."""
    order = db.get_order(order_id)
    if order is None:
        await callback.answer("سفارش پیدا نشد.", show_alert=True)
        return False
    if order["status"] != "awaiting_review":
        await callback.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(order["status"])),
            show_alert=True,
        )
        return False
    return True




# ---------- Accept ----------
@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_ACCEPT_PREFIX))
async def cb_accept_order(
    callback: CallbackQuery,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_ACCEPT_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    if not await _reject_if_not_reviewable(callback, db, order_id):
        return

    order = db.get_order(order_id)
    assert order is not None
    admin_id = callback.from_user.id
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False

    if not db.claim_order_review(order_id, "approved", admin_id):
        order = db.get_order(order_id)
        st = order["status"] if order else "—"
        await callback.answer(
            texts.REVIEW_ALREADY.format(status=_status_label(str(st))),
            show_alert=True,
        )
        return

    await callback.answer(texts.REVIEW_ACCEPTED)
    await clear_admin_receipt_buttons(
        bot,
        db,
        order_id,
        acting_admin_id=admin_id,
        action="تأیید شد",
    )

    location = db.get_location(int(order["location_id"]))
    if location is None or not location.inbound_ids:
        err = "لوکیشن مرتبط با این سفارش حذف شده یا inbound ندارد."
        db.set_order_status(order_id, "failed", admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order["user_id"]),
                location=str(order["location_name"]),
                volume_gb=int(order["volume_gb"]),
                duration_days=int(order["duration_days"]),
                price=int(order["price"]),
                error=err,
                is_test=is_test,
            )
        await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_ERR.format(error=err))
        await bot.send_message(int(order["user_id"]), texts.ORDER_PROVISION_FAILED_USER)
        return

    renew_of_order_id = order['renew_of_order_id']
    is_renewal = bool(renew_of_order_id)
    parent_order = None
    if is_renewal:
        parent_order = db.get_order(int(renew_of_order_id))
        if parent_order and parent_order['xui_email']:
            email = parent_order['xui_email']
        else:
            is_renewal = False
            email = build_client_email(order_id, is_test=is_test)
    else:
        email = build_client_email(order_id, is_test=is_test)

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            if is_renewal:
                await xui.renew_client(
                    email=email,
                    volume_gb=int(order['volume_gb']),
                    duration_days=int(order['duration_days']),
                    is_test=is_test,
                )
                
                import json
                sub_id = parent_order['xui_sub_id']
                client_uuid = parent_order['xui_client_uuid']
                try:
                    sub_links = json.loads(parent_order['sub_links'] or '[]')
                except Exception:
                    sub_links = []
                
                if not sub_links and sub_id:
                    try:
                        sub_links = await xui.get_sub_links(sub_id)
                    except Exception:
                        pass
                
                from app.xui import ProvisionedClient
                result = ProvisionedClient(
                    email=email,
                    sub_id=sub_id,
                    client_uuid=client_uuid,
                    sub_links=sub_links,
                    raw_get_response=None,
                )
            else:
                result = await xui.provision(
                    email=email,
                    volume_gb=int(order['volume_gb']),
                    duration_days=int(order['duration_days']),
                    inbound_ids=location.inbound_ids,
                    tg_user_id=int(order['user_id']),
                    total_bytes=TEST_VOLUME_BYTES if is_test else None,
                    expiry_time_ms=test_expiry_time_ms() if is_test else None,
                )
    except XuiError as exc:
        log.warning('Provisioning failed for order %s: %s', order_id, exc)
        db.set_order_status(order_id, 'failed', admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order['user_id']),
                location=str(order['location_name']),
                volume_gb=int(order['volume_gb']),
                duration_days=int(order['duration_days']),
                price=int(order['price']),
                error=str(exc),
                is_test=is_test,
            )
        await bot.send_message(
            callback.from_user.id,
            texts.REVIEW_PROVISION_ERR.format(error=escape(str(exc))),
        )
        await bot.send_message(int(order['user_id']), texts.ORDER_PROVISION_FAILED_USER)
        return
    except Exception as exc:  # noqa: BLE001 — any other failure (network, etc.)
        log.exception('Unexpected provisioning error for order %s', order_id)
        db.set_order_status(order_id, 'failed', admin_id=callback.from_user.id)
        admin = Actor.from_user(callback.from_user)
        if admin is not None:
            await make_logger(bot, db).log_order_provision_failed(
                order_id=order_id,
                admin=admin,
                buyer_id=int(order['user_id']),
                location=str(order['location_name']),
                volume_gb=int(order['volume_gb']),
                duration_days=int(order['duration_days']),
                price=int(order['price']),
                error=str(exc),
                is_test=is_test,
            )
        await bot.send_message(
            callback.from_user.id,
            texts.REVIEW_PROVISION_ERR.format(error=escape(str(exc))),
        )
        await bot.send_message(int(order['user_id']), texts.ORDER_PROVISION_FAILED_USER)
        return

    if is_renewal:
        db.update_order_plan(
            int(renew_of_order_id),
            volume_gb=int(parent_order["volume_gb"]) + int(order["volume_gb"]),
            duration_days=int(parent_order["duration_days"]) + int(order["duration_days"]),
        )
        db.set_order_status(order_id, 'completed_renewal', admin_id=callback.from_user.id)
    else:
        db.set_order_provisioned(
            order_id=order_id,
            email=result.email,
            sub_id=result.sub_id,
            client_uuid=result.client_uuid,
            sub_links=result.sub_links,
        )

    sub_url = location.render_sub_url(result.sub_id)
    configs_block = texts.format_configs_block(
        sub_url=sub_url,
        sub_links=[escape(x) for x in result.sub_links],
    )

    try:
        if is_renewal:
            await bot.send_message(
                int(order["user_id"]),
                texts.ORDER_RENEWED_NOTIFY.format(
                    order_id=int(renew_of_order_id),
                    location=escape(str(order["location_name"])),
                    volume=int(order["volume_gb"]),
                    days=int(order["duration_days"]),
                ),
            )
        else:
            await bot.send_message(
                int(order["user_id"]),
                texts.ORDER_PROVISIONED_NOTIFY.format(
                    order_id=order_id,
                    location=escape(str(order["location_name"])),
                    volume=int(order["volume_gb"]),
                    days=int(order["duration_days"]),
                    configs_block=configs_block,
                ),
            )
    except Exception:  # noqa: BLE001 — user may have blocked the bot
        log.exception("Failed to notify user %s about provisioned order %s",
                      order["user_id"], order_id)

    admin = Actor.from_user(callback.from_user)
    if admin is not None:
        await make_logger(bot, db).log_order_accepted(
            order_id=order_id,
            admin=admin,
            buyer_id=int(order["user_id"]),
            location=str(order["location_name"]),
            volume_gb=int(order["volume_gb"]),
            duration_days=int(order["duration_days"]),
            price=int(order["price"]),
            panel_email=result.email,
            is_test=is_test,
        )

    await bot.send_message(callback.from_user.id, texts.REVIEW_PROVISION_OK)


# ---------- Decline ----------
async def _apply_decline(
    *,
    order_id: int,
    reason: str,
    admin_user: User,
    bot: Bot,
    db: Database,
    prompt_chat_id: int | None = None,
    prompt_message_id: int | None = None,
    error_reply: Message | None = None,
) -> bool:
    """Decline order and notify buyer. Returns True on success."""
    order = db.get_order(order_id)
    if order is None:
        if error_reply is not None:
            await error_reply.answer("سفارش پیدا نشد.")
        return False
    if order["status"] != "awaiting_review":
        if error_reply is not None:
            await error_reply.answer(
                texts.REVIEW_ALREADY.format(status=_status_label(order["status"]))
            )
        return False

    user_id = int(order["user_id"])
    admin_id = admin_user.id
    if not db.claim_order_review(
        order_id, "declined", admin_id, decline_reason=reason
    ):
        order = db.get_order(order_id)
        st = order["status"] if order else "—"
        if error_reply is not None:
            await error_reply.answer(
                texts.REVIEW_ALREADY.format(status=_status_label(str(st)))
            )
        return False

    await clear_admin_receipt_buttons(
        bot,
        db,
        order_id,
        acting_admin_id=admin_id,
        action="رد شد",
    )
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
    admin = Actor.from_user(admin_user)
    if admin is not None:
        await make_logger(bot, db).log_order_declined(
            order_id=order_id,
            admin=admin,
            buyer_id=user_id,
            location=str(order["location_name"]),
            volume_gb=int(order["volume_gb"]),
            duration_days=int(order["duration_days"]),
            price=int(order["price"]),
            reason=reason,
            is_test=is_test,
        )

    if prompt_chat_id is not None and prompt_message_id is not None:
        await _edit_decline_prompt(
            bot,
            chat_id=prompt_chat_id,
            message_id=prompt_message_id,
            text=texts.REVIEW_DECLINE_DONE.format(order_id=order_id),
        )
    elif error_reply is not None:
        await error_reply.answer(texts.REVIEW_DECLINE_SENT)

    try:
        await bot.send_message(
            user_id,
            texts.ORDER_DECLINED_NOTIFY.format(
                order_id=order_id,
                reason=escape(reason),
            ),
        )
    except Exception:  # noqa: BLE001
        log.exception(
            "Failed to notify user %s about declined order %s",
            user_id,
            order_id,
        )
    return True


@router.callback_query(
    F.data.startswith(keyboards.CB_ADMIN_DECLINE_PREFIX)
    & ~F.data.startswith(keyboards.CB_ADMIN_DECLINE_PRESET_PREFIX)
    & ~F.data.startswith(keyboards.CB_ADMIN_DECLINE_CANCEL_PREFIX)
)
async def cb_decline_order(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    settings: Settings,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADMIN_DECLINE_PREFIX)
    try:
        order_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    if not await _reject_if_not_reviewable(callback, db, order_id):
        return

    order = db.get_order(order_id)
    assert order is not None

    await state.set_state(DeclineFlow.waiting_reason)
    if isinstance(callback.message, Message):
        prompt = await callback.message.answer(
            texts.REVIEW_DECLINE_PROMPT,
            reply_markup=keyboards.decline_reason_keyboard(order_id),
            parse_mode=ParseMode.HTML,
        )
        await state.update_data(
            decline_order_id=order_id,
            decline_prompt_chat_id=prompt.chat.id,
            decline_prompt_message_id=prompt.message_id,
        )
    else:
        await state.update_data(decline_order_id=order_id)
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_DECLINE_PRESET_PREFIX))
async def cb_decline_preset(
    callback: CallbackQuery,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return
    if callback.from_user is None:
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(
        keyboards.CB_ADMIN_DECLINE_PRESET_PREFIX
    )
    parts = raw.split(":", 1)
    if len(parts) != 2:
        await callback.answer()
        return
    try:
        order_id = int(parts[0])
    except ValueError:
        await callback.answer()
        return
    preset_id = parts[1]
    reason = texts.DECLINE_PRESET_REASONS.get(preset_id)
    if reason is None:
        await callback.answer()
        return

    if not await _reject_if_not_reviewable(callback, db, order_id):
        await state.clear()
        return

    data = await state.get_data()
    await state.clear()
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    prompt_chat_id = int(data.get("decline_prompt_chat_id", 0)) or callback.message.chat.id
    prompt_message_id = (
        int(data.get("decline_prompt_message_id", 0)) or callback.message.message_id
    )

    await _apply_decline(
        order_id=order_id,
        reason=reason,
        admin_user=callback.from_user,
        bot=bot,
        db=db,
        prompt_chat_id=prompt_chat_id,
        prompt_message_id=prompt_message_id,
        error_reply=callback.message,
    )
    await callback.answer()


@router.callback_query(F.data.startswith(keyboards.CB_ADMIN_DECLINE_CANCEL_PREFIX))
async def cb_decline_cancel(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_callback(callback, settings, db, ORDERS_REVIEW):
        return
    await state.clear()
    if isinstance(callback.message, Message):
        await _edit_decline_prompt(
            bot,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id,
            text=texts.REVIEW_DECLINE_CANCELLED,
        )
    await callback.answer(texts.CANCELLED)


@router.message(StateFilter(DeclineFlow.waiting_reason), Command("cancel"))
async def cmd_cancel_decline(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_REVIEW):
        return
    data = await state.get_data()
    await state.clear()
    chat_id = int(data.get("decline_prompt_chat_id", 0))
    msg_id = int(data.get("decline_prompt_message_id", 0))
    if chat_id and msg_id:
        await _edit_decline_prompt(
            bot,
            chat_id=chat_id,
            message_id=msg_id,
            text=texts.REVIEW_DECLINE_CANCELLED,
        )
    await message.answer(texts.CANCELLED)


@router.message(StateFilter(DeclineFlow.waiting_reason))
async def on_decline_reason(
    message: Message,
    state: FSMContext,
    db: Database,
    bot: Bot,
    settings: Settings,
) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_REVIEW):
        await state.clear()
        return
    if message.from_user is None:
        return

    data = await state.get_data()
    order_id = int(data.get("decline_order_id", 0))
    prompt_chat_id = int(data.get("decline_prompt_chat_id", 0))
    prompt_message_id = int(data.get("decline_prompt_message_id", 0))
    reason = (message.text or "").strip()
    if not reason:
        await message.answer(
            "لطفاً دلیل رد را بنویسید یا از دکمه‌های بالا انتخاب کنید."
        )
        return
    await state.clear()

    if not order_id:
        return

    await _apply_decline(
        order_id=order_id,
        reason=reason,
        admin_user=message.from_user,
        bot=bot,
        db=db,
        prompt_chat_id=prompt_chat_id or None,
        prompt_message_id=prompt_message_id or None,
        error_reply=message,
    )
