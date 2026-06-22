"""Mandatory channel join — user verify + admin /reqchannel setup."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import TOOLS_MISC
from app.channel_gate import (
    check_user_membership,
    reply_join_required,
    save_invite_link,
    try_bind_required_channel,
)
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import admin_panel_access, guard_admin_message
from app.handlers.buyer_ui import buyer_reply_keyboard
from app.logs import resolve_forwarded_channel_id

router = Router(name="required_channel")


class RequiredChannelFlow(StatesGroup):
    waiting_channel = State()
    waiting_invite_link = State()


async def start_required_channel_wizard(message: Message, state: FSMContext) -> None:
    await state.set_state(RequiredChannelFlow.waiting_channel)
    await message.answer(
        texts.REQ_CHANNEL_PROMPT,
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_TOOLS
        ),
    )


async def start_invite_link_step(message: Message, state: FSMContext) -> None:
    await state.set_state(RequiredChannelFlow.waiting_invite_link)
    await message.answer(
        texts.REQ_CHANNEL_LINK_PROMPT,
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=keyboards.CB_ADM_TOOLS
        ),
    )


@router.callback_query(F.data == keyboards.CB_MAIN_CHECK_JOIN)
async def cb_check_channel_join(
    callback: CallbackQuery,
    bot: Bot,
    settings: Settings,
    db: Database,
    state: FSMContext,
) -> None:
    if callback.from_user is None:
        await callback.answer()
        return
    uid = callback.from_user.id
    check = await check_user_membership(bot, db, settings, uid)

    if check.gate_unavailable:
        from app.channel_gate import required_channel_id, send_gate_unavailable

        cid = required_channel_id(db, settings)
        if cid is not None:
            await send_gate_unavailable(bot, settings, callback, cid)
        else:
            await callback.answer(texts.JOIN_GATE_UNAVAILABLE_SHORT, show_alert=True)
        return

    if check.joined:
        await state.clear()
        await callback.answer(texts.JOIN_VERIFIED_OK)
        if callback.message is None:
            return
        if admin_panel_access(uid, settings, db):
            from app.handlers.admin_panel import send_admin_home

            await send_admin_home(
                callback.message,
                settings,
                db,
                admin_user_id=uid,
            )
        else:
            await callback.message.answer(
                texts.WELCOME,
                reply_markup=buyer_reply_keyboard(
                    callback.message, db, user_id=uid
                ),
            )
    else:
        await callback.answer(texts.JOIN_NOT_YET, show_alert=True)
        if callback.message is not None:
            await reply_join_required(
                bot,
                db,
                settings,
                callback,
                force=True,
            )


@router.message(Command("reqchannel"), StateFilter(None))
async def cmd_reqchannel(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_MISC):
        return

    raw = (command.args or "").strip()
    if raw.lower() in ("off", "-", "0", "none"):
        db.set_required_channel(None)
        await message.answer(texts.REQ_CHANNEL_CLEARED)
        return

    if raw:
        try:
            chat_id = int(raw)
        except ValueError:
            await message.answer(texts.REQ_CHANNEL_USAGE)
            return
        ok, reply, needs_link = await try_bind_required_channel(bot, db, chat_id)
        await message.answer(reply)
        if ok and needs_link:
            await start_invite_link_step(message, state)
        elif ok:
            await state.clear()
        return

    await start_required_channel_wizard(message, state)


@router.message(Command("reqchannellink"), StateFilter(None))
async def cmd_reqchannel_link(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_MISC):
        return
    raw = (command.args or "").strip()
    if not raw:
        await start_invite_link_step(message, state)
        return
    ok, reply = save_invite_link(db, raw)
    await message.answer(reply)
    if ok:
        await state.clear()


@router.message(Command("cancel"), StateFilter(RequiredChannelFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(RequiredChannelFlow)
)
async def cancel_required_channel(
    event: Message | CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(RequiredChannelFlow.waiting_channel))
async def on_required_channel_input(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
    bot: Bot,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_MISC):
        await state.clear()
        return

    chat_id = resolve_forwarded_channel_id(message)
    if chat_id is None:
        text = (message.text or "").strip()
        if text.lstrip("-").isdigit():
            chat_id = int(text)
        else:
            await message.answer(texts.REQ_CHANNEL_NEED_FORWARD)
            return

    ok, reply, needs_link = await try_bind_required_channel(bot, db, chat_id)
    await message.answer(reply)
    if ok and needs_link:
        await start_invite_link_step(message, state)
    elif ok:
        await state.clear()


@router.message(StateFilter(RequiredChannelFlow.waiting_invite_link))
async def on_required_channel_link_input(
    message: Message,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_MISC):
        await state.clear()
        return
    ok, reply = save_invite_link(db, message.text or "")
    await message.answer(reply)
    if ok:
        await state.clear()
