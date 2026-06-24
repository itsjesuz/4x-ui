"""All Persian (Farsi) UI strings and constants in one place."""

from __future__ import annotations


# ---------- order presets (defaults until admin changes them in DB) ----------
DEFAULT_VOLUME_PRESETS_GB: list[int] = [1, 2, 5, 10]
DEFAULT_DURATION_PRESETS_DAYS: list[int] = [3, 7, 30]
# Back-compat aliases
VOLUME_PRESETS_GB = DEFAULT_VOLUME_PRESETS_GB
DURATION_PRESETS_DAYS = DEFAULT_DURATION_PRESETS_DAYS

CUSTOM_VOLUME_MIN_GB = 1
CUSTOM_VOLUME_MAX_GB = 500

# Free test subscription (one per user)
TEST_VOLUME_MB = 100
TEST_DURATION_HOURS = 5


# ---------- helpers ----------
def format_price(toman: int) -> str:
    return f"{toman:,} تومان"


def _truncate_btn(text: str, *, max_len: int = 64) -> str:
    return text if len(text) <= max_len else text[: max_len - 1] + "…"


def format_service_package_volume(volume_gb: int) -> str:
    """Right-hand button: e.g. 25 گیگابایت"""
    return _truncate_btn(f"{volume_gb} گیگابایت")


def format_service_package_term(duration_days: int, price: int) -> str:
    """Left-hand button: e.g. 30 روزه - 378,000 تومان (final price only)."""
    return _truncate_btn(f"{duration_days} روزه · {price:,}")


def format_card_number(card: str) -> str:
    """Digits only — no dashes or spaces (easier to copy in banking apps)."""
    return "".join(ch for ch in card if ch.isdigit()) or card


def format_payment_amount(toman: int) -> str:
    """Payment line: only the numeric amounts are monospace (easy to copy)."""
    rial = toman * 10
    return f"<code>{toman}</code> تومان یا <code>{rial}</code> ریال"


def calc_price(volume_gb: int, duration_days: int,
               base: int, per_gb: int, per_day: int) -> int:
    return int(base + per_gb * volume_gb + per_day * duration_days)


def format_pricing_formula(base: int, per_gb: int, per_day: int) -> str:
    return f"base {base:,} + {per_gb:,}/GB + {per_day:,}/day"


def format_bytes(n: int) -> str:
    """Render a byte count using GB/MB units (1024-based)."""
    if n <= 0:
        return "0 MB"
    if n >= 1024 ** 3:
        return f"{n / (1024 ** 3):.2f} GB"
    return f"{n / (1024 ** 2):.1f} MB"


# ---------- buttons ----------
BTN_BUY          = "🛒 خرید سرویس"
BTN_TEST_SUB     = "🧪 دریافت اشتراک تست"
BTN_MY_SERVICES  = "📊 سرویس‌های من"
BTN_MY_ACCOUNT   = "👤 حساب کاربری"
BTN_SUPPORT      = "💬 پشتیبانی"
BTN_HELP         = "❓ راهنما"
BTN_ABOUT        = "ℹ️ درباره ما"
BTN_BACK       = "🔙 بازگشت"
BTN_CANCEL     = "❌ انصراف"
BTN_CONFIRM    = "✅ تأیید و ادامه"
BTN_CUSTOM     = "✏️ مقدار دلخواه"
BTN_ACCEPT     = "✅ تأیید پرداخت"
BTN_DECLINE    = "❌ رد پرداخت"
BTN_VIEW_USER  = "👤 پروفایل کاربر"
BTN_USER_INFO   = "👤 شناسه کاربر"
ADMIN_USER_INFO_ALERT = (
    "شناسه: {user_id}\n"
    "نام: {full_name}\n"
    "یوزرنیم: {username}"
)
FORWARDED_USER_ID = (
    "👤 شناسه کاربر فورواردشده:\n"
    "<code>{user_id}</code>"
)
FORWARDED_USER_HIDDEN = (
    "شناسه این پیام قابل مشاهده نیست.\n"
    "کاربر ارسال‌کننده، نمایش مشخصات در فوروارد را محدود کرده است."
)
FORWARDED_CHAT_ID = (
    "این پیام از کاربر عادی فوروارد نشده است.\n"
    "شناسه مبدأ:\n"
    "<code>{chat_id}</code>"
)

# My services
BTN_VIEW_CONFIGS  = "📋 دریافت کانفیگ‌ها"
BTN_REFRESH_USAGE = "🔄 بروزرسانی مصرف"
BTN_TOGGLE_OFF   = "⏸ توقف موقت"
BTN_TOGGLE_ON    = "▶️ فعال‌سازی"
BTN_RENAME       = "✏️ تغییر نام"
BTN_REGEN        = "🔁 تغییر لینک ساب"
BTN_REGEN_CONFIRM = "✅ بله، تولید مجدد کن"


# ---------- my services ----------
MY_SERVICES_EMPTY = (
    "📊 <b>سرویس‌های من</b>\n\n"
    "هنوز هیچ سفارشی ثبت نکرده‌اید.\n"
    "برای خرید اولین سرویس، از منوی اصلی روی «خرید سرویس» بزنید."
)

MY_SERVICES_HEADER = (
    "📊 <b>سرویس‌های من</b>\n\n"
    "روی هر سرویس بزنید تا جزئیات و اقدامات آن را ببینید:"
)

# Status badges used in both list and detail
STATUS_BADGE = {
    "awaiting_payment": "💳 در انتظار پرداخت",
    "awaiting_review":  "⏳ در انتظار بررسی",
    "approved":         "✅ تأییدشده",
    "declined":         "❌ ردشده",
    "provisioned":      "🟢 فعال",
    "failed":           "⚠️ خطا",
    "expired":          "⏱ منقضی",
    "quota_exhausted":  "اتمام حجم 🔴",
}

# Live panel state (admin users list / detail when usage is fetched)
PANEL_BADGE_EXPIRED = "⏱ منقضی"
PANEL_BADGE_QUOTA_DONE = "اتمام حجم 🔴"
PANEL_BADGE_DISABLED = "⏸ غیرفعال در پنل"

SERVICE_LIST_ITEM = (
    "{status_emoji} #{id} — {location} — {volume}GB / {days}d{nickname_part}"
)

SERVICE_DETAIL = (
    "📦 <b>سرویس #{order_id}</b>{nickname_part}\n\n"
    "📍 لوکیشن: <b>{location}</b>\n"
    "💾 حجم سفارش: <b>{volume}</b>\n"
    "📅 مدت سفارش: <b>{duration}</b>\n"
    "💰 مبلغ: <b>{price}</b>\n"
    "🏷 وضعیت: <b>{status}</b>\n"
    "{panel_id_line}"
    "{usage_block}"
    "🗓 تاریخ ثبت: {created_at}"
)

SERVICE_DETAIL_USAGE_BLOCK = (
    "📊 <b>مصرف و اعتبار (زنده)</b>\n"
    "🔌 اتصال: <b>{enabled}</b>\n"
    "💾 مصرف: <b>{used}</b> از <b>{total}</b>\n"
    "📈 باقیمانده: <b>{remaining}</b>\n"
    "⏳ اعتبار تا: <b>{expiry}</b> ({time_left})\n\n"
)

SERVICE_DETAIL_USAGE_ERROR = (
    "📊 <b>مصرف و اعتبار</b>\n"
    "⚠️ دریافت از پنل ناموفق: <code>{error}</code>\n\n"
)

SERVICE_NOT_PROVISIONED_ACTIONS = (
    "\n\nℹ️ این سرویس هنوز فعال نشده، بنابراین گزینه‌های مدیریت در دسترس نیستند."
)

TEST_SERVICE_LIMITED = (
    "\n\n🧪 <i>سرویس تست — فقط مشاهده کانفیگ و مصرف؛ "
    "تغییر نام، توقف و تولید مجدد غیرفعال است.</i>"
)

TEST_SERVICE_ACTION_BLOCKED = (
    "🧪 این گزینه برای سرویس تست در دسترس نیست."
)

VIEW_CONFIGS_TITLE = (
    "🔗 <b>اطلاعات اتصال — سرویس #{order_id}</b>\n\n{configs_block}"
)

VIEW_USAGE_TITLE = (
    "📊 <b>وضعیت سرویس #{order_id}</b>\n\n"
    "🟢 وضعیت: <b>{enabled}</b>\n"
    "💾 مصرف: <b>{used}</b> از <b>{total}</b>\n"
    "📈 باقیمانده: <b>{remaining}</b>\n"
    "⏳ اعتبار تا: <b>{expiry}</b> ({time_left})"
)
VIEW_USAGE_UNLIMITED_TRAFFIC = "نامحدود"
VIEW_USAGE_NEVER_EXPIRES     = "بدون انقضا"
VIEW_USAGE_EXPIRED           = "منقضی شده"
VIEW_USAGE_ENABLED           = "فعال"
VIEW_USAGE_DISABLED          = "غیرفعال"
VIEW_USAGE_FETCH_FAILED      = (
    "⚠️ دریافت اطلاعات مصرف از پنل ممکن نشد:\n<code>{error}</code>\n\n"
    "ممکن است سرویس از پنل حذف شده باشد یا پنل در دسترس نباشد."
)

TOGGLE_OK_DISABLED = "⏸ سرویس #{order_id} موقتاً متوقف شد."
TOGGLE_OK_ENABLED  = "▶️ سرویس #{order_id} دوباره فعال شد."
TOGGLE_FAILED      = "⚠️ تغییر وضعیت ممکن نشد:\n<code>{error}</code>"

RENAME_PROMPT = (
    "✏️ <b>تغییر نام سرویس #{order_id}</b>\n\n"
    "یک نام کوتاه بفرستید (فقط حروف انگلیسی، عدد، <code>-</code> و <code>_</code>).\n"
    "مثال: <code>phone</code> → شناسه پنل: <code>nf{order_id}-phone</code>\n\n"
    "حداکثر ۳۰ کاراکتر. حذف نام محلی: <code>-</code>\n"
    "انصراف: /cancel"
)
RENAME_TOO_LONG = "❗ نام نباید بیشتر از ۳۰ کاراکتر باشد."
RENAME_INVALID_LABEL = (
    "❗ نام نامعتبر است.\n"
    "فقط حروف انگلیسی کوچک، عدد، خط‌تیره و زیرخط مجاز است."
)
RENAME_PANEL_FAILED = "⚠️ تغییر نام روی پنل ناموفق بود:\n<code>{error}</code>"
RENAME_OK = "✅ نام نمایشی سرویس به‌روز شد."
RENAME_OK_PANEL = (
    "✅ نام سرویس به‌روز شد.\n"
    "🏷 برچسب: <b>{label}</b>\n"
    "🆔 شناسه پنل: <code>{panel_id}</code>"
)
RENAME_CLEARED  = "✅ نام سرویس حذف شد."

REGEN_CONFIRM = (
    "⚠️ <b>تولید مجدد لینک‌ها</b>\n\n"
    "این کار:\n"
    "• سرویس فعلی روی پنل را <b>غیرفعال</b> می‌کند (لینک‌های فعلی دیگر کار نخواهند کرد)\n"
    "• یک سرویس جدید با ترافیک باقیمانده و همان تاریخ انقضا می‌سازد\n"
    "• شمارنده مصرف <b>صفر</b> می‌شود اما مهلت زمانی تغییر نمی‌کند\n\n"
    "این کار <b>قابل بازگشت نیست</b>. آیا مطمئن هستید؟"
)
REGEN_IN_PROGRESS = "⏳ در حال ساخت مجدد سرویس..."
REGEN_OK          = "🎉 سرویس با موفقیت بازسازی شد.\n\n{configs_block}"
REGEN_FAILED      = "⚠️ بازسازی ناموفق بود:\n<code>{error}</code>\n\nسرویس قبلی شما همچنان فعال است."
REGEN_NOT_SUPPORTED = (
    "ℹ️ این سرویس هنوز روی پنل ساخته نشده یا اطلاعات کافی ندارد."
)


# ---------- top-level messages ----------
WELCOME = (
    "🛡️ <b>به NetFly خوش آمدید</b>\n\n"
    "خرید و مدیریت آسان سرویس‌های پرسرعت و امن وی‌پی‌ان.\n\n"
    "جهت شروع، از دکمه‌های زیر استفاده کنید 👇"
)

TEST_SUB_CONFIRM = (
    "🧪 <b>اشتراک تست رایگان</b>\n\n"
    "📍 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume}</b>\n"
    "📅 مدت: <b>{duration}</b>\n"
    "💰 مبلغ: <b>رایگان</b>\n\n"
    "⚠️ هر کاربر فقط <b>یک‌بار</b> می‌تواند اشتراک تست دریافت کند.\n\n"
    "ادامه می‌دهید؟"
)
TEST_SUB_PROVISIONING = "⏳ در حال ساخت اشتراک تست روی پنل..."
TEST_SUB_OK = (
    "🎉 <b>اشتراک تست شما آماده است!</b>\n\n"
    "{configs_block}\n\n"
    "از «سرویس‌های من» می‌توانید مصرف و لینک‌ها را ببینید."
)
TEST_SUB_ALREADY_USED = (
    "ℹ️ شما قبلاً اشتراک تست دریافت کرده‌اید.\n"
    "برای سرویس کامل از «خرید سرویس» استفاده کنید."
)
TEST_SUB_DISABLED = (
    "ℹ️ اشتراک تست در حال حاضر غیرفعال است.\n"
    "بعداً دوباره امتحان کنید یا از «خرید سرویس» استفاده کنید."
)
TEST_SUB_NO_LOCATION = (
    "ℹ️ لوکیشن تست هنوز توسط ادمین تنظیم نشده است."
)
TEST_SUB_FAILED = (
    "⚠️ ساخت اشتراک تست ناموفق بود:\n<code>{error}</code>\n\n"
    "لطفاً بعداً دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
)

def format_test_volume() -> str:
    return f"{TEST_VOLUME_MB} مگابایت"


def format_test_duration() -> str:
    return f"{TEST_DURATION_HOURS} ساعت"


def format_order_duration(duration_days: int, *, is_test: bool = False) -> str:
    if is_test:
        return format_test_duration()
    return f"{duration_days} روز"


def format_order_volume(volume_gb: int, *, is_test: bool = False) -> str:
    if is_test:
        return format_test_volume()
    return f"{volume_gb} گیگابایت"

HELP = (
    "📖 <b>راهنمای استفاده از NetFly</b>\n\n"
    "<b>برای خرید:</b>\n"
    "۱) لوکیشن سرور را انتخاب کنید\n"
    "۲) حجم ترافیک را مشخص کنید (یا «مقدار دلخواه»)\n"
    "۳) مدت اعتبار را انتخاب کنید\n"
    "۴) پس از تأیید قیمت، مبلغ را به شماره کارت اعلام‌شده واریز کنید\n"
    "۵) اسکرین‌شات رسید را در ربات ارسال کنید\n"
    "۶) پس از تأیید توسط ادمین، لینک اتصال برای شما ارسال می‌شود\n\n"
    "دستورها:\n"
    "/start — منوی اصلی\n"
    "/help — همین راهنما\n"
    "/cancel — لغو عملیات در حال انجام"
)

ABOUT = (
    "ℹ️ <b>درباره NetFly</b>\n\n"
    "NetFly سرویس وی‌پی‌ان امن، سریع و پایدار با پشتیبانی ۲۴ ساعته است.\n\n"
    "✅ سرورهای پرسرعت در چند لوکیشن\n"
    "✅ بدون لاگ، با تضمین حریم خصوصی\n"
    "✅ پشتیبانی از تمامی پلتفرم‌ها"
)

ACCOUNT_INFO = (
    "👤 <b>حساب کاربری شما</b>\n\n"
    "شناسه عددی: <code>{user_id}</code>\n"
    "نام کاربری: {username}\n"
    "نام: {full_name}\n"
    "عضو از: {created_at}\n"
)


# ---------- order flow ----------
ORDER_PICK_LOCATION = "📍 <b>لوکیشن سرور را انتخاب کنید:</b>"

NO_LOCATIONS_USER = (
    "⛔ در حال حاضر هیچ لوکیشنی فعال نیست. لطفاً بعداً دوباره تلاش کنید "
    "یا با پشتیبانی در تماس باشید."
)

ORDER_PICK_PACKAGE = (
    "📦 لوکیشن: <b>{location}</b>\n\n"
    "📋 <b>پلن مورد نظر را انتخاب کنید:</b>"
)

ORDER_NO_PACKAGES = (
    "⛔ برای این لوکیشن هنوز پلنی تعریف نشده.\n"
    "لطفاً لوکیشن دیگری انتخاب کنید یا با پشتیبانی تماس بگیرید."
)

ORDER_PICK_VOLUME = (
    "📦 لوکیشن انتخاب‌شده: <b>{location}</b>\n\n"
    "💾 <b>حجم ترافیک را انتخاب کنید:</b>"
)

ORDER_ASK_CUSTOM_VOLUME = (
    "✏️ <b>حجم دلخواه</b>\n\n"
    "لطفاً عدد را به گیگابایت ارسال کنید "
    "(بین {min_gb} تا {max_gb} گیگابایت).\n\n"
    "مثال: <code>25</code>\n"
    "برای انصراف: /cancel"
)

ORDER_CUSTOM_VOLUME_INVALID = (
    "❗ لطفاً یک عدد صحیح بین {min_gb} تا {max_gb} وارد کنید."
)

ORDER_PICK_DURATION = (
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n\n"
    "📅 <b>مدت اعتبار را انتخاب کنید:</b>"
)

ORDER_REVIEW = (
    "🧾 <b>خلاصه سفارش</b>\n\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت اعتبار: <b>{days} روز</b>\n"
    "💰 مبلغ قابل پرداخت: <b>{price}</b>\n\n"
    "در صورت تأیید، دستور پرداخت برای شما ارسال می‌شود."
)

ORDER_PAYMENT_INSTRUCTIONS = (
    "💳 <b>دستور پرداخت — سفارش #{order_id}</b>\n\n"
    "لطفاً مبلغ {amount} را به کارت زیر واریز کنید:\n\n"
    "<code>{card_number}</code>\n"
    "به نام: <b>{card_holder}</b>\n\n"
    "✅ پس از واریز، <b>اسکرین‌شات رسید</b> را در همین چت ارسال کنید "
    "(به‌صورت عکس، نه فایل).\n\n"
    "⏳ پس از بررسی توسط ادمین، لینک اتصال برای شما ارسال خواهد شد.\n"
    "برای انصراف: /cancel"
)

ORDER_RECEIPT_NEED_PHOTO = (
    "❗ لطفاً <b>اسکرین‌شات رسید</b> را به‌صورت عکس ارسال کنید."
)

ORDER_RECEIPT_RECEIVED = (
    "✅ رسید شما دریافت شد و در حال بررسی توسط ادمین است.\n"
    "به‌محض تأیید، لینک اتصال برای شما ارسال می‌شود."
)

ORDER_DECLINED_NOTIFY = (
    "❌ <b>سفارش #{order_id} رد شد</b>\n\n"
    "{reason}\n\n"
    "در صورت سؤال، با پشتیبانی در تماس باشید."
)
ORDER_DECLINED_DEFAULT_REASON = "متأسفانه رسید پرداخت شما توسط ادمین تأیید نشد."

ORDER_PROVISIONED_NOTIFY = (
    "🎉 <b>سفارش #{order_id} با موفقیت فعال شد!</b>\n\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت اعتبار: <b>{days} روز</b>\n\n"
    "{configs_block}\n\n"
    "💡 پیشنهاد می‌شود از <b>لینک اشتراک</b> استفاده کنید — کافی است یک‌بار در "
    "اپلیکیشن وی‌پی‌ان وارد شود، کانفیگ‌ها به‌صورت خودکار به‌روزرسانی می‌شوند.\n"
    "اپلیکیشن‌های پیشنهادی: V2RayNG، NekoBox، v2rayN، Streisand."
)

ORDER_RENEWED_NOTIFY = (
    "♻️ <b>سفارش #{order_id} با موفقیت تمدید شد!</b>\n\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "➕ حجم اضافه‌شده: <b>{volume} گیگابایت</b>\n"
    "➕ مدت اضافه‌شده: <b>{days} روز</b>\n\n"
    "💡 سرویس شما در پنل به‌روز شد و نیازی به تغییر کانفیگ یا لینک اشتراک نیست."
)


def format_configs_block(sub_url: str | None, sub_links: list[str]) -> str:
    """Build the connection-info block used in both the order completion message
    and the My Services detail view.
    """
    parts: list[str] = []
    if sub_url:
        parts.append("🔔 <b>لینک اشتراک:</b>")
        parts.append(f"<code>{sub_url}</code>")
        parts.append("")
        
    if sub_links:
        total_len = sum(len(link) for link in sub_links)
        if total_len > 2500:
            if sub_url:
                parts.append("📋 <b>لینک‌های جداگانه:</b>\n<i>لینک‌ها به دلیل طولانی بودن مخفی شدند. لطفاً از <b>لینک اشتراک</b> استفاده کنید.</i>")
            else:
                parts.append("📋 <b>لینک‌های جداگانه:</b>")
                # Add as many as we can fit within ~2500 chars
                current_len = 0
                for link in sub_links:
                    if current_len + len(link) > 2500:
                        parts.append("<i>...سایر لینک‌ها به دلیل محدودیت تلگرام مخفی شدند...</i>")
                        break
                    parts.append(f"<code>{link}</code>")
                    current_len += len(link)
        else:
            parts.append("📋 <b>لینک‌های جداگانه:</b>")
            for link in sub_links:
                parts.append(f"<code>{link}</code>")
                
    if not parts:
        parts.append("—")
    return "\n".join(parts)

ORDER_PROVISION_FAILED_USER = (
    "⚠️ پرداخت شما تأیید شد، اما در ساخت کانفیگ روی پنل مشکلی پیش آمد. "
    "تیم پشتیبانی به‌زودی موضوع را پیگیری خواهد کرد."
)


# ---------- support ----------
SUPPORT_PROMPT = (
    "💬 <b>پشتیبانی NetFly</b>\n\n"
    "برای ارتباط با تیم پشتیبانی و پیگیری مشکلات، لطفاً از طریق ربات اختصاصی پشتیبانی ما اقدام کنید:"
)
SUPPORT_SENT     = "✅ پیام شما با موفقیت برای پشتیبانی ارسال شد. به‌زودی پاسخ خواهیم داد."
SUPPORT_TOO_LONG = "❗ پیام شما خیلی طولانی است. لطفاً آن را کوتاه‌تر کنید."
SUPPORT_EMPTY    = "❗ لطفاً یک پیام متنی ارسال کنید."
SUPPORT_ADMIN_REPLY = "💬 پاسخ"
SUPPORT_ADMIN_CLOSE = "✅ بستن"
SUPPORT_REPLY_PROMPT = (
    "💬 پاسخ تیکت <code>#{ticket_id}</code> را ارسال کنید.\n"
    "برای لغو /cancel را بفرستید."
)
SUPPORT_REPLY_SENT_ADMIN = "✅ پاسخ برای کاربر ارسال شد و تیکت بسته شد."
SUPPORT_REPLY_FAILED_USER = "❗ ارسال پاسخ به کاربر ممکن نشد. احتمالاً ربات را بلاک کرده است."
SUPPORT_REPLY_SENT_USER = (
    "💬 <b>پاسخ پشتیبانی NetFly</b>\n\n"
    "{message}"
)
SUPPORT_TICKET_CLOSED = "✅ تیکت <code>#{ticket_id}</code> بسته شد."
SUPPORT_TICKET_NOT_FOUND = "❗ تیکت پیدا نشد."
SUPPORT_TICKET_ALREADY_CLOSED = "این تیکت قبلاً بسته شده است."

CANCELLED   = "❌ عملیات لغو شد."
NOT_ADMIN   = "⛔ این دستور فقط برای ادمین‌ها در دسترس است."
NOT_PERMITTED = "⛔ سطح دسترسی شما برای این کار کافی نیست."

ADMIN_ROLE_LABELS = {
    "owner": "👑 مالک (همه دسترسی‌ها)",
    "manager": "🛠 مدیر",
    "reviewer": "🔍 بررسی سفارش",
    "support": "💬 پشتیبانی",
    "viewer": "👁 مشاهده",
}

ADMIN_ROLES_MENU = (
    "👮 <b>مدیریت دسترسی ادمین‌ها</b>\n\n"
    "مالک: اولین شناسه در <code>ADMIN_IDS</code> — همیشه کامل.\n"
    "بقیه با نقش محدود وارد می‌شوند.\n\n"
    "{lines}"
)

ADMIN_ROLES_LINE = "• <code>{user_id}</code> — <b>{role_label}</b>"
ADMIN_ROLE_SET_OK = "✅ نقش <code>{user_id}</code> → <b>{role_label}</b>"
ADMIN_ROLE_USAGE = (
    "❗ <b>مدیریت نقش (فقط مالک)</b>\n\n"
    "<code>/setadminrole &lt;user_id&gt; manager|reviewer|support|viewer</code>\n"
    "نقش‌ها:\n"
    "• <b>manager</b> — همه جز مدیریت ادمین‌ها\n"
    "• <b>reviewer</b> — بررسی و مدیریت سفارش، مشتریان\n"
    "• <b>support</b> — کاربران، مشتریان، تأیید رسید\n"
    "• <b>viewer</b> — فقط مشاهده"
)
ADMIN_BTN_PERM_MATRIX = "📋 ماتریس دسترسی نقش‌ها"
ADMIN_BTN_PERM_RESET_ROLE = "🔄 بازنشانی این نقش"
ADMIN_BTN_PERM_RESET_ALL = "🔄 بازنشانی همه به پیش‌فرض"
ADMIN_PERM_MATRIX_HINT = (
    "<i>برای تغییر: یک نقش را انتخاب کنید و روی هر دسترسی بزنید.</i>\n"
    "<i>مالک همیشه همه دسترسی‌ها را دارد.</i>"
)
ADMIN_PERM_ROLE_HEADER = "✏️ <b>{role_label}</b>{custom}\n\n<i>روی هر ردیف بزنید تا روشن/خاموش شود:</i>"
ADMIN_PERM_RESET_ROLE_OK = "✅ این نقش به پیش‌فرض برگشت."
ADMIN_PERM_RESET_ALL_OK = "✅ همه نقش‌ها به پیش‌فرض برگشتند."
ADMIN_PERM_PANEL_REQUIRED = "⛔ دسترسی panel همیشه باید روشن باشد."
USER_BANNED = "⛔ دسترسی شما به ربات مسدود شده است."


# ---------- admin panel (buttons) ----------
ADMIN_BTN_DASHBOARD = "📊 داشبورد"
ADMIN_BTN_PENDING   = "🔍 بررسی پرداخت‌ها"
ADMIN_BTN_ORDERS    = "📦 سفارش‌ها"  # legacy label; UI uses PENDING only
ADMIN_BTN_SETTINGS  = "⚙️ تنظیمات"
ADMIN_BTN_LOCATIONS = "📍 لوکیشن‌ها"
ADMIN_BTN_TOOLS     = "🛠 ابزارها"
ADMIN_BTN_USERS     = "👥 کاربران"
ADMIN_BTN_CUSTOMERS = "🛒 مشتریان"
ADMIN_BTN_CUSTOMERS_SEARCH = "🔎 جستجوی مشتری"
ADMIN_BTN_PANEL     = "🏠 پنل ادمین"
ADMIN_BTN_HIDE_REPLY = "🔽 بستن منوی پایین"
ADMIN_BTN_SHOW_REPLY = "📋 نمایش منوی پایین"
ADMIN_REPLY_HIDDEN = "✅ منوی پایین بسته شد.\n\nبرای بازگشت: <code>/admin</code> یا دکمهٔ «نمایش منوی پایین» در پنل."
ADMIN_REPLY_SHOWN = "✅ منوی پایین ادمین نمایش داده شد."
ADMIN_BTN_REFRESH   = "🔄 بروزرسانی"
ADMIN_BTN_SERVICES  = "🛒 پلن‌های فروش"
ADMIN_BTN_ORDER_LOOKUP = "🔎 جست و جوی سفارشات"
ADMIN_BTN_TOGGLE_MANUAL = "🔀 خرید از دکمه‌ها"
ADMIN_BTN_LOG_CHANNEL = "📋 کانال لاگ"
ADMIN_BTN_TOGGLE_TEST = "🧪 دکمه تست"
ADMIN_BTN_ADD_LOC_HELP = "➕ افزودن لوکیشن"
ADMIN_BTN_EDIT_LOC = "✏️ ویرایش لوکیشن"
ADMIN_BTN_ADD_SVC_HELP = "➕ افزودن پلن"
ADMIN_BTN_EDIT_SVC_HELP = "✏️ ویرایش پلن"
ADMIN_BTN_SETCARD_HELP = "💳 تنظیم کارت"
ADMIN_BTN_SETPRICE_HELP = "💰 تنظیم قیمت"
ADMIN_BTN_ORDER_MANAGE = "⚙️ سفارش"

ADMIN_PANEL_HOME = (
    "🛠 <b>پنل مدیریت NetFly</b>\n\n"
    "از <b>دکمه‌های پایین صفحه</b> یا منوی زیر استفاده کنید.\n"
    "دکمه <b>داشبورد</b> پنل را از نو باز می‌کند.\n"
    "بررسی رسیدها: <b>بررسی پرداخت‌ها</b>."
)

ADMIN_HOME_STATS = "{stats}"

ADMIN_DASHBOARD_HEADER = (
    "📊 <b>داشبورد</b>\n\n"
    "{stats}"
)

ADMIN_SETTINGS_VIEW = (
    "⚙️ <b>تنظیمات فعلی</b>\n\n"
    "💳 شماره کارت: <code>{card_number}</code>\n"
    "👤 صاحب کارت: <b>{card_holder}</b>\n\n"
    "💰 قیمت پیش‌فرض:\n"
    "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>\n\n"
    "🎁 تخفیف سراسری: <b>{offer_desc}</b>\n\n"
    "<b>ویرایش با دستور:</b>\n"
    "<code>/setcard 6037... | نام</code>\n"
    "<code>/setprice 20000 8000 1500</code>\n"
    "<code>/setoffer 20</code> — ۲۰٪ تخفیف · <code>/setoffer off 5000</code> — مبلغ کم‌شده"
)

ADMIN_OFFER_MENU = (
    "🎁 <b>تخفیف سراسری</b>\n\n"
    "وضعیت فعلی: <b>{offer_desc}</b>\n\n"
    "روی هر سرویس (پلن‌ها و خرید فرمولی) اعمال می‌شود.\n"
    "سرویس تست رایگان تحت تأثیر نیست."
)

ADMIN_OFFER_PERCENT_PROMPT = (
    "📉 <b>تخفیف درصدی</b>\n\n"
    "عدد ۱ تا ۹۹ را بفرستید (مثلاً <code>20</code> برای ۲۰٪ تخفیف).\n"
    "انصراف: <code>/cancel</code>"
)

ADMIN_OFFER_AMOUNT_PROMPT = (
    "💵 <b>تخفیف مبلغی</b>\n\n"
    "مبلغ تومان که از هر قیمت کم می‌شود را بفرستید (مثلاً <code>50000</code>).\n"
    "انصراف: <code>/cancel</code>"
)

ADMIN_OFFER_FIXED_PROMPT = (
    "🏷 <b>قیمت ثابت برای همه</b>\n\n"
    "قیمت نهایی هر سرویس را به تومان بفرستید (مثلاً <code>99000</code>).\n"
    "انصراف: <code>/cancel</code>"
)

ADMIN_OFFER_SET_OK = "✅ تخفیف سراسری فعال شد: <b>{offer_desc}</b>"
ADMIN_OFFER_CLEARED = "✅ تخفیف سراسری غیرفعال شد."
ADMIN_OFFER_INVALID = "❗ مقدار نامعتبر است."
ADMIN_OFFER_USAGE = (
    "❗ <b>تخفیف سراسری</b>\n\n"
    "<code>/setoffer 20</code> — ۲۰٪ تخفیف\n"
    "<code>/setoffer percent 20</code>\n"
    "<code>/setoffer off 50000</code> — ۵۰٬۰۰۰ تومان کمتر از هر قیمت\n"
    "<code>/setoffer amount 50000</code>\n"
    "<code>/setoffer price 99000</code> — همه سرویس‌ها = ۹۹٬۰۰۰ تومان\n"
    "<code>/setoffer clear</code> — خاموش"
)

ADMIN_BTN_OFFER = "🎁 تخفیف سراسری"

ADMIN_SETTINGS_MENU = (
    "⚙️ <b>تنظیمات</b>\n\n"
    "کارت و قیمت پیش‌فرض را با دکمه‌های راهنما تنظیم کنید.\n"
    "پلن‌های پایه (حجم/مدت) و پلن‌های فروش (خرید دستی) جداگانه‌اند.\n\n"
    "{settings_block}"
)

ADMIN_ORDERS_MENU = (
    "🔍 <b>بررسی پرداخت‌ها</b>\n\n"
    "روی هر سفارش بزنید تا رسید را ببینید و تأیید یا رد کنید.\n"
    "برای جستجوی سفارش با شناسه از دکمه «جستجوی سفارش» استفاده کنید."
)

ADMIN_SERVICES_MENU = (
    "🛒 <b>پلن‌های فروش (خرید دستی)</b>\n\n"
    "حالت خرید از دکمه‌ها: <b>{manual_mode}</b>\n\n"
    "{packages_block}"
)

ADMIN_ORDER_LOOKUP_PROMPT = (
    "🔎 <b>جستجوی سفارش</b>\n\n"
    "شناسه سفارش را بفرستید (عدد، مثل <code>42</code>).\n\n"
    "انصراف: دکمه زیر یا <code>/cancel</code>"
)

ADMIN_ORDER_LOOKUP_NOTFOUND = "❗ سفارشی با شناسه <code>{order_id}</code> یافت نشد."

ADMIN_PLANS_HEADER = (
    "📋 <b>پلن‌های پایه خرید</b>\n\n"
    "این گزینه‌ها در فلو «خرید سرویس» به کاربر نشان داده می‌شوند "
    "(گزینه «حجم دلخواه» همیشه باقی می‌ماند).\n\n"
    "<b>حجم (گیگابایت):</b> {volumes}\n"
    "<b>مدت (روز):</b> {durations}\n\n"
    "برای <b>افزودن</b>:\n"
    "<code>/addvolume 5</code> — مثلاً ۵ گیگ\n"
    "<code>/addduration 14</code> — مثلاً ۱۴ روز\n\n"
    "روی دکمه‌های زیر بزنید تا یک پلن <b>حذف</b> شود."
)

ADMIN_PLAN_VOL_REMOVED  = "✅ پلن حجم <b>{gb} GB</b> حذف شد."
ADMIN_PLAN_VOL_ADDED    = "✅ پلن حجم <b>{gb} GB</b> اضافه شد."
ADMIN_PLAN_DUR_REMOVED  = "✅ پلن مدت <b>{days} روز</b> حذف شد."
ADMIN_PLAN_DUR_ADDED    = "✅ پلن مدت <b>{days} روز</b> اضافه شد."
ADMIN_PLAN_EXISTS       = "ℹ️ این پلن از قبل وجود دارد."
ADMIN_PLAN_NOT_FOUND    = "ℹ️ این پلن در لیست نیست."
ADMIN_PLAN_INVALID      = "❗ مقدار نامعتبر است."
ADMIN_PLAN_LAST         = "❗ حداقل یک پلن باید باقی بماند."
ADMIN_PLAN_MAX          = "❗ حداکثر تعداد پلن‌ها پر است."
ADMIN_PLAN_USAGE        = (
    "❗ استفاده:\n"
    "<code>/addvolume 5</code> | <code>/delvolume 5</code>\n"
    "<code>/addduration 14</code> | <code>/delduration 14</code>\n"
    "<code>/plans</code> — نمایش لیست"
)

ADMIN_TOOLS_MENU = (
    "🛠 <b>ابزارها</b>\n\n"
    "📋 کانال لاگ: <b>{log_channel}</b>\n"
    "📢 عضویت اجباری: <b>{req_channel}</b>\n"
    "🧪 دکمه اشتراک تست: <b>{test_sub}</b>\n\n"
    "همگام‌سازی پنل، پاکسازی و همگانی از دکمه‌های زیر."
)
ADMIN_BTN_ADD_CLIENT = "➕ ساخت کلاینت دستی"
ADMIN_BTN_ADD_CLIENT_SKIP_USER = "⏭ بدون کاربر (فقط لینک)"
ADMIN_ADD_CLIENT_USER_PROMPT = (
    "➕ <b>ساخت کلاینت دستی</b>\n\n"
    "🆔 <b>شناسه کاربر تلگرام</b>\n"
    "عدد بفرستید (یا یک پیام از کاربر فوروارد کنید) تا در «سرویس‌های من» همان کاربر ثبت شود.\n\n"
    "انصراف: <code>/cancel</code>"
)
ADMIN_ADD_CLIENT_USER_INVALID = (
    "❗ شناسه نامعتبر. عدد مثبت بفرستید (مثل <code>123456789</code>) "
    "یا یک پیام از کاربر فوروارد کنید."
)
ADMIN_ADD_CLIENT_VOLUME_PROMPT = (
    "💾 <b>حجم سرویس</b> را به <b>گیگابایت</b> بفرستید\n"
    "(فقط عدد، مثلاً <code>5</code> برای ۵ گیگ).\n\n"
    "محدوده: <b>{min_gb}</b> تا <b>{max_gb}</b> گیگ"
)
ADMIN_ADD_CLIENT_VOLUME_INVALID = (
    "❗ حجم نامعتبر. عددی بین <b>{min_gb}</b> و <b>{max_gb}</b> گیگ بفرستید."
)
ADMIN_ADD_CLIENT_DAYS_PROMPT = (
    "📅 <b>مدت اعتبار</b> را به <b>روز</b> بفرستید\n"
    "(فقط عدد، مثلاً <code>30</code> برای ۳۰ روز)."
)
ADMIN_ADD_CLIENT_DAYS_INVALID = (
    "❗ مدت نامعتبر. عددی بین <b>{min_days}</b> و <b>{max_days}</b> روز بفرستید."
)
ADMIN_ADD_CLIENT_LOCATION_PROMPT = (
    "📍 <b>لوکیشن</b> را انتخاب کنید:"
)
ADMIN_ADD_CLIENT_NO_LOCATIONS = (
    "❗ هیچ لوکیشن فعالی برای ساخت کلاینت وجود ندارد."
)
ADMIN_ADD_CLIENT_PROVISIONING = "⏳ در حال ساخت کلاینت روی پنل..."
ADMIN_ADD_CLIENT_OK = (
    "✅ <b>کلاینت ساخته شد</b>\n\n"
    "🆔 سفارش: <code>#{order_id}</code>\n"
    "👤 کاربر: <code>{user_id}</code>\n"
    "📍 لوکیشن: <b>{location}</b>\n"
    "💾 {volume} گیگ · 📅 {days} روز\n"
    "📧 پنل: <code>{panel_email}</code>\n\n"
    "{configs_block}"
)
ADMIN_ADD_CLIENT_OK_PANEL_ONLY = (
    "✅ <b>کلاینت روی پنل ساخته شد</b> (بدون «سرویس‌های من»)\n\n"
    "🆔 سفارش: <code>#{order_id}</code>\n"
    "📍 لوکیشن: <b>{location}</b>\n"
    "💾 {volume} گیگ · 📅 {days} روز\n"
    "📧 پنل: <code>{panel_email}</code>\n\n"
    "{configs_block}"
)
ADMIN_ADD_CLIENT_FAILED = (
    "⚠️ ساخت کلاینت ناموفق بود{order_hint}:\n"
    "<code>{error}</code>"
)
ADMIN_ADD_CLIENT_USER_NOTIFY = (
    "🎉 <b>سرویس شما توسط پشتیبانی فعال شد</b>\n\n"
    "🆔 سفارش: <code>#{order_id}</code>\n"
    "📍 {location} · {volume} گیگ · {days} روز\n\n"
    "{configs_block}\n\n"
    "از «سرویس‌های من» می‌توانید مصرف را ببینید."
)

ADMIN_LOCATIONS_MENU = (
    "📍 <b>لوکیشن‌ها</b> ({count} مورد)\n\n"
    "روی هر لوکیشن بزنید برای جزئیات.\n"
    "🟢 فعال · 🟡 فقط سرویس‌های قبلی · 🔴 غیرفعال"
)

ADMIN_LOC_EMPTY = "هیچ لوکیشنی ثبت نشده است.\n\n<code>/addlocation ...</code>"

ADMIN_LOC_DETAIL = (
    "📍 <b>لوکیشن #{id}</b> {state_emoji} <b>{name}</b>\n"
    "{test_line}"
    "🛒 خرید جدید: <b>{purchase_state}</b>\n"
    "🔗 <code>{base_url}</code>\n"
    "📡 inbounds: <code>{inbounds}</code>\n"
    "🔔 sub: <code>{sub}</code>\n"
    "💰 {pricing}\n\n"
    "<b>دستورات:</b>\n"
    "<code>/editlocation {id} ...</code> — ویرایش کامل\n"
    "<code>/setlocationprice {id} base per_gb per_day</code>\n"
    "<code>/setsuburl {id} https://host:2096/sub/{{subId}}</code>\n"
    "<code>/purgelocation {id}</code>\n"
    "<code>/togglepurchase {id}</code> — باز/بسته کردن خرید جدید"
)

ADMIN_PENDING_HEADER = (
    "🔍 <b>سفارش‌های در انتظار بررسی</b> — <b>{count}</b> مورد\n\n"
    "روی هر سفارش بزنید تا رسید و دکمه‌های تأیید/رد نمایش داده شود."
)

ADMIN_PENDING_EMPTY = "✅ هیچ سفارشی در انتظار بررسی نیست."

ADMIN_PENDING_BTN = "🔍 #{id} · {price} · کاربر {user_id}"

ADMIN_USERS_HEADER = (
    "👥 <b>کاربران و کلاینت‌های پنل</b>\n"
    "صفحه <b>{page}</b> از <b>{pages}</b> — جمع: <b>{total}</b> کاربر\n\n"
    "روی هر کاربر بزنید برای جزئیات کامل.\n"
    "<i>وضعیت کلاینت‌های فعال از پنل (مصرف/اعتبار) خوانده می‌شود.</i>"
)
ADMIN_USERS_EMPTY = "هیچ کاربری در ربات ثبت نشده است."

ADMIN_USER_DETAIL = (
    "👤 <b>کاربر تلگرام</b>\n\n"
    "🆔 شناسه: <code>{user_id}</code>\n"
    "👤 نام: <b>{full_name}</b>\n"
    "📎 یوزرنیم: {username}\n"
    "📅 عضو از: {created_at}\n"
    "🚫 وضعیت: <b>{ban_state}</b>\n\n"
    "<b>سفارش‌ها و کلاینت پنل ({order_count}):</b>\n"
    "{orders_block}"
)

ADMIN_USER_ORDER_LINE = (
    "• <b>#{order_id}</b> — {status}\n"
    "  📍 {location} · {volume}GB / {days}d · {price}\n"
    "  {panel_line}"
)
ADMIN_USER_ORDER_PANEL = "  🆔 پنل: <code>{email}</code>\n"
ADMIN_USER_ORDER_NO_PANEL = "  🆔 پنل: <i>هنوز ساخته نشده</i>\n"
ADMIN_USER_NO_ORDERS = "<i>هیچ سفارشی ثبت نشده.</i>"

ADMIN_CUSTOMERS_HEADER = (
    "🛒 <b>مشتریان (خریداران)</b>\n"
    "صفحه <b>{page}</b> از <b>{pages}</b> — جمع: <b>{total}</b> مشتری\n\n"
    "فقط خریداران واقعی (سفارش‌های پولی؛ اشتراک تست نمایش داده نمی‌شود).\n"
    "روی هر نام بزنید برای جزئیات خرید و پنل.\n"
    "<i>وضعیت سرویس‌های فعال از پنل خوانده می‌شود.</i>"
)
ADMIN_CUSTOMERS_EMPTY = "هنوز مشتری (سفارش ثبت‌شده) وجود ندارد."
ADMIN_CUSTOMERS_SEARCH_PROMPT = (
    "🔎 <b>جستجوی مشتری</b>\n\n"
    "شناسه کاربر، شماره سفارش، یوزرنیم، نام، "
    "ایمیل پنل (<code>nf12</code>) یا نام مستعار را بفرستید.\n\n"
    "انصراف: دکمه زیر یا <code>/cancel</code>"
)
ADMIN_CUSTOMERS_SEARCH_EMPTY = (
    "❗ نتیجه‌ای برای <code>{query}</code> یافت نشد."
)
ADMIN_CUSTOMERS_SEARCH_HEADER = (
    "🔎 نتایج جستجو برای <code>{query}</code> — <b>{count}</b> مورد\n\n"
    "روی مشتری بزنید:"
)
ADMIN_CUSTOMER_LIST_LINE = (
    "▸ <b>{full_name}</b> ({username}) — <code>{user_id}</code> {ban}\n"
    "   📦 {order_count} سفارش · 💰 {total_spent} · 🟢 {provisioned} فعال"
    " · 🕐 {last_order}"
)
ADMIN_CUSTOMER_DETAIL = (
    "🛒 <b>مشتری</b>\n"
    "<b>{full_name}</b> · {username}\n"
    "شناسه <code>{user_id}</code> · عضو {created_at} · <b>{ban_state}</b>\n\n"
    "<b>خلاصه</b> — {total_orders} سفارش · جمع {total_spent}\n"
    "فعال {provisioned} · رد {declined} · بررسی {awaiting_review}"
    " · پرداخت {awaiting_payment}\n"
    "درآمد {paid_revenue} · {first_order} تا {last_order}\n\n"
    "<b>سفارش‌ها ({order_count})</b>\n"
    "{orders_block}"
)
ADMIN_CUSTOMER_ORDER_BLOCK = (
    "<blockquote>"
    "<b>#{order_id}</b>{test_mark} · {status}\n"
    "{location} · {plan_detail}\n"
    "<i>{created_at}</i>\n"
    "{footer}"
    "</blockquote>"
)
ADMIN_CUSTOMER_ORDER_SUB = "sub <code>{sub_id}</code>"
ADMIN_CUSTOMER_ORDER_REVIEWER = "بررسی {reviewer}"
ADMIN_CUSTOMER_ORDER_DECLINE = "رد: {decline}"
ADMIN_CUSTOMER_ORDER_RECEIPT = "رسید ✓"
ADMIN_CUSTOMER_NO_ORDERS = "<i>بدون سفارش.</i>"

ADMIN_TOOL_SYNC_DONE = "✅ همگام‌سازی پنل انجام شد (همان نتیجه <code>/syncpanel</code>)."

ADMIN_CMD_HELP_BTN = "📖 راهنمای دستورات"


# ---------- admin commands (reference) ----------
ADMIN_HELP = (
    "🛠 <b>دستورهای ادمین</b>\n\n"
    "💡 <b>پنل دکمه‌ای:</b> <code>/admin</code> — منوی پایین + دکمه‌های شیشه‌ای\n\n"
    "<b>عمومی:</b>\n"
    "/stats — آمار کلی\n"
    "/users — کاربران تلگرام + کلاینت‌های پنل\n"
    "/pending — سفارش‌های در انتظار بررسی\n"
    "/broadcast — ارسال همگانی (متن، عکس، ویدیو، فایل + کپشن)\n"
    "/broadcast &lt;متن&gt; — ارسال سریع فقط متن\n\n"
    "<b>تنظیمات:</b>\n"
    "/setcard &lt;شماره کارت&gt; | &lt;نام صاحب کارت&gt;\n"
    "/setprice &lt;base&gt; &lt;per_gb&gt; &lt;per_day&gt; — قیمت پیش‌فرض (لوکیشن‌های جدید)\n"
    "/setoffer 20 — ۲۰٪ تخفیف سراسری · /setoffer clear — خاموش\n"
    "/setlocationprice &lt;id&gt; &lt;base&gt; &lt;per_gb&gt; &lt;per_day&gt; — قیمت یک لوکیشن\n"
    "/setlocationprice &lt;id&gt; - — بازگشت لوکیشن به قیمت پیش‌فرض\n"
    "/showsettings — نمایش تنظیمات فعلی\n\n"
    "<b>پلن‌های پایه خرید:</b>\n"
    "/plans — حجم و مدت پیش‌فرض در فلو خرید\n"
    "/addvolume &lt;gb&gt; | /delvolume &lt;gb&gt;\n"
    "/addduration &lt;days&gt; | /delduration &lt;days&gt;\n\n"
    "<b>پلن‌های ازپیش‌تعریف (خرید دستی):</b>\n"
    "/togglemanualpurchase — روشن/خاموش انتخاب پلن از دکمه‌ها\n"
    "/addservice &lt;loc_id&gt; &lt;gb&gt; &lt;days&gt; &lt;toman&gt;\n"
    "/listservices [loc_id] — لیست پلن‌ها\n"
    "/delservice &lt;package_id&gt;\n\n"
    "<b>لاگ:</b>\n"
    "/logchannel — اتصال کانال لاگ (سفارش، رسید، تأیید/رد، تست، تیکت)\n"
    "/logchannel off — خاموش\n"
    "/reqchannel — کانال عضویت اجباری برای کاربران\n"
    "/reqchannel off — خاموش\n"
    "/reqchannellink — لینک دعوت کانال خصوصی\n\n"
    "<b>سفارش و کاربر:</b>\n"
    "/order &lt;id&gt; — جزئیات سفارش\n"
    "/editorder &lt;id&gt; — حجم/زمان پنل، فعال/غیرفعال، حذف\n"
    "/ban &lt;user_id&gt; | /unban &lt;user_id&gt;\n"
    "/editservice &lt;pkg_id&gt; &lt;gb&gt; &lt;days&gt; &lt;toman&gt;\n\n"
    "<b>لوکیشن‌ها:</b>\n"
    "/locations — لیست لوکیشن‌ها\n"
    "/addlocation — شروع مراحل افزودن لوکیشن جدید\n"
    "/dellocation &lt;id&gt; — حذف اگر سفارشی ندارد، در غیر این صورت غیرفعال\n"
    "/purgelocation &lt;id&gt; — ⚠️ حذف کامل لوکیشن و همه سفارش‌های آن\n"
    "/togglelocation &lt;id&gt;\n"
    "/setsuburl &lt;id&gt; &lt;template&gt; — تنظیم لینک اشتراک\n"
    "/addtestlocation — لوکیشن تست (۱۰۰MB، یک‌بار برای هر کاربر)\n"
    "/toggletest — روشن/خاموش دکمه «دریافت اشتراک تست»\n\n"
    "<b>همگام‌سازی پنل:</b>\n"
    "/clearorder &lt;order_id&gt; — حذف یک سفارش از دیتابیس\n"
    "/syncpanel — حذف سفارش‌های یتیم (پنل) + همه رد‌شده‌ها\n"
    "/syncpanel &lt;location_id&gt; — فقط یک لوکیشن\n"
    "/cleardeclined — حذف سفارش‌های رد‌شده و پرداخت‌نشده"
)

ADMIN_STATS = (
    "📊 <b>آمار NetFly</b>\n\n"
    "👥 کاربران: <b>{users}</b>\n"
    "🛒 کل سفارش‌ها: <b>{orders}</b>\n"
    "⏳ در انتظار پرداخت: <b>{awaiting_payment}</b>\n"
    "🔍 در انتظار بررسی: <b>{awaiting_review}</b>\n"
    "🎉 فعال‌شده: <b>{provisioned}</b>\n"
    "❌ رد‌شده: <b>{declined}</b>\n"
    "⚠️ خطا در فعال‌سازی: <b>{failed}</b>\n"
    "💬 تیکت‌های پشتیبانی: <b>{tickets}</b>"
)

CLEAR_ORDER_USAGE    = "❗ استفاده: <code>/clearorder &lt;order_id&gt;</code>"
CLEAR_ORDER_OK       = "✅ سفارش <code>#{id}</code> از دیتابیس حذف شد."
CLEAR_ORDER_NOTFOUND = "❗ سفارشی با این شناسه پیدا نشد."

CLEAR_DECLINED_OK = (
    "✅ از دیتابیس حذف شد:\n"
    "❌ رد‌شده: <b>{declined}</b>\n"
    "💳 پرداخت‌نشده: <b>{unpaid}</b>\n"
    "جمع: <b>{total}</b>"
)
CLEAR_DECLINED_NONE = "ℹ️ سفارش رد‌شده یا پرداخت‌نشده‌ای در دیتابیس نیست."

SYNC_PANEL_USAGE    = (
    "❗ استفاده:\n"
    "<code>/syncpanel</code> — همه لوکیشن‌ها\n"
    "<code>/syncpanel 2</code> — فقط لوکیشن ۲"
)
SYNC_PANEL_START    = "⏳ در حال همگام‌سازی با پنل..."
SYNC_PANEL_NONE = (
    "✅ همه سفارش‌های فعال در پنل موجودند.\n"
    "سفارش رد‌شده حذف‌شده: <b>{declined}</b>"
)
SYNC_PANEL_DONE = (
    "✅ همگام‌سازی پایان یافت.\n\n"
    "🗑 حذف از دیتابیس (یتیم پنل): <b>{orphan_count}</b>\n"
    "<code>{orphan_ids}</code>\n\n"
    "🧪 تست منقضی — حذف از پنل (ثبت در ربات): <b>{test_cleaned_count}</b>\n"
    "<code>{test_cleaned_ids}</code>\n\n"
    "❌ حذف سفارش‌های رد‌شده: <b>{declined}</b>"
)
SYNC_PANEL_LOC_ERR  = "⚠️ خطا در لوکیشن <code>#{id}</code> ({name}):\n<code>{error}</code>"

BTN_ADMIN_BROADCAST = "📣 ارسال همگانی"
BTN_BROADCAST_SEND   = "✅ ارسال به همه"
BTN_BROADCAST_CANCEL = "❌ انصراف"

BROADCAST_PROMPT = (
    "📣 <b>ارسال همگانی</b>\n\n"
    "یک پیام بفرستید — هر کدام از این‌ها:\n"
    "• متن (با فرمت تلگرام)\n"
    "• عکس / ویدیو / فایل / گیف / ویس / استیکر\n"
    "• همراه با <b>کپشن</b> در صورت نیاز\n\n"
    "پس از ارسال، پیش‌نمایش و تأیید نمایش داده می‌شود.\n"
    "انصراف: <code>/cancel</code> یا دکمه زیر"
)

BROADCAST_PREVIEW = (
    "👁 <b>پیش‌نمایش ارسال همگانی</b>\n\n"
    "نوع: <b>{type_label}</b>\n"
    "متن/کپشن: {caption_preview}\n"
    "مخاطب: <b>{count}</b> کاربر (غیرمسدود)\n\n"
    "پیام بالا همان چیزی است که ارسال می‌شود.\n"
    "تأیید می‌کنید؟"
)

BROADCAST_ALBUM_UNSUPPORTED = (
    "⚠️ آلبوم (چند عکس/فایل یکجا) پشتیبانی نمی‌شود.\n"
    "لطفاً <b>یک پیام</b> بفرستید (مثلاً یک عکس با کپشن)."
)

BROADCAST_WRONG_ADMIN = "فقط ادمینی که این پیام را ساخت می‌تواند ارسال را تأیید کند."

BROADCAST_CANCELLED = "❌ ارسال همگانی لغو شد."

BROADCAST_CONFIRM_HINT = (
    "ℹ️ برای ارسال، دکمه «ارسال به همه» را بزنید.\n"
    "انصراف: <code>/cancel</code>"
)

BROADCAST_STARTED = "📣 شروع ارسال همگانی به <b>{count}</b> کاربر..."
BROADCAST_PROGRESS = (
    "📣 در حال ارسال… <b>{done}</b> / <b>{total}</b>\n"
    "موفق: <b>{ok}</b> | ناموفق: <b>{fail}</b>"
)
BROADCAST_DONE = (
    "✅ ارسال همگانی پایان یافت.\n"
    "موفق: <b>{ok}</b> | ناموفق: <b>{fail}</b>\n\n"
    "<i>ناموفق معمولاً به‌خاطر بلاک ربات یا حذف اکانت است.</i>"
)

NEW_TICKET_NOTIFY = (
    "🆕 <b>تیکت پشتیبانی جدید #{ticket_id}</b>\n"
    "از طرف: <a href='tg://user?id={user_id}'>{full_name}</a> "
    "(<code>{user_id}</code>)\n\n"
    "{message}"
)

NEW_RECEIPT_NOTIFY = (
    "💳 <b>رسید پرداخت جدید — سفارش #{order_id}</b>\n\n"
    "👤 کاربر: <a href='tg://user?id={user_id}'>{full_name}</a> (<code>{user_id}</code>)\n"
    "📦 لوکیشن: <b>{location}</b>\n"
    "💾 حجم: <b>{volume} گیگابایت</b>\n"
    "📅 مدت: <b>{days} روز</b>\n"
    "💰 مبلغ: <b>{price}</b>"
)

# Settings / locations admin replies
SET_CARD_OK        = "✅ شماره کارت به‌روزرسانی شد:\n<code>{number}</code>\nبه نام: <b>{holder}</b>"
SET_CARD_USAGE     = "❗ استفاده:\n<code>/setcard 6037-9912-3456-7890 | NetFly</code>"
SET_PRICE_OK       = ("✅ فرمول قیمت به‌روزرسانی شد:\n"
                     "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>")
SET_PRICE_USAGE    = "❗ استفاده:\n<code>/setprice 20000 8000 1500</code>"
SHOW_SETTINGS      = ADMIN_SETTINGS_VIEW  # alias for /showsettings command

ADD_SERVICE_USAGE = (
    "➕ <b>افزودن پلن فروش</b>\n\n"
    "از دکمه <b>➕ افزودن پلن</b> در منوی پلن‌ها استفاده کنید،\n"
    "یا دستور:\n"
    "<code>/addservice 2 5 3 20000</code>\n"
    "یعنی: لوکیشن ۲ — ۵ گیگ — ۳ روز — ۲۰٬۰۰۰ تومان"
)
ADD_SERVICE_WIZARD_LOCATION = (
    "➕ <b>افزودن پلن</b> — مرحله ۱ از ۴\n\n"
    "📍 <b>لوکیشن</b> را انتخاب کنید:"
)
ADD_SERVICE_WIZARD_VOLUME = (
    "➕ <b>افزودن پلن</b> — مرحله ۲ از ۴\n\n"
    "📍 لوکیشن: <b>{location}</b>\n\n"
    "💾 <b>حجم (گیگابایت)</b> را انتخاب کنید:"
)
ADD_SERVICE_WIZARD_VOLUME_CUSTOM = (
    "➕ <b>افزودن پلن</b> — مرحله ۲ از ۴\n\n"
    "📍 لوکیشن: <b>{location}</b>\n\n"
    "عدد حجم را به <b>گیگابایت</b> بفرستید "
    "(بین {min_gb} تا {max_gb}):"
)
ADD_SERVICE_WIZARD_VOLUME_INVALID = (
    "❗ حجم نامعتبر. عددی بین {min_gb} و {max_gb} گیگ بفرستید."
)
ADD_SERVICE_WIZARD_DURATION = (
    "➕ <b>افزودن پلن</b> — مرحله ۳ از ۴\n\n"
    "📍 {location} · 💾 <b>{volume} گیگ</b>\n\n"
    "📅 <b>مدت (روز)</b> را انتخاب کنید:"
)
ADD_SERVICE_WIZARD_DURATION_CUSTOM = (
    "➕ <b>افزودن پلن</b> — مرحله ۳ از ۴\n\n"
    "📍 {location} · 💾 <b>{volume} گیگ</b>\n\n"
    "تعداد <b>روز</b> را بفرستید (حداقل ۱):"
)
ADD_SERVICE_WIZARD_DURATION_INVALID = "❗ مدت نامعتبر. عدد روز باید بزرگ‌تر از ۰ باشد."
ADD_SERVICE_WIZARD_PRICE = (
    "➕ <b>افزودن پلن</b> — مرحله ۴ از ۴\n\n"
    "📍 {location}\n"
    "💾 {volume} گیگ · 📅 {days} روز\n\n"
    "💰 <b>قیمت (تومان)</b> را بفرستید (عدد ≥ ۰):"
)
ADD_SERVICE_WIZARD_PRICE_INVALID = "❗ قیمت نامعتبر. عدد صحیح ≥ ۰ بفرستید."
ADD_SERVICE_WIZARD_NO_LOCATIONS = (
    "⛔ هیچ لوکیشن فعال (غیرتست) برای تعریف پلن وجود ندارد.\n"
    "ابتدا لوکیشن اضافه و فعال کنید."
)
ADD_SERVICE_OK = (
    "✅ پلن اضافه شد — شناسه <code>#{id}</code>\n"
    "📍 لوکیشن <code>#{loc_id}</code> · {volume} گیگ · {days} روز · {price}"
)
ADD_SERVICE_DUPLICATE = "❗ این ترکیب حجم/مدت برای همین لوکیشن قبلاً ثبت شده."
ADD_SERVICE_NOT_FOUND = "❗ لوکیشن با این شناسه یافت نشد."
ADD_SERVICE_INVALID   = "❗ مقادیر نامعتبر (حجم و روز باید بزرگ‌تر از ۰، قیمت ≥ ۰)."
ADD_SERVICE_TEST_LOC  = "❗ برای لوکیشن تست نمی‌توان پلن فروش تعریف کرد."
ADD_SERVICE_DISABLED  = "❗ لوکیشن غیرفعال است — ابتدا فعالش کنید یا لوکیشن دیگری انتخاب کنید."

ORDER_INCOMPLETE = "اطلاعات سفارش ناقص است. از ابتدا خرید را شروع کنید."
ORDER_PLAN_CHANGED = "این پلن دیگر موجود نیست. لطفاً دوباره انتخاب کنید."

DEL_SERVICE_USAGE    = "❗ استفاده: <code>/delservice &lt;package_id&gt;</code>"
DEL_SERVICE_OK       = "✅ پلن <code>#{id}</code> حذف شد."
DEL_SERVICE_NOTFOUND = "❗ پلن یافت نشد."

LIST_SERVICES_EMPTY = "ℹ️ هیچ پلنی ثبت نشده. دکمه <b>➕ افزودن پلن</b> را بزنید."
LIST_SERVICES_HEADER = "📋 <b>پلن‌های فروش</b>{filter_line}\n\n"
LIST_SERVICES_LINE = (
    "• <code>#{id}</code> — لوکیشن <code>#{loc_id}</code> ({loc_name})\n"
    "  {volume} گیگ · {days} روز · {price}"
)

TOGGLE_MANUAL_PURCHASE_USAGE = (
    "❗ استفاده:\n"
    "<code>/togglemanualpurchase</code> — تغییر حالت\n"
    "<code>/togglemanualpurchase on</code> | <code>off</code>"
)
TOGGLE_MANUAL_PURCHASE_OK = (
    "✅ حالت خرید: <b>{mode}</b>\n\n"
    "<b>روشن:</b> کاربر پس از انتخاب لوکیشن، پلن‌های ازپیش‌تعریف را می‌بیند.\n"
    "<b>خاموش:</b> انتخاب جداگانه حجم و مدت (فرمول قیمت)."
)

LOG_CHANNEL_USAGE = (
    "❗ استفاده:\n"
    "<code>/logchannel</code> — اتصال کانال (فوروارد یا شناسه)\n"
    "<code>/logchannel -1001234567890</code> — شناسه مستقیم\n"
    "<code>/logchannel off</code> — غیرفعال"
)
LOG_CHANNEL_PROMPT = (
    "📋 <b>تنظیم کانال لاگ</b>\n\n"
    "۱) ربات را در کانال لاگ <b>ادمین</b> کنید (دسترسی ارسال پیام).\n"
    "۲) یک پیام از همان کانال را <b>فوروارد</b> کنید\n"
    "   یا شناسه کانال را بفرستید (مثل <code>-1001234567890</code>).\n\n"
    "انصراف: <code>/cancel</code>"
)
LOG_CHANNEL_NEED_FORWARD = (
    "❗ یک پیام <b>فوروارد‌شده</b> از کانال لاگ بفرستید "
    "یا شناسه عددی کانال (مثل <code>-100…</code>)."
)
LOG_CHANNEL_TEST = "✅ کانال لاگ NetFly متصل شد."
LOG_CHANNEL_OK = (
    "✅ کانال لاگ ثبت شد: <code>{chat_id}</code>\n"
    "پیام آزمایشی ارسال شد."
)
LOG_CHANNEL_FORBIDDEN = (
    "❗ ربات نمی‌تواند در این کانال پیام بفرستد.\n"
    "ربات را ادمین کانال کنید و دوباره تلاش کنید."
)
LOG_CHANNEL_BAD = "❗ خطا: <code>{error}</code>"
LOG_CHANNEL_CLEARED = "✅ کانال لاگ غیرفعال شد."

JOIN_CHANNEL_REQUIRED = (
    "📢 <b>عضویت در کانال الزامی است</b>\n\n"
    "برای استفاده از ربات، ابتدا در کانال زیر عضو شوید:\n"
    "<b>{channel}</b>\n\n"
    "بعد از عضویت، دکمه «بررسی عضویت» را بزنید."
)
JOIN_CHANNEL_REQUIRED_SHORT = "ابتدا در کانال عضو شوید، سپس «بررسی عضویت» را بزنید."
JOIN_CHANNEL_NO_LINK_HINT = (
    "\n\n<i>لینک کانال از طرف ادمین تنظیم نشده — از ادمین لینک دعوت بگیرید.</i>"
)
BTN_JOIN_CHANNEL = "📢 ورود به کانال"
BTN_CHECK_JOIN = "✅ بررسی عضویت"
JOIN_VERIFIED_OK = "✅ عضویت تأیید شد. خوش آمدید!"
JOIN_NOT_YET = "هنوز در کانال عضو نشده‌اید. پس از عضویت دوباره بررسی کنید."
JOIN_GATE_UNAVAILABLE = (
    "⚠️ ربات الان نمی‌تواند عضویت کانال را بررسی کند.\n"
    "لطفاً کمی بعد دوباره تلاش کنید."
)
JOIN_GATE_UNAVAILABLE_SHORT = "بررسی عضویت موقتاً ممکن نیست."
JOIN_GATE_ADMIN_ALERT = (
    "⚠️ <b>عضویت اجباری کانال کار نمی‌کند</b>\n\n"
    "ربات در کانال <code>{channel_id}</code> ادمین نیست "
    "یا شناسه کانال اشتباه است.\n"
    "ربات را ادمین کانال کنید یا از "
    "<code>/reqchannel off</code> خاموش کنید."
)

REQ_CHANNEL_USAGE = (
    "❗ استفاده:\n"
    "<code>/reqchannel</code> — تنظیم کانال عضویت اجباری\n"
    "<code>/reqchannel -1001234567890</code> — شناسه مستقیم\n"
    "<code>/reqchannel off</code> — غیرفعال\n"
    "<code>/reqchannellink https://t.me/+…</code> — لینک دعوت (کانال خصوصی)"
)
REQ_CHANNEL_PROMPT = (
    "📢 <b>کانال عضویت اجباری</b>\n\n"
    "۱) ربات را در کانال <b>ادمین</b> کنید.\n"
    "۲) یک پیام از همان کانال را <b>فوروارد</b> کنید\n"
    "   یا شناسه کانال را بفرستید (مثل <code>-1001234567890</code>).\n\n"
    "انصراف: <code>/cancel</code>"
)
REQ_CHANNEL_NEED_FORWARD = (
    "❗ یک پیام <b>فوروارد‌شده</b> از کانال بفرستید "
    "یا شناسه عددی کانال (مثل <code>-100…</code>)."
)
REQ_CHANNEL_OK = (
    "✅ کانال عضویت اجباری ثبت شد.\n"
    "شناسه: <code>{chat_id}</code>\n"
    "نام: <b>{title}</b>{link_line}"
)
REQ_CHANNEL_OK_NEED_LINK = (
    "✅ کانال ثبت شد (<code>{chat_id}</code> — <b>{title}</b>).\n\n"
    "لینک دعوت خودکار پیدا نشد.\n"
    "یک لینک <code>t.me/…</code> بفرستید "
    "یا <code>/reqchannellink</code> را بزنید."
)
REQ_CHANNEL_LINK_PROMPT = (
    "🔗 <b>لینک دعوت کانال</b>\n\n"
    "لینک عضویت را بفرستید (مثل <code>https://t.me/+AbCd…</code> "
    "یا <code>https://t.me/channelname</code>).\n\n"
    "انصراف: <code>/cancel</code>"
)
REQ_CHANNEL_LINK_INVALID = (
    "❗ لینک نامعتبر. فقط آدرس <code>t.me/…</code> بپذیریم."
)
REQ_CHANNEL_LINK_NO_CHANNEL = "❗ ابتدا کانال را با <code>/reqchannel</code> تنظیم کنید."
REQ_CHANNEL_LINK_SAVED = "✅ لینک دعوت ذخیره شد:\n{link}"
REQ_CHANNEL_BOT_NOT_ADMIN = (
    "❗ ربات در این کانال ادمین نیست.\n"
    "ربات را ادمین کانال کنید و دوباره تلاش کنید."
)
REQ_CHANNEL_BAD = "❗ خطا: <code>{error}</code>"
REQ_CHANNEL_CLEARED = "✅ عضویت اجباری در کانال غیرفعال شد."
ADMIN_BTN_REQ_CHANNEL = "📢 کانال عضویت اجباری"

ADMIN_ORDER_USAGE = "❗ استفاده: <code>/order &lt;order_id&gt;</code>"
ADMIN_ORDER_NOTFOUND = "❗ سفارشی با این شناسه یافت نشد."
ADMIN_ORDER_DETAIL = (
    "📋 <b>سفارش #{order_id}</b>\n\n"
    "📌 وضعیت: {status}\n"
    "👤 کاربر: {user_line}\n"
    "📍 لوکیشن: <b>{location}</b> (<code>#{location_id}</code>)\n"
    "💾 حجم: <b>{volume}</b> · 📅 <b>{days}</b> روز\n"
    "💰 مبلغ: <b>{price}</b>\n"
    "🏷 نام نمایشی: {nickname}\n"
    "🧪 تست: {test_mark}\n\n"
    "🆔 پنل: <code>{panel_email}</code>\n"
    "🔔 subId: <code>{sub_id}</code>\n"
    "👮 بررسی‌کننده: {reviewer}\n"
    "📝 دلیل رد: {decline_reason}\n"
    "📷 رسید: {screenshot}\n\n"
    "🕐 ایجاد: {created_at}\n"
    "🕑 بروزرسانی: {updated_at}"
)

ADMIN_EDIT_ORDER_USAGE = "❗ استفاده: <code>/editorder &lt;order_id&gt;</code>"
ADMIN_EDIT_ORDER_HEADER = "⚙️ <b>مدیریت سفارش</b>\n\n{detail}"
ADMIN_EDIT_ORDER_NO_PANEL = "این سفارش روی پنل فعال نیست (فقط حذف از ربات ممکن است)."
ADMIN_EDIT_ORDER_FAIL = "❗ خطای پنل: <code>{error}</code>"
ADMIN_EDIT_ORDER_ENABLED = "✅ سرویس <code>#{order_id}</code> در پنل فعال شد."
ADMIN_EDIT_ORDER_DISABLED = "⏸ سرویس <code>#{order_id}</code> در پنل غیرفعال شد."
ADMIN_EDIT_ORDER_PLAN_MENU = (
    "⚙️ <b>ویرایش حجم و زمان</b> — سفارش <code>#{order_id}</code>\n\n"
    "{panel_live}\n"
    "تغییرها روی پنل اعمال می‌شود. دکمه‌های <b>+</b> به مقدار فعلی اضافه می‌کنند."
)
ADMIN_EDIT_ORDER_PROMPT_GB = (
    "حجم <b>کل</b> جدید را به گیگابایت بفرستید (مثلاً <code>20</code>).\n\n"
    "<code>/cancel</code> — انصراف"
)
ADMIN_EDIT_ORDER_PROMPT_DAYS = (
    "چند <b>روز</b> به اعتبار <b>اضافه</b> شود؟ (مثلاً <code>30</code>)\n\n"
    "<code>/cancel</code> — انصراف"
)
ADMIN_EDIT_ORDER_INVALID_NUMBER = "❗ عدد صحیح بین <b>1</b> و <b>{max}</b> وارد کنید."
ADMIN_EDIT_ORDER_GB_ADDED = (
    "✅ <b>+{add_gb} GB</b> به سفارش <code>#{order_id}</code> اضافه شد.\n"
    "حجم کل پنل: <b>{total_gb} GB</b>"
)
ADMIN_EDIT_ORDER_GB_SET = (
    "✅ حجم سفارش <code>#{order_id}</code> روی <b>{total_gb} GB</b> تنظیم شد."
)
ADMIN_EDIT_ORDER_DAYS_ADDED = (
    "✅ <b>+{add_days}</b> روز به سفارش <code>#{order_id}</code> اضافه شد.\n"
    "انقضا: <code>{expiry}</code>"
)
ADMIN_EDIT_ORDER_PANEL_LIVE = (
    "📊 مصرف: <b>{used}</b> / <b>{total}</b> · انقضا: <code>{expiry}</code>"
)
ADMIN_EDIT_ORDER_PANEL_LIVE_UNLIMITED = (
    "📊 مصرف: <b>{used}</b> (نامحدود) · انقضا: <code>{expiry}</code>"
)
ADMIN_ORDER_DELETE_CONFIRM = (
    "⚠️ <b>حذف سفارش #{order_id}</b>\n\n"
    "کلاینت از پنل (در صورت وجود) و رکورد از ربات حذف می‌شود.\n"
    "تأیید می‌کنید؟"
)
ADMIN_ORDER_DELETE_CANCELLED = "❌ حذف لغو شد."
ADMIN_ORDER_DELETED_OK = "✅ سفارش <code>#{order_id}</code> از پنل و ربات حذف شد."
ADMIN_ORDER_DELETED_PARTIAL = (
    "⚠️ سفارش <code>#{order_id}</code> از ربات حذف شد.\n"
    "خطای حذف از پنل: <code>{error}</code>"
)

BTN_ORDER_EDIT_PLAN = "💾 حجم و زمان"
BTN_ORDER_SET_GB = "✏️ تنظیم حجم"
BTN_ORDER_ADD_DAYS = "✏️ افزودن روز"
BTN_ORDER_ENABLE = "✅ فعال در پنل"
BTN_ORDER_DISABLE = "⏸ غیرفعال در پنل"
BTN_ORDER_DELETE = "🗑 حذف پنل + ربات"
BTN_ORDER_DELETE_CONFIRM = "✅ بله، حذف کن"
BTN_USER_BAN = "🚫 مسدود کردن"
BTN_USER_UNBAN = "✅ رفع مسدودیت"

BAN_USAGE = "❗ استفاده: <code>/ban &lt;user_id&gt;</code>"
UNBAN_USAGE = "❗ استفاده: <code>/unban &lt;user_id&gt;</code>"
BAN_OK = "🚫 کاربر <code>{user_id}</code> مسدود شد."
UNBAN_OK = "✅ مسدودیت کاربر <code>{user_id}</code> برداشته شد."
BAN_USER_NOTFOUND = "❗ کاربر در ربات ثبت نشده."
BAN_SELF = "❗ نمی‌توانید خودتان را مسدود کنید."

EDIT_SERVICE_USAGE = (
    "❗ استفاده:\n"
    "<code>/editservice 5 10 3 38000</code>\n"
    "شناسه پلن + حجم + روز + قیمت (همان فرمت addservice)"
)
EDIT_SERVICE_OK = (
    "✅ پلن <code>#{id}</code> به‌روز شد:\n"
    "{volume} گیگ · {days} روز · {price}"
)

SET_LOC_PRICE_USAGE = (
    "❗ استفاده:\n"
    "<code>/setlocationprice 2 25000 10000 2000</code>\n\n"
    "برای استفاده از قیمت پیش‌فرض سراسری:\n"
    "<code>/setlocationprice 2 -</code>"
)
SET_LOC_PRICE_OK = (
    "✅ قیمت لوکیشن <code>#{id}</code> «{name}»:\n"
    "base = <b>{base}</b> | per_gb = <b>{per_gb}</b> | per_day = <b>{per_day}</b>"
)
SET_LOC_PRICE_DEFAULT_OK = (
    "✅ لوکیشن <code>#{id}</code> «{name}» از قیمت پیش‌فرض سراسری استفاده می‌کند."
)
ADD_LOC_USAGE   = (
    "❗ استفاده:\n"
    "<code>/addlocation Germany 🇩🇪 | https://panel.example.com | "
    "MY_API_TOKEN | 3,5</code>\n\n"
    "می‌توانید فیلد پنجم اختیاری را برای لینک اشتراک اضافه کنید:\n"
    "<code>... | 3,5 | https://panel.example.com:2096/sub/{subId}</code>"
)
ADD_LOC_OK      = (
    "✅ لوکیشن «{name}» با شناسه <code>{id}</code> اضافه شد.\n"
    "💰 قیمت: {pricing}"
)
EDIT_LOC_KEEP_HINT = "<i>خط تنه <code>-</code> = بدون تغییر</i>"
EDIT_LOC_PROMPT_NAME = (
    "✏️ <b>ویرایش لوکیشن #{id}</b>\n\n"
    "📝 <b>نام نمایشی</b>\n"
    "فعلی: <b>{current}</b>\n\n"
    "نام جدید را بفرستید.\n"
    + EDIT_LOC_KEEP_HINT
)
EDIT_LOC_PROMPT_BASE_URL = (
    "✏️ <b>ویرایش لوکیشن #{id}</b>\n\n"
    "🔗 <b>آدرس پنل (base_url)</b>\n"
    "فعلی:\n<code>{current}</code>\n\n"
    "آدرس جدید را بفرستید.\n"
    + EDIT_LOC_KEEP_HINT
)
EDIT_LOC_PROMPT_TOKEN = (
    "✏️ <b>ویرایش لوکیشن #{id}</b>\n\n"
    "🔑 <b>توکن API</b>\n"
    "توکن جدید را بفرستید.\n"
    + EDIT_LOC_KEEP_HINT
)
EDIT_LOC_PROMPT_INBOUNDS = (
    "✏️ <b>ویرایش لوکیشن #{id}</b>\n\n"
    "📡 <b>inboundها</b> (با ویرگول)\n"
    "فعلی: <code>{current}</code>\n\n"
    "مثال: <code>3,5</code>\n"
    + EDIT_LOC_KEEP_HINT
)
EDIT_LOC_PROMPT_INBOUNDS_PICKER = (
    "📡 <b>انتخاب Inbound</b>\n\n"
    "اینباندهای موجود در پنل را از لیست زیر انتخاب کنید.\n"
    "می‌توانید چند inbound را همزمان انتخاب کنید.\n\n"
    "✅ = انتخاب شده  |  ☑️ = انتخاب نشده"
)
EDIT_LOC_INBOUNDS_FETCH_FAIL = (
    "⚠️ <b>دریافت اینباندها از پنل ناموفق بود.</b>\n\n"
    "آدرس پنل یا توکن را بررسی کنید، یا شناسه‌های inbound را دستی وارد کنید.\n"
    "مثال: <code>1,3,5</code>"
)
EDIT_LOC_INBOUNDS_NONE_SELECTED = "⚠️ حداقل یک inbound را انتخاب کنید."
EDIT_LOC_PROMPT_SUB = (
    "✏️ <b>ویرایش لوکیشن #{id}</b>\n\n"
    "🔔 <b>لینک اشتراک</b>\n"
    "فعلی: <code>{current}</code>\n\n"
    "الگوی جدید (با <code>{{subId}}</code>)، "
    "<code>-</code> بدون تغییر، یا <code>0</code> برای حذف."
)
EDIT_LOC_USAGE = (
    "❗ استفاده — <b>اول شناسه لوکیشن</b>، بعد فیلدها با <code>|</code>:\n"
    "<code>/editlocation 5 | Sweden 🇸🇪 | https://panel.example.com/TOKEN | "
    "API_TOKEN | 1,2,3</code>\n\n"
    "فیلد ششم اختیاری — لینک اشتراک (حروف <code>subId</code> مهم نیست):\n"
    "<code>/editlocation 5 | ... | 1,2 | https://host:2096/sub/{subId}</code>\n\n"
    "اگر از دکمه «ویرایش» آمده‌اید، می‌توانید فقط ۵ فیلد را بچسبانید "
    "(بدون شمارهٔ اول) — همان لوکیون باز ویرایش می‌شود."
)
EDIT_LOC_MISSING_ID = (
    "❗ اول <b>شناسه لوکیشن</b> را بگذارید:\n"
    "<code>/editlocation 5 | نام | آدرس پنل | توکن | 1,2</code>\n\n"
    "یا از 📍 لوکیشن‌ها → ویرایش شروع کنید و فقط فیلدها را بچسبانید."
)
EDIT_LOC_OK = (
    "✅ لوکیشن <code>#{id}</code> «{name}» به‌روزرسانی شد.\n"
    "🔗 <code>{base_url}</code>\n"
    "📡 inbounds: <code>{inbounds}</code>"
)
EDIT_LOC_NOT_FOUND = "❗ لوکیشن با شناسه <code>{id}</code> یافت نشد."
ADD_TEST_LOC_USAGE = (
    "❗ استفاده (همان فرمت <code>/addlocation</code>):\n"
    "<code>/addtestlocation Test 🧪 | https://panel.example.com | "
    "TOKEN | 1,2</code>\n\n"
    "فیلد پنجم اختیاری: لینک اشتراک با <code>{subId}</code>\n\n"
    "• فقط <b>یک</b> لوکیشن تست فعال — لوکیشن تست قبلی غیرفعال/حذف می‌شود\n"
    f"• خریداران: <b>۱۰۰ مگابایت</b>، <b>{TEST_DURATION_HOURS} ساعت</b>، رایگان، یک‌بار برای هر کاربر\n"
    "• در لیست «خرید سرویس» نمایش داده <b>نمی‌شود</b>\n"
    "• دکمه تست را با <code>/toggletest</code> روشن/خاموش کنید"
)
ADD_TEST_LOC_OK = (
    "✅ <b>لوکیشن تست</b> «{name}» با شناسه <code>{id}</code> ثبت شد.\n"
    "💾 {volume} · 📅 {duration} · رایگان\n\n"
    "دکمه تست: <b>{toggle_state}</b> — <code>/toggletest</code> برای تغییر"
)
TOGGLE_TEST_OK = "✅ دکمه «دریافت اشتراک تست» اکنون <b>{state}</b> است."
TOGGLE_TEST_USAGE = "❗ استفاده:\n<code>/toggletest</code> — تغییر وضعیت\n<code>/toggletest on</code> | <code>/toggletest off</code>"

SET_SUBURL_USAGE = (
    "❗ استفاده:\n"
    "<code>/setsuburl &lt;id&gt; https://host:2096/sub/{subId}</code>\n\n"
    "برای حذف الگو: <code>/setsuburl &lt;id&gt; -</code>\n"
    "متن باید شامل <code>{subId}</code> باشد (محل قرارگیری شناسه اشتراک)."
)
SET_SUBURL_OK       = "✅ الگوی لینک اشتراک برای لوکیشن <code>#{id}</code> تنظیم شد:\n<code>{template}</code>"
SET_SUBURL_CLEARED  = "✅ الگوی لینک اشتراک برای لوکیشن <code>#{id}</code> حذف شد."
SET_SUBURL_BAD      = "❗ الگو باید شامل <code>{subId}</code> باشد."
DEL_LOC_USAGE     = "❗ استفاده: <code>/dellocation &lt;id&gt;</code>"
DEL_LOC_OK        = "✅ لوکیشن <code>{id}</code> حذف شد."
DEL_LOC_DISABLED  = (
    "ℹ️ لوکیشن <code>{id}</code> سفارش‌های ثبت‌شده دارد و قابل حذف کامل نیست؛ "
    "به‌جای حذف، <b>غیرفعال</b> شد و دیگر در لیست کاربر نمایش داده نمی‌شود.\n\n"
    "اگر می‌خواهید کاملاً پاک شود، ابتدا سفارش‌های مرتبط را از دیتابیس حذف کنید."
)
DEL_LOC_NOTFOUND  = "❗ لوکیشنی با این شناسه پیدا نشد."

PURGE_USAGE     = "❗ استفاده: <code>/purgelocation &lt;id&gt;</code>"
PURGE_CONFIRM   = (
    "⚠️ <b>هشدار — عملیات غیرقابل بازگشت</b>\n\n"
    "این کار لوکیشن <code>#{id}</code> «<b>{name}</b>» و "
    "<b>{count}</b> سفارش مرتبط با آن را برای همیشه از دیتابیس حذف می‌کند.\n\n"
    "آیا مطمئن هستید؟"
)
PURGE_DONE      = "✅ لوکیشن <code>#{id}</code> و <b>{count}</b> سفارش مرتبط حذف شدند."
PURGE_CANCELLED = "❌ پاک‌سازی لغو شد."
TOGGLE_LOC_USAGE = "❗ استفاده: <code>/togglelocation &lt;id&gt;</code>"
TOGGLE_LOC_OK    = "✅ لوکیشن <code>{id}</code> اکنون <b>{state}</b> است."
TOGGLE_PURCHASE_USAGE = "❗ استفاده: <code>/togglepurchase &lt;id&gt;</code>"
TOGGLE_PURCHASE_OK = (
    "✅ خرید جدید از لوکیشن <code>{id}</code> «{name}» اکنون <b>{state}</b> است."
)
LOC_PURCHASE_CLOSED_USER = (
    "⛔ خرید سرویس جدید از این لوکیشن موقتاً بسته است.\n"
    "سرویس‌های قبلی شما در «سرویس‌های من» همچنان فعال است."
)
LOC_LIST_EMPTY  = "هیچ لوکیشنی ثبت نشده است. با <code>/addlocation</code> یکی اضافه کنید."
LOC_LIST_HEADER = "📍 <b>لوکیشن‌های ثبت‌شده</b>\n"
LOC_LIST_ITEM   = (
    "• <code>#{id}</code> {state_emoji}{test_tag} <b>{name}</b>\n"
    "    base: <code>{base_url}</code>\n"
    "    inbounds: <code>{inbounds}</code>\n"
    "    sub: <code>{sub_template}</code>\n"
    "    💰 {pricing}"
)

PENDING_EMPTY  = "هیچ سفارشی در انتظار بررسی نیست."
PENDING_HEADER = "🔍 <b>سفارش‌های در انتظار بررسی</b>\n"
PENDING_ITEM   = (
    "• سفارش <code>#{id}</code> — کاربر <code>{user_id}</code> — "
    "{volume}GB / {days}d — <b>{price}</b> ({created_at})"
)

REVIEW_ALREADY = (
    "⚠️ این سفارش قبلاً توسط ادمین دیگر بررسی شده است.\n"
    "وضعیت فعلی: <b>{status}</b>"
)
REVIEW_OTHER_ADMIN_DONE = (
    "ℹ️ سفارش <code>#{order_id}</code> دیگر در انتظار بررسی نیست.\n"
    "نتیجه: <b>{action}</b> (ادمین <code>{admin_id}</code>)"
)
REVIEW_DECLINE_PROMPT = (
    "❌ <b>دلیل رد سفارش</b>\n\n"
    "یکی از گزینه‌های زیر را بزنید، یا دلیل دلخواه را در یک پیام بنویسید.\n"
    "متن انتخاب‌شده برای کاربر ارسال می‌شود.\n\n"
    "<i>/cancel برای انصراف</i>"
)
REVIEW_DECLINE_SENT  = "✅ سفارش رد شد و کاربر مطلع شد."
REVIEW_DECLINE_DONE = (
    "✅ سفارش <code>#{order_id}</code> رد شد و به کاربر اطلاع داده شد."
)
REVIEW_DECLINE_CANCELLED = "❌ انتخاب دلیل رد لغو شد."

# (id, button label, full message sent to buyer)
DECLINE_PRESETS: tuple[tuple[str, str, str], ...] = (
    (
        "invalid_payment",
        "❌ پرداخت نامعتبر",
        "رسید ارسالی شما قابل تأیید نیست (تصویر ناخوانا، ناقص یا فاقد اطلاعات "
        "تراکنش). لطفاً یک رسید واضح با مبلغ، تاریخ و شماره پیگیری مجدداً ارسال کنید.",
    ),
    (
        "wrong_amount",
        "💰 مبلغ نادرست",
        "مبلغ واریزی با مبلغ سفارش شما مطابقت ندارد. لطفاً مابه‌التفاوت را واریز "
        "کنید یا سفارش جدید با مبلغ صحیح ثبت نمایید.",
    ),
    (
        "failed_transaction",
        "🔄 تراکنش ناموفق",
        "تراکنش بانکی شما ناموفق یا لغو شده است. در صورت کسر وجه، معمولاً تا ۷۲ "
        "ساعت به حساب شما بازمی‌گردد؛ سپس مجدداً پرداخت کنید.",
    ),
    (
        "duplicate_payment",
        "🔁 پرداخت تکراری",
        "این رسید یا شماره پیگیری قبلاً برای سفارش دیگری ثبت شده است. در صورت "
        "واریز اشتباه با پشتیبانی تماس بگیرید.",
    ),
    (
        "wrong_destination",
        "🏦 واریز به حساب اشتباه",
        "مبلغ به شماره کارت یا حسابی غیر از حساب رسمی اعلام‌شده در ربات واریز شده "
        "است. لطفاً فقط به شماره کارت نمایش‌داده‌شده در ربات واریز کنید.",
    ),
    (
        "unclear_receipt",
        "📷 رسید ناخوانا",
        "تصویر رسید شما واضح نیست یا تاریخ، ساعت و مبلغ مشخص نیست. لطفاً "
        "اسکرین‌شات کامل و خوانای رسید بانکی را ارسال کنید.",
    ),
    (
        "policy_mismatch",
        "⚠️ مغایر با شرایط",
        "این سفارش با شرایط فروش یا نوع سرویس درخواستی سازگار نیست. برای راهنمایی "
        "با پشتیبانی در تماس باشید.",
    ),
)

DECLINE_PRESET_REASONS: dict[str, str] = {p[0]: p[2] for p in DECLINE_PRESETS}
REVIEW_ACCEPTED      = "✅ سفارش تأیید شد. در حال ساخت کانفیگ روی پنل..."
REVIEW_PROVISION_OK  = "🎉 سفارش با موفقیت فعال و برای کاربر ارسال شد."
REVIEW_PROVISION_ERR = "⚠️ خطا در فعال‌سازی روی پنل:\n<code>{error}</code>"

DELETE_SERVICE_CONFIRM = "⚠️ آیا از حذف این سرویس مطمئن هستید؟ با این کار سرویس از ربات و پنل به طور کامل حذف خواهد شد و امکان بازیابی آن وجود ندارد."
DELETE_SERVICE_OK = "✅ سرویس با موفقیت حذف شد."
DELETE_SERVICE_FAILED = "⚠️ خطا در حذف سرویس: {error}"
