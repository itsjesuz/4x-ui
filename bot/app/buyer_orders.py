"""Which orders buyers see in «سرویس‌های من» (hide ended test subs)."""

from __future__ import annotations

from datetime import datetime, timezone

from app import texts
from app.db import Database
from app.xui import ClientUsage, XuiClient, XuiError


def is_test_order(row) -> bool:
    return bool(row["is_test"]) if "is_test" in row.keys() else False


def is_admin_manual_panel_only(row) -> bool:
    return (
        bool(row["admin_manual_only"])
        if "admin_manual_only" in row.keys()
        else False
    )


def _parse_sqlite_utc(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts.strip(), "%Y-%m-%d %H:%M:%S").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


def test_ended_by_db_clock(row) -> bool:
    """True if test provision time is past TEST_DURATION_HOURS (no panel call)."""
    raw = row["updated_at"] if row["updated_at"] else row["created_at"]
    dt = _parse_sqlite_utc(str(raw))
    if dt is None:
        return False
    age_s = (datetime.now(timezone.utc) - dt).total_seconds()
    return age_s >= texts.TEST_DURATION_HOURS * 3600


def test_ended_sync(row) -> bool:
    """Heuristics without calling the panel."""
    if not is_test_order(row):
        return False
    if str(row["status"]) != "provisioned":
        return True
    if not row["xui_email"]:
        return True
    return test_ended_by_db_clock(row)


def test_ended_with_usage(usage: ClientUsage) -> bool:
    return usage.is_service_ended()


async def is_visible_to_buyer(db: Database, row) -> bool:
    """Whether this order should appear in the buyer's service list / detail."""
    if str(row["status"]) == "completed_renewal":
        return False
    if is_admin_manual_panel_only(row):
        return False
    if not is_test_order(row):
        return True
    if test_ended_sync(row):
        return False

    email = row["xui_email"]
    if not email:
        return False

    location = db.get_location(int(row["location_id"]))
    if location is None:
        return test_ended_by_db_clock(row)

    try:
        async with XuiClient(location.base_url, location.api_token) as xui:
            usage = await xui.get_usage(str(email))
    except XuiError:
        return not test_ended_by_db_clock(row)

    return not test_ended_with_usage(usage)


async def filter_visible_orders(db: Database, rows: list) -> list:
    visible: list = []
    for row in rows:
        if await is_visible_to_buyer(db, row):
            visible.append(row)
    return visible
