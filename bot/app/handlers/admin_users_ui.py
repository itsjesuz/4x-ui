"""Format admin «کاربران» list and user detail (Telegram ↔ panel clients)."""

from __future__ import annotations

from html import escape
import math
import time

from app import texts
from app.db import Database
from app.xui import ClientUsage, XuiClient, XuiError

ADMIN_USERS_PER_PAGE = 8


def _user_display_name(row) -> str:
    last = None
    try:
        last = row["last_name"]
    except (IndexError, KeyError):
        pass
    parts = [row["first_name"], last]
    name = " ".join(p for p in parts if p).strip()
    if not name:
        try:
            name = row["username"] or ""
        except (IndexError, KeyError):
            name = ""
        name = name.strip()
    if not name:
        name = str(row["user_id"])
    return escape(name)


def panel_live_badge(usage: ClientUsage | None, *, db_status: str) -> str:
    """Badge from DB status, or live panel usage when order is provisioned."""
    if db_status != "provisioned":
        return texts.STATUS_BADGE.get(db_status, escape(db_status))
    if usage is None:
        return texts.STATUS_BADGE["provisioned"]

    now_ms = int(time.time() * 1000)
    if usage.expiry_time_ms > 0 and now_ms >= usage.expiry_time_ms:
        return texts.PANEL_BADGE_EXPIRED
    if not usage.is_unlimited_traffic and usage.remaining_bytes <= 0:
        return texts.PANEL_BADGE_QUOTA_DONE
    if not usage.enable:
        return texts.PANEL_BADGE_DISABLED
    return texts.STATUS_BADGE["provisioned"]


async def load_panel_usage_for_orders(
    db: Database, orders: list
) -> dict[str, ClientUsage]:
    """Fetch live usage for provisioned clients, grouped by location (one list/location)."""
    by_loc: dict[int, set[str]] = {}
    for o in orders:
        email = o["xui_email"]
        if not email or str(o["status"]) != "provisioned":
            continue
        try:
            loc_id = int(o["location_id"])
        except (KeyError, TypeError, ValueError):
            continue
        by_loc.setdefault(loc_id, set()).add(str(email))

    merged: dict[str, ClientUsage] = {}
    for loc_id, emails in by_loc.items():
        loc = db.get_location(loc_id)
        if loc is None:
            continue
        try:
            async with XuiClient(loc.base_url, loc.api_token) as xui:
                merged.update(await xui.usage_for_emails(emails))
        except XuiError:
            continue
    return merged


def _format_order_line(
    order, *, usage: ClientUsage | None = None
) -> str:
    status = panel_live_badge(usage, db_status=str(order["status"]))
    email = order["xui_email"]
    if email:
        panel_line = texts.ADMIN_USER_ORDER_PANEL.format(email=escape(str(email)))
    else:
        panel_line = texts.ADMIN_USER_ORDER_NO_PANEL
    return texts.ADMIN_USER_ORDER_LINE.format(
        order_id=order["id"],
        status=status,
        location=escape(str(order["location_name"])),
        volume=int(order["volume_gb"]),
        days=int(order["duration_days"]),
        price=texts.format_price(int(order["price"])),
        panel_line=panel_line,
    )


def _panel_client_summary(
    order, usage: ClientUsage | None
) -> str:
    st = panel_live_badge(usage, db_status=str(order["status"]))
    loc = escape(str(order["location_name"]))
    line = (
        f"   🆔 <code>{escape(str(order['xui_email']))}</code> · "
        f"{st} · {loc}"
    )
    if usage is not None and str(order["status"]) == "provisioned":
        if usage.is_unlimited_traffic:
            used = texts.format_bytes(usage.used_bytes)
            line += f" · مصرف {used}"
        else:
            line += (
                f" · {texts.format_bytes(usage.used_bytes)}/"
                f"{texts.format_bytes(usage.total_bytes)}"
            )
    return line


async def format_users_page(db: Database, page: int = 0) -> tuple[str, int, list]:
    """Return (message_html, total_pages, users_on_page)."""
    total = db.count_users()
    if total == 0:
        return texts.ADMIN_USERS_EMPTY, 1, []

    per_page = ADMIN_USERS_PER_PAGE
    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    users = db.list_users_paginated(page * per_page, per_page)

    all_orders: list = []
    orders_by_user: dict[int, list] = {}
    for u in users:
        uid = int(u["user_id"])
        orders = db.list_user_orders_admin(uid, limit=20)
        orders_by_user[uid] = orders
        all_orders.extend(orders)

    usage_map = await load_panel_usage_for_orders(db, all_orders)

    lines = [
        texts.ADMIN_USERS_HEADER.format(
            page=page + 1,
            pages=total_pages,
            total=total,
        ),
        "",
    ]

    for u in users:
        username = f"@{u['username']}" if u["username"] else "—"
        ban = "🚫 مسدود" if bool(u["is_banned"]) else "✅ فعال"
        orders = orders_by_user[int(u["user_id"])]
        with_panel = [o for o in orders if o["xui_email"]]

        lines.append(
            f"▸ <b>{_user_display_name(u)}</b> ({username}) — <code>{u['user_id']}</code> {ban}"
        )
        if with_panel:
            for o in with_panel[:4]:
                email = str(o["xui_email"])
                lines.append(
                    _panel_client_summary(o, usage_map.get(email))
                )
            if len(with_panel) > 4:
                lines.append(f"   <i>+{len(with_panel) - 4} کلاینت دیگر…</i>")
        elif orders:
            lines.append(f"   <i>{len(orders)} سفارش — هنوز کلاینت پنل ندارد</i>")
        else:
            lines.append("   <i>بدون سفارش</i>")
        lines.append("")

    return "\n".join(lines).rstrip(), total_pages, users


async def format_user_detail(db: Database, user_id: int) -> str | None:
    row = db.get_user(user_id)
    if row is None:
        return None

    username = f"@{row['username']}" if row["username"] else "—"
    ban_state = "مسدود 🚫" if bool(row["is_banned"]) else "فعال ✅"
    orders = db.list_user_orders_admin(user_id, limit=30)
    usage_map = await load_panel_usage_for_orders(db, orders)

    if orders:
        order_lines = [
            _format_order_line(
                o, usage=usage_map.get(str(o["xui_email"])) if o["xui_email"] else None
            )
            for o in orders
        ]
        orders_block = "\n".join(order_lines)
    else:
        orders_block = texts.ADMIN_USER_NO_ORDERS

    return texts.ADMIN_USER_DETAIL.format(
        user_id=user_id,
        full_name=_user_display_name(row),
        username=username,
        created_at=escape(str(row["created_at"])),
        ban_state=ban_state,
        order_count=len(orders),
        orders_block=orders_block,
    )
