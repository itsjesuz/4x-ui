"""Shared helpers for admin commands and admin panel UI."""

from __future__ import annotations

from html import escape

from aiogram.types import CallbackQuery, Message

from app import texts
from app.admin_perms import (
    can_access_panel,
    get_role,
    has_permission,
    is_staff,
)
from app.config import Settings
from app.db import Database, Location
from app.xui import XuiClient, XuiError, _usage_from_client


def is_admin(user_id: int, settings: Settings) -> bool:
    """Listed in ADMIN_IDS (staff). Use has_permission() for actions."""
    return is_staff(user_id, settings)


def admin_from_message(message: Message, settings: Settings) -> bool:
    return message.from_user is not None and is_admin(message.from_user.id, settings)


def admin_can(
    user_id: int | None, perm: str, settings: Settings, db: Database
) -> bool:
    if user_id is None:
        return False
    return has_permission(user_id, perm, settings, db)


def admin_panel_access(
    user_id: int | None, settings: Settings, db: Database
) -> bool:
    if user_id is None:
        return False
    return can_access_panel(user_id, settings, db)


async def guard_admin_message(
    message: Message, settings: Settings, db: Database, perm: str
) -> bool:
    """Return True if the sender may run an admin command requiring ``perm``."""
    user = message.from_user
    if user is None or not is_staff(user.id, settings):
        await message.answer(texts.NOT_ADMIN)
        return False
    if not has_permission(user.id, perm, settings, db):
        await message.answer(texts.NOT_PERMITTED)
        return False
    return True


async def guard_admin_callback(
    callback: CallbackQuery, settings: Settings, db: Database, perm: str
) -> bool:
    user = callback.from_user
    if user is None or not is_staff(user.id, settings):
        await callback.answer(texts.NOT_ADMIN, show_alert=True)
        return False
    if not has_permission(user.id, perm, settings, db):
        await callback.answer(texts.NOT_PERMITTED, show_alert=True)
        return False
    return True


def format_role_label(user_id: int, settings: Settings, db: Database) -> str:
    from app import texts

    role = get_role(user_id, settings, db)
    return texts.ADMIN_ROLE_LABELS.get(role, role)


def normalize_panel_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if url.endswith("/panel"):
        url = url[: -len("/panel")]
    return url


def location_pricing_label(db: Database, loc) -> str:
    base, per_gb, per_day = db.get_pricing_for_location(loc.id)
    uses_global = (
        loc.price_base is None
        and loc.price_per_gb is None
        and loc.price_per_day is None
    )
    tag = "پیش‌فرض" if uses_global else "اختصاصی"
    return f"{tag} — {texts.format_pricing_formula(base, per_gb, per_day)}"


def format_stats_text(db: Database) -> str:
    return texts.ADMIN_STATS.format(
        users=db.count_users(),
        orders=db.count_orders(),
        awaiting_payment=db.count_orders_by_status("awaiting_payment"),
        awaiting_review=db.count_orders_by_status("awaiting_review"),
        provisioned=db.count_orders_by_status("provisioned"),
        declined=db.count_orders_by_status("declined"),
        failed=db.count_orders_by_status("failed"),
        tickets=db.count_tickets(),
    )


def format_base_plans_text(db: Database) -> str:
    volumes = ", ".join(f"{g} GB" for g in db.get_volume_presets()) or "—"
    durations = ", ".join(f"{d} روز" for d in db.get_duration_presets()) or "—"
    return texts.ADMIN_PLANS_HEADER.format(volumes=volumes, durations=durations)


def format_settings_text(db: Database) -> str:
    from app.pricing import describe_offer

    base, per_gb, per_day = db.get_pricing()
    return texts.ADMIN_SETTINGS_VIEW.format(
        card_number=escape(
            texts.format_card_number(db.get_setting("card_number", "—") or "—")
        ),
        card_holder=escape(db.get_setting("card_holder", "—") or "—"),
        base=base,
        per_gb=per_gb,
        per_day=per_day,
        offer_desc=describe_offer(db.get_offer_config()),
    )


async def sync_location_orders(
    db: Database, loc: Location
) -> tuple[list[int], list[int], str | None]:
    """Return (orphan_deleted_ids, test_panel_cleaned_ids, error_message)."""
    try:
        async with XuiClient(loc.base_url, loc.api_token) as xui:
            clients = await xui.list_clients()

            clients_by_email: dict[str, dict] = {}
            for c in clients:
                em = c.get("email")
                if em:
                    clients_by_email[str(em)] = c

            panel_emails = set(clients_by_email)
            orphan_deleted: list[int] = []
            test_panel_cleaned: list[int] = []

            for row in db.list_provisioned_orders(location_id=loc.id):
                email = row["xui_email"]
                if not email:
                    continue
                email = str(email)
                oid = int(row["id"])
                is_test = bool(row["is_test"]) if "is_test" in row.keys() else False

                if is_test:
                    if email not in panel_emails:
                        continue
                    usage = _usage_from_client(clients_by_email[email])
                    if not usage.is_service_ended():
                        continue
                    try:
                        await xui.delete_client(email, keep_traffic=1)
                    except XuiError:
                        continue
                    if db.detach_test_order_from_panel(oid):
                        test_panel_cleaned.append(oid)
                    continue

                if email not in panel_emails:
                    if db.delete_order(oid):
                        orphan_deleted.append(oid)

            return orphan_deleted, test_panel_cleaned, None
    except XuiError as exc:
        return [], [], str(exc)


async def run_sync_panel(
    db: Database, loc_filter: int | None = None
) -> list[str]:
    """Messages to send after a panel sync (excluding the initial 'started' line)."""
    locations = db.list_locations(only_enabled=False)
    if loc_filter is not None:
        loc = db.get_location(loc_filter)
        locations = [loc] if loc else []

    all_orphans: list[int] = []
    all_test_cleaned: list[int] = []
    out: list[str] = []
    for loc in locations:
        if loc is None:
            continue
        orphans, test_cleaned, err = await sync_location_orders(db, loc)
        if err:
            out.append(
                texts.SYNC_PANEL_LOC_ERR.format(
                    id=loc.id, name=escape(loc.name), error=escape(err)
                )
            )
            continue
        all_orphans.extend(orphans)
        all_test_cleaned.extend(test_cleaned)

    declined_deleted = db.delete_orders_by_status("declined")
    if not all_orphans and not all_test_cleaned and declined_deleted == 0:
        out.append(texts.SYNC_PANEL_NONE.format(declined=0))
    else:
        orphan_ids = ", ".join(str(i) for i in all_orphans) if all_orphans else "—"
        test_ids = (
            ", ".join(str(i) for i in all_test_cleaned) if all_test_cleaned else "—"
        )
        out.append(
            texts.SYNC_PANEL_DONE.format(
                orphan_count=len(all_orphans),
                orphan_ids=orphan_ids,
                test_cleaned_count=len(all_test_cleaned),
                test_cleaned_ids=test_ids,
                declined=declined_deleted,
            )
        )
    return out


def run_clear_declined(db: Database) -> str:
    declined = db.delete_orders_by_status("declined")
    unpaid = db.delete_orders_by_status("awaiting_payment")
    total = declined + unpaid
    if total == 0:
        return texts.CLEAR_DECLINED_NONE
    return texts.CLEAR_DECLINED_OK.format(
        declined=declined, unpaid=unpaid, total=total
    )
