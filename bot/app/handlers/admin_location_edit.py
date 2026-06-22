"""Admin: edit location (wizard + /editlocation)."""

from __future__ import annotations

import re
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.admin_perms import LOCATIONS
from app.config import Settings
from app.db import Database
from app.handlers.admin_helpers import (
    admin_can,
    guard_admin_callback,
    guard_admin_message,
    is_admin,
    normalize_panel_url,
)
from app.handlers.admin_panel import send_location_detail
from app.handlers.admin_ui_helpers import admin_edit_or_answer

router = Router(name="admin_location_edit")

_KEEP = "-"
_SUB_CLEAR = frozenset({"0", "none", "clear", "off"})
_SUBID_PLACEHOLDER_RE = re.compile(r"\{subId\}", re.IGNORECASE)


class EditLocationFlow(StatesGroup):
    waiting_name = State()
    waiting_base_url = State()
    waiting_token = State()
    waiting_inbounds = State()
    waiting_sub = State()


def _keep_or_replace(raw: str, current: str) -> str:
    s = (raw or "").strip()
    return current if s == _KEEP else s


def _normalize_sub_template(raw: str) -> str:
    return _SUBID_PLACEHOLDER_RE.sub("{subId}", raw.strip())


def _parse_inbounds(raw: str, current: list[int]) -> list[int] | None:
    s = (raw or "").strip()
    if s == _KEEP:
        return current
    try:
        ids = [int(x.strip()) for x in s.split(",") if x.strip()]
    except ValueError:
        return None
    return ids if ids else None


def _parse_sub_url(raw: str, current: str | None) -> str | None | str:
    """Return template, None (cleared), or 'bad' if invalid."""
    s = (raw or "").strip()
    if s == _KEEP:
        return current
    if s.lower() in _SUB_CLEAR:
        return None
    if not _SUBID_PLACEHOLDER_RE.search(s):
        return "bad"
    return _normalize_sub_template(s)


def _split_pipe_fields(raw: str) -> list[str]:
    return [p.strip() for p in raw.split("|")]


def _parse_editlocation_args(
    raw: str,
    *,
    default_loc_id: int | None = None,
) -> tuple[int | None, list[str] | None, str | None]:
    """Returns (loc_id, field_parts, error_key). field_parts are 4 or 5 items."""
    parts = _split_pipe_fields(raw.strip())
    if not parts or not any(parts):
        return None, None, "usage"

    first = parts[0]
    if first.lstrip("-").isdigit():
        try:
            loc_id = int(first)
        except ValueError:
            return None, None, "usage"
        field_parts = parts[1:]
        if len(field_parts) not in (4, 5):
            return None, None, "usage"
        if not all(field_parts[:4]):
            return None, None, "usage"
        return loc_id, field_parts, None

    if len(parts) in (4, 5):
        if default_loc_id is None:
            return None, None, "missing_id"
        if not all(parts[:4]):
            return None, None, "usage"
        return default_loc_id, parts, None

    return None, None, "usage"


def _extract_edit_raw(message: Message, command: CommandObject | None = None) -> str:
    if command is not None:
        return (command.args or "").strip()
    text = (message.text or "").strip()
    if text.lower().startswith("/editlocation"):
        rest = text.split(maxsplit=1)
        return rest[1].strip() if len(rest) > 1 else ""
    return text


def _apply_edit_from_parts(
    db: Database,
    loc_id: int,
    parts: list[str],
) -> tuple[bool, str | None]:
    """Parse pipe-separated fields (name..inbounds, optional sub). Returns (ok, error_key)."""
    loc = db.get_location(loc_id)
    if loc is None:
        return False, "not_found"

    if len(parts) not in (4, 5):
        return False, "usage"

    name, base_url, api_token, inbound_str = parts[:4]
    sub_raw = parts[4].strip() if len(parts) == 5 and parts[4].strip() else None

    name = _keep_or_replace(name, loc.name)
    base_url = normalize_panel_url(_keep_or_replace(base_url, loc.base_url))
    api_token = _keep_or_replace(api_token, loc.api_token)

    inbound_ids = _parse_inbounds(inbound_str, loc.inbound_ids)
    if inbound_ids is None:
        return False, "usage"

    if sub_raw is None:
        sub_url_template = loc.sub_url_template
    else:
        sub_parsed = _parse_sub_url(sub_raw, loc.sub_url_template)
        if sub_parsed == "bad":
            return False, "sub_bad"
        sub_url_template = sub_parsed

    if not db.update_location(
        loc_id,
        name=name,
        base_url=base_url,
        api_token=api_token,
        inbound_ids=inbound_ids,
        sub_url_template=sub_url_template,
    ):
        return False, "not_found"
    return True, None


async def _reply_edit_errors(message: Message, err: str, loc_id: int | None) -> None:
    if err == "not_found" and loc_id is not None:
        await message.answer(texts.EDIT_LOC_NOT_FOUND.format(id=loc_id))
    elif err == "missing_id":
        await message.answer(texts.EDIT_LOC_MISSING_ID)
    elif err == "sub_bad":
        await message.answer(texts.SET_SUBURL_BAD)
    else:
        await message.answer(texts.EDIT_LOC_USAGE)


async def _reply_edit_success(message: Message, db: Database, loc_id: int) -> None:
    loc = db.get_location(loc_id)
    if loc is None:
        return
    inbounds = ",".join(str(i) for i in loc.inbound_ids) or "—"
    await message.answer(
        texts.EDIT_LOC_OK.format(
            id=loc_id,
            name=escape(loc.name),
            base_url=escape(loc.base_url),
            inbounds=inbounds,
        )
    )


async def _run_editlocation(
    message: Message,
    state: FSMContext,
    db: Database,
    raw: str,
    *,
    default_loc_id: int | None = None,
) -> bool:
    """Parse one-shot edit; clear wizard state on success. Returns True if handled."""
    if not raw.strip():
        await message.answer(texts.EDIT_LOC_USAGE)
        return True

    loc_id, field_parts, err = _parse_editlocation_args(
        raw, default_loc_id=default_loc_id
    )
    if err or loc_id is None or field_parts is None:
        if err:
            await _reply_edit_errors(message, err, loc_id)
        return err is not None

    ok, apply_err = _apply_edit_from_parts(db, loc_id, field_parts)
    if apply_err:
        await _reply_edit_errors(message, apply_err, loc_id)
        return True
    if not ok:
        await message.answer(texts.EDIT_LOC_USAGE)
        return True

    await state.clear()
    await _reply_edit_success(message, db, loc_id)
    await send_location_detail(message, db, loc_id)
    return True


async def _save_location(
    message: Message,
    db: Database,
    loc_id: int,
    *,
    name: str,
    base_url: str,
    api_token: str,
    inbound_ids: list[int],
    sub_url_template: str | None,
) -> bool:
    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.EDIT_LOC_NOT_FOUND.format(id=loc_id))
        return False

    base_url = normalize_panel_url(base_url)
    if not db.update_location(
        loc_id,
        name=name,
        base_url=base_url,
        api_token=api_token,
        inbound_ids=inbound_ids,
        sub_url_template=sub_url_template,
    ):
        await message.answer(texts.EDIT_LOC_NOT_FOUND.format(id=loc_id))
        return False

    updated = db.get_location(loc_id)
    if updated is None:
        return False

    inbounds = ",".join(str(i) for i in updated.inbound_ids) or "—"
    await message.answer(
        texts.EDIT_LOC_OK.format(
            id=loc_id,
            name=escape(updated.name),
            base_url=escape(updated.base_url),
            inbounds=inbounds,
        )
    )
    await send_location_detail(message, db, loc_id)
    return True


async def _prompt_step(
    message: Message,
    loc_id: int,
    text: str,
) -> None:
    await admin_edit_or_answer(
        message,
        text,
        keyboards.admin_flow_cancel_inline(
            back_data=f"{keyboards.CB_ADM_LOC_DETAIL_PREFIX}{loc_id}"
        ),
        edit_in_place=True,
    )


async def start_edit_location_wizard(
    message: Message, state: FSMContext, db: Database, loc_id: int
) -> None:
    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.EDIT_LOC_NOT_FOUND.format(id=loc_id))
        return

    await state.update_data(
        loc_id=loc_id,
        name=loc.name,
        base_url=loc.base_url,
        api_token=loc.api_token,
        inbound_ids=loc.inbound_ids,
        sub_url_template=loc.sub_url_template,
    )
    await state.set_state(EditLocationFlow.waiting_name)
    await _prompt_step(
        message,
        loc_id,
        texts.EDIT_LOC_PROMPT_NAME.format(
            id=loc_id, current=escape(loc.name)
        ),
    )


async def _try_bulk_edit_in_wizard(
    message: Message,
    state: FSMContext,
    db: Database,
) -> bool:
    raw = _extract_edit_raw(message)
    if "|" not in raw:
        return False
    data = await state.get_data()
    default_loc_id = data.get("loc_id")
    if default_loc_id is not None:
        default_loc_id = int(default_loc_id)
    return await _run_editlocation(
        message, state, db, raw, default_loc_id=default_loc_id
    )


@router.callback_query(F.data.startswith(keyboards.CB_ADM_LOC_EDIT_PREFIX))
async def cb_admin_loc_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_callback(callback, settings, db, LOCATIONS):
        return
    if not isinstance(callback.message, Message):
        await callback.answer()
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_ADM_LOC_EDIT_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    await start_edit_location_wizard(callback.message, state, db, loc_id)
    await callback.answer()


@router.message(Command("editlocation"))
async def cmd_editlocation(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    data = await state.get_data()
    default_loc_id = data.get("loc_id")
    if default_loc_id is not None:
        default_loc_id = int(default_loc_id)

    raw = _extract_edit_raw(message, command)
    await _run_editlocation(
        message, state, db, raw, default_loc_id=default_loc_id
    )


@router.message(Command("cancel"), StateFilter(EditLocationFlow))
@router.callback_query(
    F.data == keyboards.CB_ADM_FLOW_CANCEL, StateFilter(EditLocationFlow)
)
async def edit_location_cancel(
    event: Message | CallbackQuery,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    user_id = event.from_user.id if event.from_user else None
    if user_id is None or not is_admin(user_id, settings):
        msg = texts.NOT_ADMIN
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return
    if not admin_can(user_id, LOCATIONS, settings, db):
        msg = texts.NOT_PERMITTED
        if isinstance(event, CallbackQuery):
            await event.answer(msg, show_alert=True)
        else:
            await event.answer(msg)
        return

    data = await state.get_data()
    loc_id = data.get("loc_id")
    await state.clear()

    if isinstance(event, CallbackQuery):
        await event.answer(texts.CANCELLED)
        if isinstance(event.message, Message) and loc_id is not None:
            await send_location_detail(
                event.message, db, int(loc_id), edit_in_place=True
            )
    else:
        await event.answer(texts.CANCELLED)


@router.message(StateFilter(EditLocationFlow.waiting_name))
async def edit_loc_name(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return
    if await _try_bulk_edit_in_wizard(message, state, db):
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    name = _keep_or_replace(message.text or "", data["name"])
    await state.update_data(name=name)
    await state.set_state(EditLocationFlow.waiting_base_url)
    await message.answer(
        texts.EDIT_LOC_PROMPT_BASE_URL.format(
            id=loc_id, current=escape(data["base_url"])
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=f"{keyboards.CB_ADM_LOC_DETAIL_PREFIX}{loc_id}"
        ),
    )


@router.message(StateFilter(EditLocationFlow.waiting_base_url))
async def edit_loc_base_url(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return
    if await _try_bulk_edit_in_wizard(message, state, db):
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    base_url = _keep_or_replace(message.text or "", data["base_url"])
    await state.update_data(base_url=base_url)
    await state.set_state(EditLocationFlow.waiting_token)
    await message.answer(
        texts.EDIT_LOC_PROMPT_TOKEN.format(id=loc_id),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=f"{keyboards.CB_ADM_LOC_DETAIL_PREFIX}{loc_id}"
        ),
    )


@router.message(StateFilter(EditLocationFlow.waiting_token))
async def edit_loc_token(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return
    if await _try_bulk_edit_in_wizard(message, state, db):
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    api_token = _keep_or_replace(message.text or "", data["api_token"])
    await state.update_data(api_token=api_token)
    await state.set_state(EditLocationFlow.waiting_inbounds)
    current = ",".join(str(i) for i in data["inbound_ids"]) or "—"
    await message.answer(
        texts.EDIT_LOC_PROMPT_INBOUNDS.format(id=loc_id, current=current),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=f"{keyboards.CB_ADM_LOC_DETAIL_PREFIX}{loc_id}"
        ),
    )


@router.message(StateFilter(EditLocationFlow.waiting_inbounds))
async def edit_loc_inbounds(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return
    if await _try_bulk_edit_in_wizard(message, state, db):
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    inbound_ids = _parse_inbounds(
        message.text or "", list(data["inbound_ids"])
    )
    if inbound_ids is None:
        await message.answer(texts.EDIT_LOC_USAGE)
        return

    await state.update_data(inbound_ids=inbound_ids)
    await state.set_state(EditLocationFlow.waiting_sub)
    sub_current = data.get("sub_url_template") or "—"
    await message.answer(
        texts.EDIT_LOC_PROMPT_SUB.format(
            id=loc_id, current=escape(str(sub_current))
        ),
        reply_markup=keyboards.admin_flow_cancel_inline(
            back_data=f"{keyboards.CB_ADM_LOC_DETAIL_PREFIX}{loc_id}"
        ),
    )


@router.message(StateFilter(EditLocationFlow.waiting_sub))
async def edit_loc_sub(
    message: Message, state: FSMContext, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        await state.clear()
        return
    if await _try_bulk_edit_in_wizard(message, state, db):
        return

    data = await state.get_data()
    loc_id = int(data["loc_id"])
    sub_parsed = _parse_sub_url(
        message.text or "", data.get("sub_url_template")
    )
    if sub_parsed == "bad":
        await message.answer(texts.SET_SUBURL_BAD)
        return

    await state.clear()
    await _save_location(
        message,
        db,
        loc_id,
        name=data["name"],
        base_url=data["base_url"],
        api_token=data["api_token"],
        inbound_ids=list(data["inbound_ids"]),
        sub_url_template=sub_parsed,
    )
