from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import keyboards, texts
from app.config import Settings
from app.db import Database
from app.admin_perms import (
    LOCATIONS,
    PANEL,
    ORDERS_MANAGE,
    ORDERS_REVIEW,
    SERVICES,
    SETTINGS,
    TOOLS_MISC,
    TOOLS_SYNC,
    USERS,
)
from app.handlers.admin_helpers import (
    guard_admin_message,
    format_stats_text,
    format_settings_text,
    location_pricing_label,
    normalize_panel_url,
    run_clear_declined,
    run_sync_panel,
)
from app.handlers.admin_panel import (
    send_base_plans,
    send_pending_list,
    send_users,
)


router = Router(name="admin")
log = logging.getLogger(__name__)


# ---------- generic ----------
def _forwarded_user_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)
    sender_user = getattr(origin, "sender_user", None)
    if sender_user is not None:
        user_id = getattr(sender_user, "id", None)
        if user_id is not None:
            return int(user_id)

    forwarded_from = getattr(message, "forward_from", None)
    if forwarded_from is not None:
        user_id = getattr(forwarded_from, "id", None)
        if user_id is not None:
            return int(user_id)

    return None


def _forwarded_chat_id(message: Message) -> int | None:
    origin = getattr(message, "forward_origin", None)
    for attr in ("sender_chat", "chat"):
        chat = getattr(origin, attr, None)
        if chat is not None:
            chat_id = getattr(chat, "id", None)
            if chat_id is not None:
                return int(chat_id)

    forwarded_chat = getattr(message, "forward_from_chat", None)
    if forwarded_chat is not None:
        chat_id = getattr(forwarded_chat, "id", None)
        if chat_id is not None:
            return int(chat_id)

    return None


@router.message(StateFilter(None), F.forward_origin)
async def msg_forwarded_user_id(
    message: Message, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, PANEL):
        return

    user_id = _forwarded_user_id(message)
    if user_id is not None:
        await message.answer(texts.FORWARDED_USER_ID.format(user_id=user_id))
        return

    chat_id = _forwarded_chat_id(message)
    if chat_id is not None:
        await message.answer(texts.FORWARDED_CHAT_ID.format(chat_id=chat_id))
        return

    await message.answer(texts.FORWARDED_USER_HIDDEN)


@router.message(Command("stats"))
async def cmd_stats(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, PANEL):
        return
    if message.from_user is None:
        return
    await message.answer(format_stats_text(db))


@router.message(Command("users"))
async def cmd_users(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, USERS):
        return
    if message.from_user is None:
        return
    await send_users(message, settings, db, page=0, user_id=message.from_user.id)


# ---------- predefined service packages (manual purchase) ----------
@router.message(Command("addservice"))
async def cmd_addservice(
    message: Message,
    command: CommandObject,
    state: FSMContext,
    settings: Settings,
    db: Database,
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return

    await state.clear()
    parts = (command.args or "").split()
    if len(parts) != 4:
        from app.handlers.admin_add_service import start_add_service_wizard

        await start_add_service_wizard(message, state, db)
        return
    try:
        loc_id, volume_gb, duration_days, price = (
            int(parts[0]),
            int(parts[1]),
            int(parts[2]),
            int(parts[3]),
        )
    except ValueError:
        await message.answer(texts.ADD_SERVICE_USAGE)
        return

    ok, reason, pkg_id = db.add_service_package(
        loc_id, volume_gb, duration_days, price
    )
    if not ok:
        msg = {
            "not_found": texts.ADD_SERVICE_NOT_FOUND,
            "invalid": texts.ADD_SERVICE_INVALID,
            "duplicate": texts.ADD_SERVICE_DUPLICATE,
            "test_location": texts.ADD_SERVICE_TEST_LOC,
            "disabled": texts.ADD_SERVICE_DISABLED,
        }.get(reason, texts.ADD_SERVICE_INVALID)
        await message.answer(msg)
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
        + f"\n📍 {loc_name}"
    )
    if message.from_user is not None:
        from app.handlers.admin_panel import send_services

        await send_services(message, db, settings, message.from_user.id)


@router.message(Command("delservice"))
async def cmd_delservice(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return

    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.DEL_SERVICE_USAGE)
        return
    try:
        package_id = int(raw)
    except ValueError:
        await message.answer(texts.DEL_SERVICE_USAGE)
        return

    if not db.remove_service_package(package_id):
        await message.answer(texts.DEL_SERVICE_NOTFOUND)
        return
    await message.answer(texts.DEL_SERVICE_OK.format(id=package_id))


@router.message(Command("listservices"))
async def cmd_listservices(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return

    raw = (command.args or "").strip()
    loc_filter: int | None = None
    if raw:
        try:
            loc_filter = int(raw)
        except ValueError:
            await message.answer(texts.ADD_SERVICE_USAGE.replace("addservice", "listservices"))
            return
        if db.get_location(loc_filter) is None:
            await message.answer(texts.ADD_SERVICE_NOT_FOUND)
            return

    packages = (
        db.list_service_packages(loc_filter, only_enabled=False)
        if loc_filter is not None
        else db.list_all_service_packages()
    )
    if not packages:
        await message.answer(texts.LIST_SERVICES_EMPTY)
        return

    from app.pricing import format_price_with_offer

    filter_line = f" — لوکیشن <code>#{loc_filter}</code>" if loc_filter else ""
    lines = [texts.LIST_SERVICES_HEADER.format(filter_line=filter_line)]
    offer = db.get_offer_config()
    for pkg in packages:
        loc = db.get_location(pkg.location_id)
        loc_name = escape(loc.name) if loc else "—"
        base = int(pkg.price)
        final = db.resolve_price(base)
        if offer.is_active and final < base:
            price_label = format_price_with_offer(base, final)
        else:
            price_label = texts.format_price(base)
        lines.append(
            texts.LIST_SERVICES_LINE.format(
                id=pkg.id,
                loc_id=pkg.location_id,
                loc_name=loc_name,
                volume=pkg.volume_gb,
                days=pkg.duration_days,
                price=price_label,
            )
        )
    mode = "روشن ✅" if db.is_manual_purchase_enabled() else "خاموش ❌"
    lines.append(f"\n🔀 حالت خرید دستی: <b>{mode}</b>")
    await message.answer("\n".join(lines))


@router.message(Command("togglemanualpurchase"))
async def cmd_toggle_manual_purchase(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return

    raw = (command.args or "").strip().lower()
    if raw in ("on", "1", "yes"):
        enabled = True
    elif raw in ("off", "0", "no"):
        enabled = False
    elif not raw:
        enabled = not db.is_manual_purchase_enabled()
    else:
        await message.answer(texts.TOGGLE_MANUAL_PURCHASE_USAGE)
        return

    db.set_manual_purchase_enabled(enabled)
    mode = "پلن ازپیش‌تعریف (دکمه‌ها) ✅" if enabled else "انتخاب حجم و مدت (فرمول قیمت) ❌"
    extra = ""
    if enabled and not db.list_all_service_packages():
        extra = "\n\n⚠️ هنوز پلنی با <code>/addservice</code> تعریف نشده."
    await message.answer(texts.TOGGLE_MANUAL_PURCHASE_OK.format(mode=mode) + extra)


# ---------- service package edit ----------
@router.message(Command("editservice"))
async def cmd_editservice(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return

    parts = (command.args or "").split()
    if len(parts) != 4:
        await message.answer(texts.EDIT_SERVICE_USAGE)
        return
    try:
        package_id, volume_gb, duration_days, price = (
            int(parts[0]),
            int(parts[1]),
            int(parts[2]),
            int(parts[3]),
        )
    except ValueError:
        await message.answer(texts.EDIT_SERVICE_USAGE)
        return

    ok, reason = db.update_service_package(
        package_id, volume_gb, duration_days, price
    )
    if not ok:
        msg = {
            "not_found": texts.DEL_SERVICE_NOTFOUND,
            "invalid": texts.ADD_SERVICE_INVALID,
            "duplicate": texts.ADD_SERVICE_DUPLICATE,
            "test_location": texts.ADD_SERVICE_TEST_LOC,
        }.get(reason, texts.ADD_SERVICE_INVALID)
        await message.answer(msg)
        return

    await message.answer(
        texts.EDIT_SERVICE_OK.format(
            id=package_id,
            volume=volume_gb,
            days=duration_days,
            price=texts.format_price(price),
        )
    )


# ---------- ban / unban ----------
@router.message(Command("ban"))
async def cmd_ban(
    message: Message, command: CommandObject, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_message(message, settings, db, USERS):
        return
    user_id = _parse_admin_user_id(message, command)
    if user_id is None:
        await message.answer(texts.BAN_USAGE)
        return
    if message.from_user and user_id == message.from_user.id:
        await message.answer(texts.BAN_SELF)
        return
    if db.get_user(user_id) is None:
        await message.answer(texts.BAN_USER_NOTFOUND)
        return
    db.set_user_banned(user_id, True)
    await message.answer(texts.BAN_OK.format(user_id=user_id))
    await _log_ban_toggle(bot, db, message, user_id, banned=True)


@router.message(Command("unban"))
async def cmd_unban(
    message: Message, command: CommandObject, settings: Settings, db: Database, bot: Bot
) -> None:
    if not await guard_admin_message(message, settings, db, USERS):
        return
    user_id = _parse_admin_user_id(message, command)
    if user_id is None:
        await message.answer(texts.UNBAN_USAGE)
        return
    if db.get_user(user_id) is None:
        await message.answer(texts.BAN_USER_NOTFOUND)
        return
    db.set_user_banned(user_id, False)
    await message.answer(texts.UNBAN_OK.format(user_id=user_id))
    await _log_ban_toggle(bot, db, message, user_id, banned=False)


def _parse_admin_user_id(message: Message, command: CommandObject) -> int | None:
    raw = (command.args or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


async def _log_ban_toggle(
    bot: Bot, db: Database, message: Message, user_id: int, *, banned: bool
) -> None:
    from app.logs import Actor, make_logger

    admin = Actor.from_user(message.from_user)
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


# ---------- settings ----------
@router.message(Command("setcard"))
async def cmd_setcard(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SETTINGS):
        return

    raw = (command.args or "").strip()
    if "|" not in raw:
        await message.answer(texts.SET_CARD_USAGE)
        return
    number, _, holder = raw.partition("|")
    number = number.strip()
    holder = holder.strip()
    if not number or not holder:
        await message.answer(texts.SET_CARD_USAGE)
        return

    number = texts.format_card_number(number)
    db.set_setting("card_number", number)
    db.set_setting("card_holder", holder)
    await message.answer(
        texts.SET_CARD_OK.format(number=escape(number), holder=escape(holder))
    )


@router.message(Command("setprice"))
async def cmd_setprice(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SETTINGS):
        return

    parts = (command.args or "").split()
    if len(parts) != 3:
        await message.answer(texts.SET_PRICE_USAGE)
        return
    try:
        base, per_gb, per_day = (int(p) for p in parts)
    except ValueError:
        await message.answer(texts.SET_PRICE_USAGE)
        return
    if min(base, per_gb, per_day) < 0:
        await message.answer(texts.SET_PRICE_USAGE)
        return

    db.set_setting("price_base", str(base))
    db.set_setting("price_per_gb", str(per_gb))
    db.set_setting("price_per_day", str(per_day))
    await message.answer(texts.SET_PRICE_OK.format(base=base, per_gb=per_gb, per_day=per_day))


@router.message(Command("showsettings"))
async def cmd_showsettings(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, SETTINGS):
        return
    await message.answer(format_settings_text(db))


# ---------- base buy plans (volume / duration presets) ----------
@router.message(Command("plans"))
async def cmd_plans(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    uid = message.from_user.id if message.from_user else 0
    await send_base_plans(message, db, settings, uid)


@router.message(Command("addvolume"))
async def cmd_add_volume(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_PLAN_USAGE)
        return
    try:
        gb = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_PLAN_INVALID)
        return
    ok, reason = db.add_volume_preset(gb)
    if not ok:
        msg = {
            "exists": texts.ADMIN_PLAN_EXISTS,
            "invalid": texts.ADMIN_PLAN_INVALID,
            "max": texts.ADMIN_PLAN_MAX,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await message.answer(msg)
        return
    await message.answer(texts.ADMIN_PLAN_VOL_ADDED.format(gb=gb))


@router.message(Command("delvolume"))
async def cmd_del_volume(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_PLAN_USAGE)
        return
    try:
        gb = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_PLAN_INVALID)
        return
    ok, reason = db.remove_volume_preset(gb)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
            "invalid": texts.ADMIN_PLAN_INVALID,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await message.answer(msg)
        return
    await message.answer(texts.ADMIN_PLAN_VOL_REMOVED.format(gb=gb))


@router.message(Command("addduration"))
async def cmd_add_duration(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_PLAN_USAGE)
        return
    try:
        days = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_PLAN_INVALID)
        return
    ok, reason = db.add_duration_preset(days)
    if not ok:
        msg = {
            "exists": texts.ADMIN_PLAN_EXISTS,
            "invalid": texts.ADMIN_PLAN_INVALID,
            "max": texts.ADMIN_PLAN_MAX,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await message.answer(msg)
        return
    await message.answer(texts.ADMIN_PLAN_DUR_ADDED.format(days=days))


@router.message(Command("delduration"))
async def cmd_del_duration(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, SERVICES):
        return
    raw = (command.args or "").strip()
    if not raw:
        await message.answer(texts.ADMIN_PLAN_USAGE)
        return
    try:
        days = int(raw)
    except ValueError:
        await message.answer(texts.ADMIN_PLAN_INVALID)
        return
    ok, reason = db.remove_duration_preset(days)
    if not ok:
        msg = {
            "missing": texts.ADMIN_PLAN_NOT_FOUND,
            "last": texts.ADMIN_PLAN_LAST,
            "invalid": texts.ADMIN_PLAN_INVALID,
        }.get(reason, texts.ADMIN_PLAN_INVALID)
        await message.answer(msg)
        return
    await message.answer(texts.ADMIN_PLAN_DUR_REMOVED.format(days=days))


# ---------- locations ----------
@router.message(Command("locations"))
async def cmd_locations(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    locs = db.list_locations(only_enabled=False)
    if not locs:
        await message.answer(texts.LOC_LIST_EMPTY)
        return

    lines = [texts.LOC_LIST_HEADER]
    for loc in locs:
        test_tag = "🧪 " if loc.is_test else ""
        if not loc.enabled:
            state_emoji = "🔴"
        elif not loc.purchase_enabled:
            state_emoji = "🟡"
        else:
            state_emoji = "🟢"
        lines.append(
            texts.LOC_LIST_ITEM.format(
                id=loc.id,
                state_emoji=state_emoji,
                test_tag=test_tag,
                name=escape(loc.name),
                base_url=escape(loc.base_url),
                inbounds=",".join(str(i) for i in loc.inbound_ids) or "—",
                sub_template=escape(loc.sub_url_template) if loc.sub_url_template else "—",
                pricing=escape(location_pricing_label(db, loc)),
            )
        )
    await message.answer("\n\n".join(lines))


@router.message(Command("addlocation"))
async def cmd_addlocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    parts = [p.strip() for p in raw.split("|")]
    # 4 required fields, 5th (sub_url_template) is optional
    if len(parts) not in (4, 5) or not all(parts[:4]):
        await message.answer(texts.ADD_LOC_USAGE)
        return

    name, base_url, api_token, inbound_str = parts[:4]
    sub_url_template = parts[4].strip() if len(parts) == 5 and parts[4].strip() else None

    base_url = normalize_panel_url(base_url)
    try:
        inbound_ids = [int(x.strip()) for x in inbound_str.split(",") if x.strip()]
    except ValueError:
        await message.answer(texts.ADD_LOC_USAGE)
        return
    if not inbound_ids:
        await message.answer(texts.ADD_LOC_USAGE)
        return

    if sub_url_template is not None and "{subId}" not in sub_url_template:
        await message.answer(texts.SET_SUBURL_BAD)
        return

    loc_id = db.add_location(
        name=name,
        base_url=base_url,
        api_token=api_token,
        inbound_ids=inbound_ids,
        sub_url_template=sub_url_template,
    )
    loc = db.get_location(loc_id)
    pricing = escape(location_pricing_label(db, loc)) if loc else "—"
    extra_sub_line = (
        f"\n🔔 sub: <code>{escape(sub_url_template)}</code>"
        if sub_url_template else ""
    )
    await message.answer(
        texts.ADD_LOC_OK.format(name=escape(name), id=loc_id, pricing=pricing)
        + f"\n\n🔗 base_url:\n<code>{escape(base_url)}</code>"
        + f"\n📡 inbounds: <code>{','.join(str(i) for i in inbound_ids)}</code>"
        + extra_sub_line
    )


@router.message(Command("addtestlocation"))
async def cmd_addtestlocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    parts = [p.strip() for p in raw.split("|")]
    if len(parts) not in (4, 5) or not all(parts[:4]):
        await message.answer(texts.ADD_TEST_LOC_USAGE)
        return

    name, base_url, api_token, inbound_str = parts[:4]
    sub_url_template = parts[4].strip() if len(parts) == 5 and parts[4].strip() else None

    base_url = normalize_panel_url(base_url)
    try:
        inbound_ids = [int(x.strip()) for x in inbound_str.split(",") if x.strip()]
    except ValueError:
        await message.answer(texts.ADD_TEST_LOC_USAGE)
        return
    if not inbound_ids:
        await message.answer(texts.ADD_TEST_LOC_USAGE)
        return

    if sub_url_template is not None and "{subId}" not in sub_url_template:
        await message.answer(texts.SET_SUBURL_BAD)
        return

    loc_id = db.replace_test_location(
        name=name,
        base_url=base_url,
        api_token=api_token,
        inbound_ids=inbound_ids,
        sub_url_template=sub_url_template,
    )
    toggle_state = "روشن ✅" if db.is_test_feature_enabled() else "خاموش ❌"
    extra_sub_line = (
        f"\n🔔 sub: <code>{escape(sub_url_template)}</code>"
        if sub_url_template else ""
    )
    await message.answer(
        texts.ADD_TEST_LOC_OK.format(
            name=escape(name),
            id=loc_id,
            volume=texts.format_test_volume(),
            duration=texts.format_test_duration(),
            toggle_state=toggle_state,
        )
        + f"\n\n🔗 base_url:\n<code>{escape(base_url)}</code>"
        + f"\n📡 inbounds: <code>{','.join(str(i) for i in inbound_ids)}</code>"
        + extra_sub_line
    )


@router.message(Command("toggletest"))
async def cmd_toggletest(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_MISC):
        return

    raw = (command.args or "").strip().lower()
    if raw in ("on", "1", "yes"):
        enabled = True
    elif raw in ("off", "0", "no"):
        enabled = False
    elif not raw:
        enabled = not db.is_test_feature_enabled()
    else:
        await message.answer(texts.TOGGLE_TEST_USAGE)
        return

    db.set_test_feature_enabled(enabled)
    state = "روشن ✅" if enabled else "خاموش ❌"
    loc = db.get_test_location()
    extra = ""
    if enabled and loc is None:
        extra = "\n\n⚠️ لوکیشن تست ثبت نشده — ابتدا <code>/addtestlocation</code> بزنید."
    await message.answer(texts.TOGGLE_TEST_OK.format(state=state) + extra)


@router.message(Command("setlocationprice"))
async def cmd_setlocationprice(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    parts = (command.args or "").split()
    if len(parts) < 2:
        await message.answer(texts.SET_LOC_PRICE_USAGE)
        return
    try:
        loc_id = int(parts[0])
    except ValueError:
        await message.answer(texts.SET_LOC_PRICE_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    if parts[1] == "-":
        db.set_location_pricing(loc_id, price_base=None, price_per_gb=None, price_per_day=None)
        await message.answer(
            texts.SET_LOC_PRICE_DEFAULT_OK.format(id=loc_id, name=escape(loc.name))
        )
        return

    if len(parts) != 4:
        await message.answer(texts.SET_LOC_PRICE_USAGE)
        return
    try:
        base, per_gb, per_day = (int(p) for p in parts[1:4])
    except ValueError:
        await message.answer(texts.SET_LOC_PRICE_USAGE)
        return
    if min(base, per_gb, per_day) < 0:
        await message.answer(texts.SET_LOC_PRICE_USAGE)
        return

    db.set_location_pricing(
        loc_id, price_base=base, price_per_gb=per_gb, price_per_day=per_day
    )
    await message.answer(
        texts.SET_LOC_PRICE_OK.format(
            id=loc_id, name=escape(loc.name), base=base, per_gb=per_gb, per_day=per_day
        )
    )


@router.message(Command("setsuburl"))
async def cmd_setsuburl(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    parts = raw.split(maxsplit=1)
    if len(parts) != 2:
        await message.answer(texts.SET_SUBURL_USAGE)
        return
    try:
        loc_id = int(parts[0])
    except ValueError:
        await message.answer(texts.SET_SUBURL_USAGE)
        return

    template_raw = parts[1].strip()
    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    if template_raw == "-":
        db.set_location_sub_url_template(loc_id, None)
        await message.answer(texts.SET_SUBURL_CLEARED.format(id=loc_id))
        return

    if "{subId}" not in template_raw:
        await message.answer(texts.SET_SUBURL_BAD)
        return

    db.set_location_sub_url_template(loc_id, template_raw)
    await message.answer(
        texts.SET_SUBURL_OK.format(id=loc_id, template=escape(template_raw))
    )


@router.message(Command("dellocation"))
async def cmd_dellocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.DEL_LOC_USAGE)
        return

    result = db.remove_location(loc_id)
    if result == "not_found":
        await message.answer(texts.DEL_LOC_NOTFOUND)
    elif result == "disabled":
        await message.answer(texts.DEL_LOC_DISABLED.format(id=loc_id))
    else:
        await message.answer(texts.DEL_LOC_OK.format(id=loc_id))


@router.message(Command("purgelocation"))
async def cmd_purgelocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.PURGE_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    count = db.count_orders_for_location(loc_id)
    await message.answer(
        texts.PURGE_CONFIRM.format(id=loc_id, name=escape(loc.name), count=count),
        reply_markup=keyboards.purge_confirm(loc_id),
    )


@router.callback_query(F.data.startswith(keyboards.CB_PURGE_CONFIRM_PREFIX))
async def cb_purge_confirm(
    callback: CallbackQuery, db: Database, settings: Settings
) -> None:
    if callback.from_user is None or callback.from_user.id not in settings.admin_ids:
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return

    raw = (callback.data or "").removeprefix(keyboards.CB_PURGE_CONFIRM_PREFIX)
    try:
        loc_id = int(raw)
    except ValueError:
        await callback.answer()
        return

    # Capture count BEFORE deletion so the success message is accurate.
    count = db.count_orders_for_location(loc_id)
    result = db.purge_location(loc_id)
    if result == "not_found":
        await callback.answer("یافت نشد", show_alert=True)
        return

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            texts.PURGE_DONE.format(id=loc_id, count=count), reply_markup=None
        )
    await callback.answer("حذف شد ✅")


@router.callback_query(F.data == keyboards.CB_PURGE_CANCEL)
async def cb_purge_cancel(callback: CallbackQuery) -> None:
    if isinstance(callback.message, Message):
        await callback.message.edit_text(texts.PURGE_CANCELLED, reply_markup=None)
    await callback.answer()


@router.message(Command("togglelocation"))
async def cmd_togglelocation(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.TOGGLE_LOC_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return

    new_state = not loc.enabled
    db.set_location_enabled(loc_id, new_state)
    await message.answer(
        texts.TOGGLE_LOC_OK.format(id=loc_id, state="فعال" if new_state else "غیرفعال")
    )


# ---------- pending orders ----------
@router.message(Command("togglepurchase"))
async def cmd_togglepurchase(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    if not await guard_admin_message(message, settings, db, LOCATIONS):
        return

    raw = (command.args or "").strip()
    try:
        loc_id = int(raw)
    except ValueError:
        await message.answer(texts.TOGGLE_PURCHASE_USAGE)
        return

    loc = db.get_location(loc_id)
    if loc is None:
        await message.answer(texts.DEL_LOC_NOTFOUND)
        return
    if loc.is_test:
        await message.answer("لوکیشن تست — خرید از فروشگاه غیرفعال است.")
        return

    new_state = not loc.purchase_enabled
    db.set_location_purchase_enabled(loc_id, new_state)
    await message.answer(
        texts.TOGGLE_PURCHASE_OK.format(
            id=loc_id,
            name=escape(loc.name),
            state="باز" if new_state else "بسته",
        )
    )


@router.message(Command("pending"))
async def cmd_pending(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, ORDERS_REVIEW):
        return
    if message.from_user is None:
        return
    await send_pending_list(message, settings, db, message.from_user.id)


# ---------- panel sync (manual client deletion on 3x-ui) ----------
@router.message(Command("clearorder"))
async def cmd_clearorder(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    """Hard-delete one order from the database."""
    if not await guard_admin_message(message, settings, db, ORDERS_MANAGE):
        return

    raw = (command.args or "").strip()
    try:
        order_id = int(raw)
    except ValueError:
        await message.answer(texts.CLEAR_ORDER_USAGE)
        return

    if not db.delete_order(order_id):
        await message.answer(texts.CLEAR_ORDER_NOTFOUND)
        return
    await message.answer(texts.CLEAR_ORDER_OK.format(id=order_id))


@router.message(Command("cleardeclined"))
async def cmd_cleardeclined(message: Message, settings: Settings, db: Database) -> None:
    if not await guard_admin_message(message, settings, db, TOOLS_SYNC):
        return
    await message.answer(run_clear_declined(db))


@router.message(Command("syncpanel"))
async def cmd_syncpanel(
    message: Message, command: CommandObject, settings: Settings, db: Database
) -> None:
    """Compare bot DB with panel /clients/list and clear orphaned orders."""
    if not await guard_admin_message(message, settings, db, TOOLS_SYNC):
        return

    raw = (command.args or "").strip()
    loc_filter: int | None = None
    if raw:
        try:
            loc_filter = int(raw)
        except ValueError:
            await message.answer(texts.SYNC_PANEL_USAGE)
            return
        if db.get_location(loc_filter) is None:
            await message.answer(texts.DEL_LOC_NOTFOUND)
            return

    await message.answer(texts.SYNC_PANEL_START)
    for chunk in await run_sync_panel(db, loc_filter):
        await message.answer(chunk)
