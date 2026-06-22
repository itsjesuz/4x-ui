"""Post structured events to the admin-configured Telegram log channel."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from html import escape
from aiogram import Bot
from aiogram.enums import ChatType
from aiogram.types import Message, MessageOriginChannel, User
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from app.db import Database

_CAPTION_MAX = 1024
_MESSAGE_MAX = 4096


def _fit_message(text: str) -> str:
    if len(text) <= _MESSAGE_MAX:
        return text
    return text[: _MESSAGE_MAX - 20] + "\n\n<i>… (متن کوتاه شد)</i>"


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Actor:
    user_id: int
    full_name: str
    username: str | None

    @classmethod
    def from_user(cls, user: User | None) -> Actor | None:
        if user is None:
            return None
        name = " ".join(p for p in [user.first_name, user.last_name] if p) or "—"
        return cls(user_id=user.id, full_name=name, username=user.username)

    def html_line(self) -> str:
        uname = f"@{escape(self.username)}" if self.username else "—"
        return (
            f"<a href='tg://user?id={self.user_id}'>{escape(self.full_name)}</a> "
            f"(<code>{self.user_id}</code>) · {uname}"
        )


def _order_detail_block(
    *,
    order_id: int,
    location: str,
    volume_gb: int,
    duration_days: int,
    price: int,
    is_test: bool = False,
    status: str | None = None,
) -> str:
    from app import texts

    vol = escape(texts_format_volume(volume_gb, is_test))
    duration = escape(
        texts.format_order_duration(duration_days, is_test=is_test)
    )
    lines = [
        f"🆔 سفارش: <code>#{order_id}</code>",
        f"📍 لوکیشن: <b>{escape(location)}</b>",
        f"💾 حجم: <b>{vol}</b>",
        f"📅 مدت: <b>{duration}</b>",
        f"💰 مبلغ: <b>{_format_price(price)}</b>",
    ]
    if is_test:
        lines.append("🧪 <i>سرویس تست</i>")
    if status:
        lines.append(f"📌 وضعیت: <code>{escape(status)}</code>")
    return "\n".join(lines)


def texts_format_volume(volume_gb: int, is_test: bool) -> str:
    from app import texts

    if is_test:
        return texts.format_test_volume()
    return f"{volume_gb} گیگابایت"


def _format_price(toman: int) -> str:
    from app import texts

    return texts.format_price(toman)


def _blockquote(body: str) -> str:
    """Telegram HTML block quote for log detail sections."""
    stripped = (body or "").strip()
    if not stripped:
        return ""
    return f"<blockquote>{stripped}</blockquote>"


def _log_event(title: str, detail: str) -> str:
    """Log layout: title line, then quoted details."""
    detail = (detail or "").strip()
    if detail:
        return f"{title}\n\n{_blockquote(detail)}"
    return title


def _buyer_line(db: Database, user_id: int) -> str:
    row = db.get_user(user_id)
    if row is None:
        return f"<code>{user_id}</code>"
    try:
        last = row["last_name"]
    except (KeyError, IndexError):
        last = None
    name = " ".join(p for p in [row["first_name"], last] if p) or "—"
    uname = f"@{escape(row['username'])}" if row["username"] else "—"
    return (
        f"<a href='tg://user?id={user_id}'>{escape(name)}</a> "
        f"(<code>{user_id}</code>) · {uname}"
    )


def _order_manage_detail_block(db: Database, order) -> str:
    """Full order snapshot for admin action logs."""
    from app import texts

    order_id = int(order["id"])
    is_test = bool(order["is_test"]) if "is_test" in order.keys() else False
    status = texts.STATUS_BADGE.get(
        str(order["status"]), escape(str(order["status"]))
    )
    body = _order_detail_block(
        order_id=order_id,
        location=str(order["location_name"]),
        volume_gb=int(order["volume_gb"]),
        duration_days=int(order["duration_days"]),
        price=int(order["price"]),
        is_test=is_test,
        status=str(order["status"]),
    )
    nick = escape(str(order["nickname"])) if order["nickname"] else "—"
    panel = (
        f"<code>{escape(str(order['xui_email']))}</code>"
        if order["xui_email"]
        else "—"
    )
    sub = (
        f"<code>{escape(str(order['xui_sub_id']))}</code>"
        if order["xui_sub_id"]
        else "—"
    )
    return (
        f"{body}\n"
        f"🏷 نام: {nick}\n"
        f"👤 خریدار:\n{_buyer_line(db, int(order['user_id']))}\n"
        f"🆔 پنل: {panel}\n"
        f"🔔 subId: {sub}\n"
        f"📌 نمایش وضعیت: {status}\n"
        f"🕐 ایجاد: <code>{escape(str(order['created_at']))}</code>\n"
        f"🕑 بروزرسانی: <code>{escape(str(order['updated_at']))}</code>"
    )


class NetFlyLogger:
    """Send HTML log messages (and photos) to the configured channel."""

    def __init__(self, bot: Bot, db: Database) -> None:
        self._bot = bot
        self._db = db

    def channel_id(self) -> int | None:
        return self._db.get_log_channel_id()

    async def _send_text(self, text: str) -> bool:
        chat_id = self.channel_id()
        if chat_id is None:
            return False
        try:
            await self._bot.send_message(chat_id, _fit_message(text))
            return True
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Log channel send failed (%s): %s", chat_id, exc)
            return False
        except Exception:  # noqa: BLE001
            log.exception("Log channel send failed (%s)", chat_id)
            return False

    @staticmethod
    def _fit_caption(caption: str) -> str:
        if len(caption) <= _CAPTION_MAX:
            return caption
        return caption[: _CAPTION_MAX - 1] + "…"

    async def _send_photo(self, photo_file_id: str, caption: str) -> bool:
        chat_id = self.channel_id()
        if chat_id is None:
            return False
        try:
            await self._bot.send_photo(
                chat_id,
                photo=photo_file_id,
                caption=self._fit_caption(caption),
            )
            return True
        except (TelegramForbiddenError, TelegramBadRequest) as exc:
            log.warning("Log channel photo failed (%s): %s", chat_id, exc)
            return False
        except Exception:  # noqa: BLE001
            log.exception("Log channel photo failed (%s)", chat_id)
            return False

    async def log_order_awaiting_payment(
        self,
        *,
        order_id: int,
        buyer: Actor,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            status="awaiting_payment",
        )
        await self._send_text(
            _log_event(
                "🛒 <b>سفارش جدید — در انتظار پرداخت</b>",
                f"👤 خریدار:\n{buyer.html_line()}\n\n{body}",
            )
        )

    async def log_receipt_uploaded(
        self,
        *,
        order_id: int,
        buyer: Actor,
        photo_file_id: str,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            status="awaiting_review",
        )
        caption = _log_event(
            "💳 <b>رسید پرداخت دریافت شد</b>",
            f"👤 خریدار:\n{buyer.html_line()}\n\n{body}",
        )
        await self._send_photo(photo_file_id, caption)

    async def log_order_accepted(
        self,
        *,
        order_id: int,
        admin: Actor,
        buyer_id: int,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
        panel_email: str,
        is_test: bool = False,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            is_test=is_test,
            status="provisioned",
        )
        await self._send_text(
            _log_event(
                "✅ <b>سفارش تأیید و فعال شد</b>",
                f"👮 ادمین:\n{admin.html_line()}\n"
                f"👤 کاربر: <code>{buyer_id}</code>\n"
                f"🆔 پنل: <code>{escape(panel_email)}</code>\n\n{body}",
            )
        )

    async def log_order_provision_failed(
        self,
        *,
        order_id: int,
        admin: Actor,
        buyer_id: int,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
        error: str,
        is_test: bool = False,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            is_test=is_test,
            status="failed",
        )
        await self._send_text(
            _log_event(
                "⚠️ <b>تأیید شد — خطا در فعال‌سازی پنل</b>",
                f"👮 ادمین:\n{admin.html_line()}\n"
                f"👤 کاربر: <code>{buyer_id}</code>\n"
                f"❗ خطا: <code>{escape(error)}</code>\n\n{body}",
            )
        )

    async def log_order_declined(
        self,
        *,
        order_id: int,
        admin: Actor,
        buyer_id: int,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
        reason: str,
        is_test: bool = False,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            is_test=is_test,
            status="declined",
        )
        await self._send_text(
            _log_event(
                "❌ <b>سفارش رد شد</b>",
                f"👮 ادمین:\n{admin.html_line()}\n"
                f"👤 کاربر: <code>{buyer_id}</code>\n"
                f"📝 دلیل: {escape(reason)}\n\n{body}",
            )
        )

    async def log_test_service(
        self,
        *,
        order_id: int,
        user: Actor,
        location: str,
        panel_email: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        if success:
            await self._send_text(
                _log_event(
                    "🧪 <b>اشتراک تست فعال شد</b>",
                    f"👤 کاربر:\n{user.html_line()}\n"
                    f"🆔 سفارش: <code>#{order_id}</code>\n"
                    f"📍 لوکیشن: <b>{escape(location)}</b>\n"
                    f"🆔 پنل: <code>{escape(panel_email)}</code>",
                )
            )
        else:
            await self._send_text(
                _log_event(
                    "🧪 <b>اشتراک تست — خطا</b>",
                    f"👤 کاربر:\n{user.html_line()}\n"
                    f"🆔 سفارش: <code>#{order_id}</code>\n"
                    f"❗ خطا: <code>{escape(error or '—')}</code>",
                )
            )

    async def log_support_ticket(
        self,
        *,
        ticket_id: int,
        user: Actor,
        message: str,
    ) -> None:
        await self._send_text(
            _log_event(
                "💬 <b>تیکت پشتیبانی</b>",
                f"🎫 شماره: <code>#{ticket_id}</code>\n"
                f"👤 کاربر:\n{user.html_line()}\n\n"
                f"{escape(message)}",
            )
        )

    async def log_order_cancelled(
        self,
        *,
        order_id: int,
        user: Actor | None,
        had_receipt: bool,
    ) -> None:
        who = user.html_line() if user else "—"
        await self._send_text(
            _log_event(
                "🚫 <b>سفارش لغو شد (خریدار)</b>",
                f"🆔 سفارش: <code>#{order_id}</code>\n"
                f"👤 کاربر: {who}\n"
                f"رسید ارسال شده بود: <b>{'بله' if had_receipt else 'خیر'}</b>",
            )
        )

    async def log_manual_client_created(
        self,
        *,
        order_id: int,
        admin: Actor,
        location: str,
        volume_gb: int,
        duration_days: int,
        price: int,
        panel_email: str,
        buyer_id: int | None = None,
    ) -> None:
        body = _order_detail_block(
            order_id=order_id,
            location=location,
            volume_gb=volume_gb,
            duration_days=duration_days,
            price=price,
            status="provisioned",
        )
        if buyer_id is not None:
            user_line = f"👤 کاربر: <code>{buyer_id}</code>\n"
        else:
            user_line = "👤 کاربر: <i>— (فقط پنل)</i>\n"
        await self._send_text(
            _log_event(
                "➕ <b>ساخت دستی کلاینت</b>",
                f"👮 ادمین:\n{admin.html_line()}\n"
                f"{user_line}"
                f"🆔 پنل: <code>{escape(panel_email)}</code>\n\n{body}",
            )
        )

    async def _panel_live_line(self, order) -> str | None:
        if not order["xui_email"] or str(order["status"]) != "provisioned":
            return None
        loc = self._db.get_location(int(order["location_id"]))
        if loc is None:
            return None
        from app.xui import XuiClient, XuiError

        email = str(order["xui_email"])
        try:
            async with XuiClient(loc.base_url, loc.api_token) as xui:
                usage = await xui.get_usage(email)
        except XuiError as exc:
            return f"📊 پنل: <i>خطا — {escape(str(exc))}</i>"

        from app import texts
        from datetime import datetime, timezone

        used = texts.format_bytes(usage.used_bytes)
        if usage.is_unlimited_traffic:
            traffic = f"مصرف <b>{used}</b> (نامحدود)"
        else:
            total = texts.format_bytes(usage.total_bytes)
            remain = texts.format_bytes(usage.remaining_bytes)
            traffic = f"مصرف <b>{used}</b> / <b>{total}</b> · باقی <b>{remain}</b>"

        if usage.expiry_time_ms <= 0:
            expiry = texts.VIEW_USAGE_NEVER_EXPIRES
        else:
            dt = datetime.fromtimestamp(
                usage.expiry_time_ms / 1000, tz=timezone.utc
            )
            expiry = dt.strftime("%Y-%m-%d %H:%M UTC")

        enable = "فعال" if usage.enable else "غیرفعال"
        return f"📊 پنل (زنده): {traffic} · انقضا <code>{escape(expiry)}</code> · {enable}"

    async def log_admin_order_action(
        self,
        *,
        order_id: int,
        admin: Actor,
        action: str,
        order=None,
        notes: str | None = None,
        fetch_panel: bool = True,
    ) -> None:
        row = order if order is not None else self._db.get_order(order_id)
        detail_parts = [
            f"🆔 سفارش: <code>#{order_id}</code>",
            f"👮 ادمین:\n{admin.html_line()}",
            f"⚙️ عملیات: <b>{escape(action)}</b>",
        ]
        if notes:
            detail_parts.append(f"📝 جزئیات عملیات: {escape(notes)}")
        if row is not None:
            detail_parts.append(_order_manage_detail_block(self._db, row))
            if fetch_panel:
                panel_live = await self._panel_live_line(row)
                if panel_live:
                    detail_parts.append(panel_live)
        else:
            detail_parts.append(
                "<i>رکورد سفارش در ربات یافت نشد (احتمالاً حذف شده).</i>"
            )

        await self._send_text(
            _log_event(
                "🛠 <b>مدیریت سفارش توسط ادمین</b>",
                "\n".join(detail_parts),
            )
        )

    async def log_user_ban(
        self,
        *,
        admin: Actor,
        user: Actor,
        banned: bool,
    ) -> None:
        label = "مسدود شد 🚫" if banned else "رفع مسدودیت ✅"
        await self._send_text(
            _log_event(
                f"👮 <b>{label}</b>",
                f"ادمین:\n{admin.html_line()}\nکاربر:\n{user.html_line()}",
            )
        )

    async def log_broadcast_done(
        self,
        *,
        admin: Actor,
        total: int,
        ok: int,
        fail: int,
    ) -> None:
        await self._send_text(
            _log_event(
                "📣 <b>ارسال همگانی</b>",
                f"👮 ادمین:\n{admin.html_line()}\n"
                f"مخاطب: <b>{total}</b> · موفق: <b>{ok}</b> · ناموفق: <b>{fail}</b>",
            )
        )


def make_logger(bot: Bot, db: Database) -> NetFlyLogger:
    return NetFlyLogger(bot, db)


async def try_bind_log_channel(bot: Bot, db: Database, chat_id: int) -> tuple[bool, str]:
    """Save channel id and send a test message. Returns (ok, message_for_admin)."""
    from app import texts

    try:
        await bot.send_message(
            chat_id,
            texts.LOG_CHANNEL_TEST,
        )
    except TelegramForbiddenError:
        return False, texts.LOG_CHANNEL_FORBIDDEN
    except TelegramBadRequest as exc:
        return False, texts.LOG_CHANNEL_BAD.format(error=escape(str(exc)))
    except Exception as exc:  # noqa: BLE001
        log.exception("bind log channel %s", chat_id)
        return False, texts.LOG_CHANNEL_BAD.format(error=escape(str(exc)))

    db.set_log_channel_id(chat_id)
    return True, texts.LOG_CHANNEL_OK.format(chat_id=chat_id)


def resolve_forwarded_channel_id(message: Message) -> int | None:
    """Extract channel/supergroup id from a forwarded message (legacy + Bot API 7+)."""
    fwd = message.forward_from_chat
    if fwd is not None and fwd.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
        return int(fwd.id)

    origin = message.forward_origin
    if isinstance(origin, MessageOriginChannel):
        chat = origin.chat
        if chat.type in (ChatType.CHANNEL, ChatType.SUPERGROUP):
            return int(chat.id)
    return None
