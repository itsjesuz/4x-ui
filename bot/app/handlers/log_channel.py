"""Admin command /logchannel — bind a Telegram channel for audit logs."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import TOOLS_MISC
from app.handlers.admin_helpers import guard_admin_message
from app.logs import resolve_forwarded_channel_id, try_bind_log_channel

router = Router(name="log_channel")


class LogChannelFlow(StatesGroup):
    waiting_channel = State()


async def start_log_channel_wizard(message: Message, state: FSMContext) -> None:
    await state.set_state(LogChannelFlow.waiting_channel)
    await message.answer(
        texts.LOG_CHANNEL_PROMPT,
        reply_markup=keyboards.admin_flow_cancel_inline(back_data=keyboards.CB_ADM_TOOLS),
    )


@router.message(Command("logchannel"), StateFilter(None))
async def cmd_logchannel(
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
        db.set_log_channel_id(None)
        await message.answer(texts.LOG_CHANNEL_CLEARED)
        return

    if raw:
        try:
            chat_id = int(raw)
        except ValueError:
            await message.answer(texts.LOG_CHANNEL_USAGE)
            return
        ok, reply = await try_bind_log_channel(bot, db, chat_id)
        await message.answer(reply)
        if not ok:
            return
        return

    await start_log_channel_wizard(message, state)


@router.message(Command("cancel"), StateFilter(LogChannelFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(LogChannelFlow)
)
async def cancel_logchannel(
    event: Message | CallbackQuery, state: FSMContext
) -> None:
    await state.clear()
    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(LogChannelFlow.waiting_channel))
async def on_logchannel_input(
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
            await message.answer(texts.LOG_CHANNEL_NEED_FORWARD)
            return

    ok, reply = await try_bind_log_channel(bot, db, chat_id)
    await message.answer(reply)
    if ok:
        await state.clear()
