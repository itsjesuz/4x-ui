"""Admin «مشتریان» — buyers with orders, search, rich detail."""

from __future__ import annotations

from html import escape
import math

from app import texts
from app.db import Database
from app.handlers.admin_users_ui import (
    _panel_client_summary,
    _user_display_name,
    load_panel_usage_for_orders,
    panel_live_badge,
)
from app.xui import ClientUsage

ADMIN_CUSTOMERS_PER_PAGE = 8


def _username_label(row) -> str:
    return f"@{row['username']}" if row["username"] else "—"


def _is_test_order(row) -> bool:
    return bool(row["is_test"]) if "is_test" in row.keys() else False


def _format_customer_list_line(row) -> str:
    ban = "🚫" if bool(row["is_banned"]) else "✅"
    spent = texts.format_price(int(row["total_spent"] or 0))
    last = escape(str(row["last_order_at"] or "—"))
    return texts.ADMIN_CUSTOMER_LIST_LINE.format(
        full_name=_user_display_name(row),
        username=_username_label(row),
        user_id=row["user_id"],
        ban=ban,
        order_count=int(row["order_count"]),
        total_spent=spent,
        provisioned=int(row["provisioned_count"] or 0),
        last_order=last,
    )


def _format_usage_compact(usage: ClientUsage) -> str:
    if usage.is_unlimited_traffic:
        return f"مصرف {texts.format_bytes(usage.used_bytes)}"
    return (
        f"مصرف {texts.format_bytes(usage.used_bytes)}"
        f"/{texts.format_bytes(usage.total_bytes)}"
        f" · باقی {texts.format_bytes(usage.remaining_bytes)}"
    )


def _format_customer_order_line(
    order, *, usage: ClientUsage | None = None
) -> str:
    status = panel_live_badge(usage, db_status=str(order["status"]))
    is_test = _is_test_order(order)
    test_mark = " 🧪" if is_test else ""
    vol = texts.format_order_volume(int(order["volume_gb"]), is_test=is_test)
    duration = texts.format_order_duration(
        int(order["duration_days"]), is_test=is_test
    )
    price = texts.format_price(int(order["price"]))
    created_at = escape(str(order["created_at"]))

    plan_parts = [vol, duration, price]
    if order["nickname"]:
        plan_parts.insert(0, escape(str(order["nickname"])))
    plan_detail = " · ".join(plan_parts)

    footer_lines: list[str] = []
    if order["xui_email"]:
        footer_lines.append(f"پنل <code>{escape(str(order['xui_email']))}</code>")
    elif str(order["status"]) != "declined":
        footer_lines.append("<i>پنل: هنوز ساخته نشده</i>")

    if usage is not None and str(order["status"]) == "provisioned":
        footer_lines.append(_format_usage_compact(usage))

    if order["xui_sub_id"]:
        footer_lines.append(
            texts.ADMIN_CUSTOMER_ORDER_SUB.format(
                sub_id=escape(str(order["xui_sub_id"]))
            )
        )

    review_bits: list[str] = []
    if order["admin_id"]:
        review_bits.append(
            texts.ADMIN_CUSTOMER_ORDER_REVIEWER.format(
                reviewer=f"<code>{int(order['admin_id'])}</code>"
            )
        )
    if order["screenshot_file_id"]:
        review_bits.append(texts.ADMIN_CUSTOMER_ORDER_RECEIPT)
    if review_bits:
        footer_lines.append(" · ".join(review_bits))

    if order["decline_reason"]:
        footer_lines.append(
            texts.ADMIN_CUSTOMER_ORDER_DECLINE.format(
                decline=escape(str(order["decline_reason"]))
            )
        )

    footer = "\n".join(footer_lines)
    if footer:
        footer += "\n"

    return texts.ADMIN_CUSTOMER_ORDER_BLOCK.format(
        order_id=order["id"],
        test_mark=test_mark,
        status=status,
        location=escape(str(order["location_name"])),
        plan_detail=plan_detail,
        created_at=created_at,
        footer=footer,
    )


async def format_customers_page(
    db: Database, page: int = 0
) -> tuple[str, int, list]:
    total = db.count_customers()
    if total == 0:
        return texts.ADMIN_CUSTOMERS_EMPTY, 1, []

    per_page = ADMIN_CUSTOMERS_PER_PAGE
    total_pages = max(1, math.ceil(total / per_page))
    page = max(0, min(page, total_pages - 1))
    customers = db.list_customers_paginated(page * per_page, per_page)

    all_orders: list = []
    orders_by_user: dict[int, list] = {}
    for c in customers:
        uid = int(c["user_id"])
        orders = db.list_user_orders_admin(uid, limit=20, exclude_test=True)
        orders_by_user[uid] = orders
        all_orders.extend(orders)

    usage_map = await load_panel_usage_for_orders(db, all_orders)

    lines = [
        texts.ADMIN_CUSTOMERS_HEADER.format(
            page=page + 1,
            pages=total_pages,
            total=total,
        ),
        "",
    ]

    for c in customers:
        lines.append("<blockquote>")
        lines.append(_format_customer_list_line(c))
        uid = int(c["user_id"])
        with_panel = [o for o in orders_by_user[uid] if o["xui_email"]]
        if with_panel:
            for o in with_panel[:3]:
                email = str(o["xui_email"])
                lines.append(_panel_client_summary(o, usage_map.get(email)))
            if len(with_panel) > 3:
                lines.append(f"   <i>+{len(with_panel) - 3} سرویس پنل دیگر…</i>")
        lines.append("</blockquote>")
        lines.append("")

    return "\n".join(lines).rstrip(), total_pages, customers


async def format_customers_search_results(
    db: Database, query: str
) -> tuple[str, list]:
    rows = db.search_customers(query, limit=15)
    if not rows:
        return texts.ADMIN_CUSTOMERS_SEARCH_EMPTY.format(
            query=escape(query)
        ), []

    lines = [
        texts.ADMIN_CUSTOMERS_SEARCH_HEADER.format(
            query=escape(query),
            count=len(rows),
        ),
        "",
    ]
    for r in rows:
        lines.append("<blockquote>")
        lines.append(_format_customer_list_line(r))
        lines.append("</blockquote>")
        lines.append("")

    return "\n".join(lines).rstrip(), rows


async def format_customer_detail(db: Database, user_id: int) -> str | None:
    row = db.get_user(user_id)
    stats = db.get_customer_order_stats(user_id)
    if row is None or stats is None:
        return None

    username = _username_label(row)
    ban_state = "مسدود" if bool(row["is_banned"]) else "فعال"
    orders = db.list_user_orders_admin(user_id, limit=50, exclude_test=True)
    usage_map = await load_panel_usage_for_orders(db, orders)

    if orders:
        order_lines = [
            _format_customer_order_line(
                o,
                usage=usage_map.get(str(o["xui_email"])) if o["xui_email"] else None,
            )
            for o in orders
        ]
        orders_block = "\n".join(order_lines)
    else:
        orders_block = texts.ADMIN_CUSTOMER_NO_ORDERS

    text = texts.ADMIN_CUSTOMER_DETAIL.format(
        user_id=user_id,
        full_name=_user_display_name(row),
        username=username,
        created_at=escape(str(row["created_at"])),
        ban_state=ban_state,
        total_orders=int(stats["total_orders"]),
        declined=int(stats["declined"]),
        awaiting_review=int(stats["awaiting_review"]),
        provisioned=int(stats["provisioned"]),
        awaiting_payment=int(stats["awaiting_payment"]),
        paid_revenue=texts.format_price(int(stats["paid_revenue"] or 0)),
        total_spent=texts.format_price(int(stats["total_spent"] or 0)),
        first_order=escape(str(stats["first_order_at"])),
        last_order=escape(str(stats["last_order_at"])),
        order_count=len(orders),
        orders_block=orders_block,
    )
    if len(text) > 4000:
        shown = min(len(orders), 15)
        order_lines = order_lines[:shown]
        orders_block = "\n".join(order_lines)
        if len(orders) > shown:
            orders_block += f"\n\n<i>+{len(orders) - shown} سفارش دیگر…</i>"
        text = texts.ADMIN_CUSTOMER_DETAIL.format(
            user_id=user_id,
            full_name=_user_display_name(row),
            username=username,
            created_at=escape(str(row["created_at"])),
            ban_state=ban_state,
            total_orders=int(stats["total_orders"]),
            declined=int(stats["declined"]),
            awaiting_review=int(stats["awaiting_review"]),
            provisioned=int(stats["provisioned"]),
            awaiting_payment=int(stats["awaiting_payment"]),
            paid_revenue=texts.format_price(int(stats["paid_revenue"] or 0)),
            total_spent=texts.format_price(int(stats["total_spent"] or 0)),
            first_order=escape(str(stats["first_order_at"])),
            last_order=escape(str(stats["last_order_at"])),
            order_count=len(orders),
            orders_block=orders_block,
        )
    return text
