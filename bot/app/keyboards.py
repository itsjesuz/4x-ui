from __future__ import annotations

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from app import texts
from app.db import Location


# ---------- callback data namespaces ----------
# Top menu
CB_MAIN_BUY           = "main:buy"
CB_MAIN_MY_SERVICES   = "main:my"
CB_MAIN_ACCOUNT       = "main:account"
CB_MAIN_SUPPORT       = "main:support"
CB_MAIN_HELP          = "main:help"
CB_MAIN_ABOUT         = "main:about"
CB_MAIN_TEST          = "main:test"
CB_MAIN_HOME          = "main:home"
CB_MAIN_CHECK_JOIN    = "main:joinchk"

# Order flow
CB_LOC_PREFIX     = "loc:"          # loc:<location_id>
CB_VOL_PREFIX     = "vol:"          # vol:<gb> or vol:custom
CB_VOL_CUSTOM     = "vol:custom"
CB_DUR_PREFIX     = "dur:"          # dur:<days>
CB_SVC_PREFIX     = "svc:"          # svc:<package_id>
CB_ORDER_BACK_PKG = "ord:back:pkg"
CB_ORDER_CONFIRM  = "ord:confirm"   # final confirmation of summary
CB_ORDER_CANCEL   = "ord:cancel"
CB_ORDER_BACK_LOC = "ord:back:loc"
CB_ORDER_BACK_VOL = "ord:back:vol"
CB_ORDER_BACK_DUR = "ord:back:dur"

# Support
CB_CANCEL_SUPPORT = "support:cancel"
CB_SUPPORT_REPLY_PREFIX = "support:reply:"  # support:reply:<ticket_id>
CB_SUPPORT_CLOSE_PREFIX = "support:close:"  # support:close:<ticket_id>

# Admin review
CB_ADMIN_ACCEPT_PREFIX  = "adm:acc:"   # adm:acc:<order_id>
CB_ADMIN_DECLINE_PREFIX = "adm:dec:"   # adm:dec:<order_id>
CB_ADMIN_DECLINE_PRESET_PREFIX = "adm:decp:"  # adm:decp:<order_id>:<preset_id>
CB_ADMIN_DECLINE_CANCEL_PREFIX = "adm:decx:"  # adm:decx:<order_id>

# Admin panel navigation
CB_ADM_HOME              = "adm:home"
CB_ADM_SHOW_REPLY        = "adm:showkb"
CB_ADM_DASH              = "adm:dash"
CB_ADM_PENDING_LIST      = "adm:plist"
CB_ADM_SETTINGS          = "adm:set"
CB_ADM_LOCATIONS_LIST    = "adm:llist"
CB_ADM_LOC_DETAIL_PREFIX = "adm_loc:"
CB_ADM_LOC_EDIT_PREFIX   = "adm_loc_e:"
CB_ADM_LOC_TOGGLE_PREFIX = "adm_loc_t:"
CB_ADM_LOC_PURCHASE_PREFIX = "adm_loc_p:"
CB_ADM_LOC_PURGE_PREFIX  = "adm_loc_purge:"
CB_ADM_LOC_BTNS_PREFIX   = "adm_loc_btns:"
CB_ADM_LOC_BTN_DEL_PREFIX = "adm_loc_btndel:"
CB_ADM_LOC_BTN_ADD_PREFIX = "adm_loc_btnadd:"
CB_ADM_TOOLS             = "adm:tools"
CB_ADM_USERS                 = "adm:usr"
CB_ADM_USERS_PAGE_PREFIX     = "adm:usrp:"   # adm:usrp:<page>
CB_ADM_USER_DETAIL_PREFIX    = "adm:u:"      # adm:u:<user_id>
CB_ADM_USER_INFO_PREFIX      = "adm:uinf:"   # adm:uinf:<user_id> — alert, no tg:// link
CB_ADM_CUSTOMERS             = "adm:cust"
CB_ADM_CUSTOMERS_PAGE_PREFIX = "adm:custp:"  # adm:custp:<page>
CB_ADM_CUST_DETAIL_PREFIX    = "adm:custd:"  # adm:custd:<user_id>
CB_ADM_CUSTOMERS_SEARCH      = "adm:custq"
CB_ADM_CUST_BAN_PREFIX       = "adm:cbn:"    # adm:cbn:<user_id>
CB_ADM_CUST_UNBAN_PREFIX     = "adm:cub:"    # adm:cub:<user_id>
CB_ADM_CMD_HELP          = "adm:cmdhelp"
CB_ADM_ORDERS            = "adm:orders"
CB_ADM_ORDER_LOOKUP      = "adm:olookup"
CB_ADM_ORDER_MANAGE_PREFIX = "adm:om:"   # adm:om:<order_id>
CB_ADM_SERVICES          = "adm:svc"
CB_ADM_TOGGLE_MANUAL     = "adm:tman"
CB_ADM_SERVICES_REFRESH  = "adm:lsvc"
CB_ADM_LOG_CHANNEL       = "adm:logch"
CB_ADM_LOG_CHANNEL_OFF   = "adm:logoff"
CB_ADM_REQ_CHANNEL       = "adm:reqch"
CB_ADM_REQ_CHANNEL_OFF   = "adm:reqoff"
CB_ADM_TOGGLE_TEST       = "adm:ttest"
CB_ADM_TOGGLE_TEST_LOC_PREFIX = "adm:ttloc:"  # adm:ttloc:<location_id>
CB_ADM_FLOW_CANCEL       = "adm:fcancel"
CB_ADM_PM_PREFIX         = "adm:pm:"          # adm:pm:<user_id>
CB_ADM_SETCARD_HELP      = "adm:hcard"
CB_ADM_SETPRICE_HELP     = "adm:hprice"
CB_ADM_ADDLOC_HELP       = "adm:hloc"
CB_ADM_ADD_LOC           = "adm:addloc"
CB_ADM_ADD_SVC           = "adm:addsvc"
CB_ADM_ADDSVC_HELP       = "adm:hsvc"  # legacy hint callback
CB_ADM_EDITSVC_HELP      = "adm:hesvc"
CB_ADM_ADD_SVC_LOC_PREFIX  = "adm:asvcl:"   # adm:asvcl:<location_id>
CB_ADM_ADD_SVC_VOL_PREFIX  = "adm:asvcv:"   # adm:asvcv:<gb>
CB_ADM_ADD_SVC_DUR_PREFIX  = "adm:asvcd:"   # adm:asvcd:<days>
CB_ADM_ADD_SVC_VOL_CUSTOM  = "adm:asvcvc"
CB_ADM_ADD_SVC_DUR_CUSTOM  = "adm:asvcdc"
CB_ADM_ADD_SVC_BACK_LOC    = "adm:asvcb0"
CB_ADM_ADD_SVC_BACK_VOL    = "adm:asvcb1"
CB_ADM_ADD_SVC_BACK_DUR    = "adm:asvcb2"
CB_ADM_SETTINGS_REFRESH  = "adm:setrf"
CB_ADM_PLAN_ADD_HINT     = "adm:phint"
CB_ADM_OFFER             = "adm:offer"
CB_ADM_OFFER_CLEAR       = "adm:ofclr"
CB_ADM_OFFER_PCT_PREFIX  = "adm:ofp:"   # adm:ofp:20 → 20%
CB_ADM_OFFER_PCT_CUSTOM  = "adm:ofpc"
CB_ADM_OFFER_AMOUNT      = "adm:ofamt"
CB_ADM_OFFER_FIXED       = "adm:offix"
CB_ADM_ROLES             = "adm:roles"
CB_ADM_ROLE_SET_PREFIX   = "adm:rlset:"  # adm:rlset:<user_id>:<role>
CB_ADM_PERM_MATRIX       = "adm:pmat"
CB_ADM_PERM_ROLE_PREFIX  = "adm:perm:r:"   # adm:perm:r:<role>
CB_ADM_PERM_TOGGLE_PREFIX = "adm:perm:t:"  # adm:perm:t:<role>:<perm>
CB_ADM_PERM_RESET_PREFIX = "adm:perm:rs:"  # adm:perm:rs:<role>
CB_ADM_PERM_RESET_ALL    = "adm:perm:ra"
CB_ADM_ORDER_VIEW_PREFIX = "adm:ov:"    # adm:ov:<order_id>
CB_ADM_ORDER_ENABLE_PREFIX   = "adm:oen:"   # adm:oen:<order_id>
CB_ADM_ORDER_DISABLE_PREFIX  = "adm:odis:"  # adm:odis:<order_id>
CB_ADM_ORDER_DELETE_ASK_PREFIX = "adm:odelask:"  # adm:odelask:<order_id>
CB_ADM_ORDER_DELETE_OK_PREFIX  = "adm:odelok:"   # adm:odelok:<order_id>
CB_ADM_ORDER_DELETE_CANCEL     = "adm:odelno"
CB_ADM_ORDER_EDIT_PLAN_PREFIX  = "adm:oepl:"   # adm:oepl:<order_id>
CB_ADM_ORDER_ADD_GB_PREFIX     = "adm:ogb:"    # adm:ogb:<order_id>:<gb>
CB_ADM_ORDER_ADD_DAYS_PREFIX   = "adm:ody:"    # adm:ody:<order_id>:<days>
CB_ADM_ORDER_SET_GB_ASK_PREFIX = "adm:ogbask:" # adm:ogbask:<order_id>
CB_ADM_ORDER_ADD_DAYS_ASK_PREFIX = "adm:odyask:" # adm:odyask:<order_id>
CB_ADM_USER_BAN_PREFIX       = "adm:ban:"   # adm:ban:<user_id>
CB_ADM_USER_UNBAN_PREFIX     = "adm:unban:" # adm:unban:<user_id>
CB_ADM_USER_UPDATE_PREFIX    = "adm:uupd:"  # adm:uupd:<user_id>
CB_ADM_LOC_DETAIL_PREFIX = "adm:ld:"    # adm:ld:<location_id>
CB_ADM_LOC_EDIT_PREFIX   = "adm:le:"    # adm:le:<location_id>
CB_ADM_LOC_TOGGLE_PREFIX = "adm:lt:"    # adm:lt:<location_id>
CB_ADM_LOC_PURCHASE_PREFIX = "adm:lp:"  # adm:lp:<location_id>
CB_ADM_TOOL_SYNC         = "adm:tsync"
CB_ADM_TOOL_CLEAR        = "adm:tclr"
CB_ADM_TOOL_CLEAR_TEST   = "adm:tclrt"
CB_ADM_ADD_CLIENT        = "adm:addcl"
CB_ADM_ADD_CLIENT_SKIP_USER = "adm:acsk"
CB_ADM_ADD_CLIENT_LOC_PREFIX = "adm:acl:"  # adm:acl:<location_id>
CB_ADM_BROADCAST         = "adm:bcast"
CB_BROADCAST_CONFIRM     = "adm:bcast:ok"
CB_BROADCAST_CANCEL      = "adm:bcast:no"
CB_ADM_PLANS             = "adm:plans"
CB_ADM_VOL_DEL_PREFIX    = "adm:vd:"   # adm:vd:<gb>
CB_ADM_DUR_DEL_PREFIX    = "adm:dd:"   # adm:dd:<days>
CB_ADM_LOC_PURGE_PREFIX  = "adm:pg:"   # adm:pg:<location_id> → purge confirm

# Admin destructive actions (require explicit confirmation)
CB_PURGE_CONFIRM_PREFIX = "adm:prg:ok:"  # adm:prg:ok:<location_id>
CB_PURGE_CANCEL         = "adm:prg:no"

# Inbound picker (wizard step for selecting inbounds from panel API)
CB_ADM_INBOUND_TOGGLE_PREFIX = "adm:ibt:"   # adm:ibt:<inbound_id>
CB_ADM_INBOUND_CONFIRM       = "adm:ibconf"
CB_ADM_INBOUND_SKIP          = "adm:ibskip"  # fallback: enter manually

# Subscription picker (wizard step for selecting default vs custom vs skip)
CB_ADM_SUB_DEFAULT = "adm:sub:def"
CB_ADM_SUB_SKIP    = "adm:sub:skip"

# My services
CB_MY_LIST                  = "my:list"
CB_MY_DETAIL_PREFIX         = "my:o:"        # my:o:<order_id>
CB_MY_CONFIGS_PREFIX        = "my:cfg:"      # my:cfg:<order_id>
CB_MY_CONFIGS_FILTER_PREFIX = "my_cfg_f:" # my_cfg_f:<order_id>:<btn_index>
CB_MY_REFRESH_USAGE_PREFIX  = "my:ref:"      # my:ref:<order_id> — refresh usage on detail
CB_MY_TOGGLE_PREFIX         = "my:tog:"      # my:tog:<order_id>
CB_MY_RENAME_PREFIX         = "my:ren:"      # my:ren:<order_id>
CB_MY_REGEN_PREFIX          = "my:rg:"       # my:rg:<order_id>      (asks confirmation)
CB_MY_REGEN_CONFIRM_PREFIX  = "my:rg:ok:"    # my:rg:ok:<order_id>   (does it)
CB_MY_RENEW_PREFIX          = "my:rn:"       # my:rn:<order_id>      (starts renew flow)
CB_MY_DELETE_PREFIX         = "my:del:"      # my:del:<order_id>     (asks confirmation)
CB_MY_DELETE_CONFIRM_PREFIX = "my:del:ok:"   # my:del:ok:<order_id>  (does it)


# ---------- reply keyboard (bottom menu, replaces phone keyboard) ----------
def main_reply_keyboard(*, show_test: bool = False) -> ReplyKeyboardMarkup:
    """Persistent bottom buttons — main navigation for buyers."""
    rows: list[list[KeyboardButton]] = []
    if show_test:
        rows.append([KeyboardButton(text=texts.BTN_TEST_SUB)])
    rows.extend([
        [
            KeyboardButton(text=texts.BTN_MY_SERVICES, style='primary'),
            KeyboardButton(text=texts.BTN_BUY, style='success'),
        ],
        [
            KeyboardButton(text=texts.BTN_MY_ACCOUNT),
            KeyboardButton(text=texts.BTN_SUPPORT),
        ],
        [
            KeyboardButton(text=texts.BTN_HELP),
            KeyboardButton(text=texts.BTN_ABOUT),
        ],
    ])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
    )


def hide_reply_keyboard() -> ReplyKeyboardRemove:
    """Hide bottom buttons during wizards (order, support, rename)."""
    return ReplyKeyboardRemove()


# All main-menu button labels — use with F.text.in_(...) + StateFilter(None).
MAIN_MENU_BUTTONS = frozenset({
    texts.BTN_BUY,
    texts.BTN_TEST_SUB,
    texts.BTN_MY_SERVICES,
    texts.BTN_MY_ACCOUNT,
    texts.BTN_SUPPORT,
    texts.BTN_HELP,
    texts.BTN_ABOUT,
})

ADMIN_MENU_BUTTONS = frozenset({
    texts.ADMIN_BTN_DASHBOARD,
    texts.ADMIN_BTN_PENDING,
    texts.ADMIN_BTN_SETTINGS,
    texts.ADMIN_BTN_LOCATIONS,
    texts.ADMIN_BTN_TOOLS,
    texts.ADMIN_BTN_USERS,
    texts.ADMIN_BTN_CUSTOMERS,
    texts.ADMIN_BTN_PANEL,
})


# ---------- inline keyboards (inside messages / wizards) ----------
def main_menu(*, show_test: bool = False) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_test:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_TEST_SUB, callback_data=CB_MAIN_TEST, style='success'
            ),
        ])
    rows.extend([
        [
            InlineKeyboardButton(text=texts.BTN_MY_SERVICES, callback_data=CB_MAIN_MY_SERVICES, style='primary'),
            InlineKeyboardButton(text=texts.BTN_BUY,         callback_data=CB_MAIN_BUY,         style='success'),
        ],
        [
            InlineKeyboardButton(text=texts.BTN_MY_ACCOUNT, callback_data=CB_MAIN_ACCOUNT,style='primary'),
            InlineKeyboardButton(text=texts.BTN_SUPPORT,    callback_data=CB_MAIN_SUPPORT,style='primary'),
        ],
        [
            InlineKeyboardButton(text=texts.BTN_HELP,  callback_data=CB_MAIN_HELP,style='primary'),
            InlineKeyboardButton(text=texts.BTN_ABOUT, callback_data=CB_MAIN_ABOUT,style='primary'),
        ],
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def join_channel_keyboard(join_url: str | None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if join_url:
        rows.append([
            InlineKeyboardButton(text=texts.BTN_JOIN_CHANNEL, url=join_url,style='success'),
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CHECK_JOIN, callback_data=CB_MAIN_CHECK_JOIN, style='primary'
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def test_sub_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_CONFIRM, callback_data="test:confirm", style='success'
                ),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_MAIN_HOME, style='danger'),
            ],
        ]
    )


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME,style='danger')]
        ]
    )


# ---------- order flow ----------
def locations(locations: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locations:
        rows.append(
            [InlineKeyboardButton(text=loc.name, callback_data=f"{CB_LOC_PREFIX}{loc.id}",style='primary')]
        )
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME,style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def _chunk_buttons(
    buttons: list[InlineKeyboardButton], per_row: int = 3
) -> list[list[InlineKeyboardButton]]:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for btn in buttons:
        row.append(btn)
        if len(row) >= per_row:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return rows


def volumes(volume_presets_gb: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(text=f"{gb} GB", callback_data=f"{CB_VOL_PREFIX}{gb}",style='primary')
        for gb in volume_presets_gb
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([InlineKeyboardButton(text=texts.BTN_CUSTOM, callback_data=CB_VOL_CUSTOM,style='primary')])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_LOC,style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def durations(duration_presets_days: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(text=f"{d} روزه", callback_data=f"{CB_DUR_PREFIX}{d}",style='primary')
        for d in duration_presets_days
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_VOL,style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def service_packages(packages: list, db) -> InlineKeyboardMarkup:
    """One plan per row: two buttons (volume + term/price), same callback each."""
    rows: list[list[InlineKeyboardButton]] = []
    for pkg in packages:
        cb = f"{CB_SVC_PREFIX}{pkg.id}"
        final = db.resolve_price(int(pkg.price))
        rows.append([
            InlineKeyboardButton(
                text=texts.format_service_package_term(pkg.duration_days, final),
                callback_data=cb,
            style='primary'),
            InlineKeyboardButton(
                text=texts.format_service_package_volume(pkg.volume_gb),
                callback_data=cb,
            style='primary'),
        ])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ORDER_BACK_LOC,style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_order(*, back_callback: str = CB_ORDER_BACK_DUR) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CONFIRM, callback_data=CB_ORDER_CONFIRM, style='success')],
            [InlineKeyboardButton(text=texts.BTN_BACK, callback_data=back_callback,style='danger')],
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ORDER_CANCEL, style='danger')],
        ]
    )


def cancel_only() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ORDER_CANCEL, style='danger')]
        ]
    )


# ---------- support ----------
def cancel_support() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_CANCEL_SUPPORT, style='danger')]
        ]
    )


def admin_support_ticket(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.SUPPORT_ADMIN_REPLY, callback_data=f"{CB_SUPPORT_REPLY_PREFIX}{ticket_id}", style='primary',
                ),
                InlineKeyboardButton(
                    text=texts.SUPPORT_ADMIN_CLOSE, callback_data=f"{CB_SUPPORT_CLOSE_PREFIX}{ticket_id}", style='danger',
                ),
            ],
        ]
    )


# ---------- admin destructive confirmation ----------
def purge_confirm(location_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ بله، پاک کن",
                    callback_data=f"{CB_PURGE_CONFIRM_PREFIX}{location_id}",
                    style='danger',
                ),
                InlineKeyboardButton(
                    text="❌ انصراف", callback_data=CB_PURGE_CANCEL, style='danger'
                ),
            ]
        ]
    )


# ---------- my services ----------
def my_services_list(orders: list[dict]) -> InlineKeyboardMarkup:
    """`orders` is a list of dicts with keys: id, label, status."""
    rows: list[list[InlineKeyboardButton]] = []
    for o in orders:
        style = 'danger' if o.get("status") in ("expired", "quota_exhausted") else 'primary'
        rows.append([
            InlineKeyboardButton(text=o["label"], callback_data=f"{CB_MY_DETAIL_PREFIX}{o['id']}", style=style)
        ])
    rows.append([InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_MAIN_HOME, style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def my_service_detail(
    order_id: int, *, provisioned: bool, enabled: bool, is_test: bool = False, status: str = "provisioned"
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    
    if status in ("expired", "quota_exhausted"):
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_REFRESH_USAGE,
                callback_data=f"{CB_MY_REFRESH_USAGE_PREFIX}{order_id}",
                style='primary'
            ),
        ])
        if not is_test:
            rows.append([
                InlineKeyboardButton(
                    text="♻️ تمدید سرویس",
                    callback_data=f"{CB_MY_RENEW_PREFIX}{order_id}",
                    style='success'
                ),
            ])
            rows.append([
                InlineKeyboardButton(
                    text="🗑️ حذف سرویس",
                    callback_data=f"{CB_MY_DELETE_PREFIX}{order_id}",
                    style='danger'
                ),
            ])
    elif provisioned:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_VIEW_CONFIGS,
                callback_data=f"{CB_MY_CONFIGS_PREFIX}{order_id}",
            style='success'),
        ])
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_REFRESH_USAGE,
                callback_data=f"{CB_MY_REFRESH_USAGE_PREFIX}{order_id}",
            style='primary'),
        ])
        if not is_test:
            toggle_text = texts.BTN_TOGGLE_OFF if enabled else texts.BTN_TOGGLE_ON
            rows.append([
                InlineKeyboardButton(
                    text=toggle_text, callback_data=f"{CB_MY_TOGGLE_PREFIX}{order_id}",
                style='primary'),
                InlineKeyboardButton(
                    text=texts.BTN_RENAME, callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}",
                style='primary'),
            ])
            rows.append([
                InlineKeyboardButton(
                    text=texts.BTN_REGEN, callback_data=f"{CB_MY_REGEN_PREFIX}{order_id}",
                style='primary'),
            ])
            rows.append([
                InlineKeyboardButton(
                    text="♻️ تمدید سرویس", callback_data=f"{CB_MY_RENEW_PREFIX}{order_id}",
                style='success'),
            ])
    elif not is_test:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_RENAME, callback_data=f"{CB_MY_RENAME_PREFIX}{order_id}",
            style='primary'),
        ])
    rows.append([InlineKeyboardButton(text="🔙 لیست سرویس‌ها", callback_data=CB_MY_LIST,style='danger')])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def delete_confirm(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🗑️ بله، سرویس حذف شود", callback_data=f"{CB_MY_DELETE_CONFIRM_PREFIX}{order_id}", style='success'),
            ],
            [
                InlineKeyboardButton(text="🔙 انصراف", callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}", style='danger'),
            ],
        ]
    )


def back_to_service(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🔙 جزئیات سرویس", callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}",style='danger')
        ]]
    )


def regen_confirm(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts.BTN_REGEN_CONFIRM, callback_data=f"{CB_MY_REGEN_CONFIRM_PREFIX}{order_id}", style='success'),
            ],
            [
                InlineKeyboardButton(text=texts.BTN_BACK,
                                     callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}",style='danger'),
            ],
        ]
    )


# ---------- admin reply keyboard ----------
# ---------- admin reply keyboard ----------
def _admin_perm(user_id: int, perm: str, settings, db) -> bool:
    from app.admin_perms import has_permission

    return has_permission(user_id, perm, settings, db)


def admin_reply_keyboard(user_id: int, settings, db) -> ReplyKeyboardMarkup:
    from app.admin_perms import (
        CUSTOMERS,
        LOCATIONS,
        PANEL,
        OFFER,
        ORDERS_REVIEW,
        SERVICES,
        SETTINGS,
        TOOLS_BROADCAST,
        TOOLS_MISC,
        TOOLS_SYNC,
        USERS,
    )

    rows: list[list[KeyboardButton]] = []
    if _admin_perm(user_id, PANEL, settings, db):
        rows.append([KeyboardButton(text=texts.ADMIN_BTN_DASHBOARD)])

    review_row: list[KeyboardButton] = []
    if _admin_perm(user_id, ORDERS_REVIEW, settings, db):
        review_row.append(KeyboardButton(text=texts.ADMIN_BTN_PENDING))
    if _admin_perm(user_id, CUSTOMERS, settings, db):
        review_row.append(KeyboardButton(text=texts.ADMIN_BTN_CUSTOMERS))
    if review_row:
        rows.append(review_row)

    operations_row: list[KeyboardButton] = []
    if _admin_perm(user_id, LOCATIONS, settings, db):
        operations_row.append(KeyboardButton(text=texts.ADMIN_BTN_LOCATIONS))
    if _admin_perm(user_id, TOOLS_BROADCAST, settings, db) or _admin_perm(
        user_id, TOOLS_SYNC, settings, db
    ) or _admin_perm(user_id, TOOLS_MISC, settings, db
    ):
        operations_row.append(KeyboardButton(text=texts.ADMIN_BTN_TOOLS))
    if _admin_perm(user_id, USERS, settings, db):
        operations_row.append(KeyboardButton(text=texts.ADMIN_BTN_USERS))
    if operations_row:
        rows.append(operations_row)

    settings_row: list[KeyboardButton] = []
    if _admin_perm(user_id, SETTINGS, settings, db) or _admin_perm(
        user_id, OFFER, settings, db
    ):
        settings_row.append(KeyboardButton(text=texts.ADMIN_BTN_SETTINGS))
    if _admin_perm(user_id, SERVICES, settings, db):
        settings_row.append(KeyboardButton(text=texts.ADMIN_BTN_SERVICES))
    if settings_row:
        rows.append(settings_row)

    return ReplyKeyboardMarkup(
        keyboard=rows or [[KeyboardButton(text=texts.ADMIN_BTN_DASHBOARD)]],
        resize_keyboard=True,
    )


# ---------- admin panel inline ----------
def admin_home_inline(user_id: int, settings, db) -> InlineKeyboardMarkup:
    from app.admin_perms import (
        CUSTOMERS,
        LOCATIONS,
        OFFER,
        ORDERS_MANAGE,
        ORDERS_REVIEW,
        SERVICES,
        SETTINGS,
        TOOLS_BROADCAST,
        TOOLS_MISC,
        TOOLS_SYNC,
        USERS,
    )

    rows: list[list[InlineKeyboardButton]] = []

    order_row: list[InlineKeyboardButton] = []
    if _admin_perm(user_id, ORDERS_REVIEW, settings, db):
        order_row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_PENDING, callback_data=CB_ADM_PENDING_LIST, style='primary'
            )
        )
    if _admin_perm(user_id, ORDERS_MANAGE, settings, db):
        order_row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_ORDER_LOOKUP,
                callback_data=CB_ADM_ORDER_LOOKUP,
            style='primary')
        )
    if order_row:
        rows.append(order_row)

    if _admin_perm(user_id, CUSTOMERS, settings, db):
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_CUSTOMERS, callback_data=CB_ADM_CUSTOMERS,
            style='primary'),
        ])

    if _admin_perm(user_id, ORDERS_MANAGE, settings, db):
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_ADD_CLIENT, callback_data=CB_ADM_ADD_CLIENT, style='primary'
            ),
        ])

    if _admin_perm(user_id, USERS, settings, db):
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_USERS, callback_data=CB_ADM_USERS,
            style='primary')
        ])

    r3: list[InlineKeyboardButton] = []
    if _admin_perm(user_id, SETTINGS, settings, db) or _admin_perm(
        user_id, SERVICES, settings, db
    ) or _admin_perm(user_id, OFFER, settings, db):
        r3.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_SETTINGS, callback_data=CB_ADM_SETTINGS,
            style='primary')
        )
    if _admin_perm(user_id, LOCATIONS, settings, db):
        r3.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_LOCATIONS,
                callback_data=CB_ADM_LOCATIONS_LIST,
            style='success')
        )
    if r3:
        rows.append(r3)

    if _admin_perm(user_id, TOOLS_BROADCAST, settings, db) or _admin_perm(
        user_id, TOOLS_SYNC, settings, db
    ) or _admin_perm(user_id, TOOLS_MISC, settings, db
    ):
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_TOOLS, callback_data=CB_ADM_TOOLS,
            style='primary')
        ])

    from app.admin_perms import is_owner

    if is_owner(user_id, settings):
        rows.append([
            InlineKeyboardButton(
                text="👮 دسترسی ادمین‌ها", callback_data=CB_ADM_ROLES,
            style='primary')
        ])

    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_CMD_HELP_BTN, callback_data=CB_ADM_CMD_HELP,
        style='primary')
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_pending_footer(user_id: int, settings, db) -> InlineKeyboardMarkup:
    """Footer under pending list / empty queue (refresh, lookup, home)."""
    from app.admin_perms import ORDERS_MANAGE, ORDERS_REVIEW

    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    if _admin_perm(user_id, ORDERS_REVIEW, settings, db):
        row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_PENDING_LIST, style='primary'
            )
        )
    if _admin_perm(user_id, ORDERS_MANAGE, settings, db):
        row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_ORDER_LOOKUP,
                callback_data=CB_ADM_ORDER_LOOKUP,
            style='primary')
        )
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_flow_cancel_inline(*, back_data: str = CB_ADM_HOME) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'
                ),
                InlineKeyboardButton(text=texts.BTN_BACK, callback_data=back_data,style='danger'),
            ],
        ]
    )


def admin_sub_picker(*, has_default: bool = True) -> InlineKeyboardMarkup:
    rows = []
    if has_default:
        rows.append([
            InlineKeyboardButton(
                text="✅ استفاده از لینک پیشنهادی",
                callback_data=CB_ADM_SUB_DEFAULT,
                style='success'
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="⏭️ بدون لینک اشتراک (رد کردن)",
            callback_data=CB_ADM_SUB_SKIP,
            style='primary'
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CANCEL,
            callback_data=CB_ADM_FLOW_CANCEL,
            style='danger'
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_inbound_picker(
    inbounds: list[dict],
    selected_ids: list[int],
    *,
    back_data: str = CB_ADM_HOME,
) -> InlineKeyboardMarkup:
    """Inline keyboard for picking inbounds from panel.

    Each inbound appears as a toggleable button. Selected ones get ✅.
    Bottom row has Confirm + Enter Manually buttons.
    """
    selected_set = set(selected_ids)
    rows = []
    for ib in inbounds:
        ib_id = ib.get("id", 0)
        label = ib.get("remark") or ib.get("tag") or str(ib_id)
        protocol = ib.get("protocol", "")
        icon = "✅" if ib_id in selected_set else "☑️"
        display = f"{icon} {label}"
        if protocol:
            display += f" ({protocol})"
        rows.append([
            InlineKeyboardButton(
                text=display,
                callback_data=f"{CB_ADM_INBOUND_TOGGLE_PREFIX}{ib_id}",
            )
        ])
    # Action row
    confirm_text = "✔️ تأیید انتخاب" if selected_set else "✔️ تأیید"
    rows.append([
        InlineKeyboardButton(text=confirm_text, callback_data=CB_ADM_INBOUND_CONFIRM),
        InlineKeyboardButton(text="⌨️ دستی", callback_data=CB_ADM_INBOUND_SKIP),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)



def admin_offer_inline(db) -> InlineKeyboardMarkup:
    """`db` — Database for refresh button state."""
    presets = [10, 15, 20, 25, 30]
    pct_row = [
        InlineKeyboardButton(
            text=f"{p}٪",
            callback_data=f"{CB_ADM_OFFER_PCT_PREFIX}{p}",
        style='primary')
        for p in presets
    ]
    return InlineKeyboardMarkup(
        inline_keyboard=[
            pct_row,
            [
                InlineKeyboardButton(
                    text="✏️ درصد دلخواه",
                    callback_data=CB_ADM_OFFER_PCT_CUSTOM,
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text="💵 کم کردن مبلغ",
                    callback_data=CB_ADM_OFFER_AMOUNT,
                style='primary'),
                InlineKeyboardButton(
                    text="🏷 قیمت ثابت همه",
                    callback_data=CB_ADM_OFFER_FIXED,
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text="❌ خاموش کردن تخفیف", callback_data=CB_ADM_OFFER_CLEAR, style='danger',
                ),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_OFFER,
                style='primary'),
                InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SETTINGS,style='danger'),
            ],
        ]
    )


def admin_settings_inline(user_id: int, settings, db) -> InlineKeyboardMarkup:
    from app.admin_perms import OFFER, SERVICES, SETTINGS, is_owner

    rows: list[list[InlineKeyboardButton]] = []
    if _admin_perm(user_id, OFFER, settings, db):
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_OFFER, callback_data=CB_ADM_OFFER,
            style='danger'),
        ])
    hint_row: list[InlineKeyboardButton] = []
    if _admin_perm(user_id, SETTINGS, settings, db):
        hint_row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_SETCARD_HELP, callback_data=CB_ADM_SETCARD_HELP,
            style='primary')
        )
        hint_row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_SETPRICE_HELP, callback_data=CB_ADM_SETPRICE_HELP,
            style='primary')
        )
    if hint_row:
        rows.append(hint_row)
    plan_row: list[InlineKeyboardButton] = []
    if _admin_perm(user_id, SERVICES, settings, db):
        plan_row.append(
            InlineKeyboardButton(text="📋 پلن‌های پایه", callback_data=CB_ADM_PLANS,style='primary')
        )
        plan_row.append(
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_SERVICES, callback_data=CB_ADM_SERVICES,
            style='primary')
        )
    if plan_row:
        rows.append(plan_row)
    if is_owner(user_id, settings):
        rows.append([
            InlineKeyboardButton(
                text="👮 دسترسی ادمین‌ها", callback_data=CB_ADM_ROLES,
            style='primary'),
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_SETTINGS_REFRESH,
        style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_roles_keyboard(settings, db) -> InlineKeyboardMarkup:
    from app.admin_perms import VALID_ROLES, is_owner

    short = {
        "manager": "🛠 مدیر",
        "reviewer": "🔍 بررسی",
        "support": "💬 پشتیبانی",
        "viewer": "👁 مشاهده",
    }
    rows: list[list[InlineKeyboardButton]] = []
    for uid, _role in db.list_staff_roles(settings.admin_ids):
        if is_owner(uid, settings):
            continue
        rows.append([
            InlineKeyboardButton(
                text=short.get(r, r),
                callback_data=f"{CB_ADM_ROLE_SET_PREFIX}{uid}:{r}",
            style='primary')
            for r in VALID_ROLES
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_PERM_MATRIX,
            callback_data=CB_ADM_PERM_MATRIX,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SETTINGS,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_perm_matrix_home_keyboard() -> InlineKeyboardMarkup:
    from app.role_permissions import CONFIGURABLE_ROLES
    from app.texts import ADMIN_ROLE_LABELS

    rows: list[list[InlineKeyboardButton]] = []
    for role in CONFIGURABLE_ROLES:
        label = ADMIN_ROLE_LABELS.get(role, role)
        rows.append([
            InlineKeyboardButton(
                text=f"✏️ {label}",
                callback_data=f"{CB_ADM_PERM_ROLE_PREFIX}{role}",
            style='primary'),
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_PERM_RESET_ALL,
            callback_data=CB_ADM_PERM_RESET_ALL,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_ROLES,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_perm_role_keyboard(role: str, db) -> InlineKeyboardMarkup:
    from app.role_permissions import (
        PERM_LABELS,
        TOGGLABLE_PERMS,
        permissions_for_role,
    )

    rows: list[list[InlineKeyboardButton]] = []
    perms = permissions_for_role(db, role)
    pair: list[InlineKeyboardButton] = []
    for perm in TOGGLABLE_PERMS:
        on = perm in perms
        label = f"{'✅' if on else '❌'} {PERM_LABELS[perm]}"
        pair.append(
            InlineKeyboardButton(
                text=label,
                callback_data=f"{CB_ADM_PERM_TOGGLE_PREFIX}{role}:{perm}",
            style='primary')
        )
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_PERM_RESET_ROLE,
            callback_data=f"{CB_ADM_PERM_RESET_PREFIX}{role}",
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_BACK, callback_data=CB_ADM_PERM_MATRIX,
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_services_inline(*, manual_enabled: bool) -> InlineKeyboardMarkup:
    toggle_label = (
        "🔀 خاموش کردن خرید دکمه‌ای"
        if manual_enabled
        else "🔀 روشن کردن خرید دکمه‌ای"
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_label, callback_data=CB_ADM_TOGGLE_MANUAL,
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_ADD_SVC_HELP, callback_data=CB_ADM_ADD_SVC,
                style='success'),
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_EDIT_SVC_HELP, callback_data=CB_ADM_EDITSVC_HELP,
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_SERVICES_REFRESH,
                style='primary'),
                InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SETTINGS,style='danger'),
            ],
        ]
    )


def admin_plans_keyboard(
    volume_presets: list[int], duration_presets: list[int]
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for gb in volume_presets:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ حذف {gb} GB",
                callback_data=f"{CB_ADM_VOL_DEL_PREFIX}{gb}",
            style='primary')
        ])
    for days in duration_presets:
        rows.append([
            InlineKeyboardButton(
                text=f"❌ حذف {days} روز",
                callback_data=f"{CB_ADM_DUR_DEL_PREFIX}{days}",
            style='primary')
        ])
    rows.append([
        InlineKeyboardButton(
            text="➕ راهنمای افزودن", callback_data=CB_ADM_PLAN_ADD_HINT,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_PLANS,style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SETTINGS,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_users_keyboard(
    users: list, *, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    """`users` — sqlite3.Row or dict with user_id, first_name, username."""
    rows: list[list[InlineKeyboardButton]] = []
    for u in users:
        uid = int(u["user_id"])
        label = (u["first_name"] or "").strip() or str(uid)
        if len(label) > 18:
            label = label[:17] + "…"
        rows.append([
            InlineKeyboardButton(
                text=f"👤 {label}",
                callback_data=f"{CB_ADM_USER_DETAIL_PREFIX}{uid}",
            style='primary')
        ])
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"{CB_ADM_USERS_PAGE_PREFIX}{page - 1}",
            style='primary')
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"{CB_ADM_USERS_PAGE_PREFIX}{page + 1}",
            style='primary')
        )
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_USERS,style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_user_detail_keyboard(
    user_id: int,
    actor_id: int,
    settings,
    db,
    *,
    is_banned: bool = False,
    order_ids: list[int] | None = None,
) -> InlineKeyboardMarkup:
    from app.admin_perms import ORDERS_MANAGE, USERS

    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=texts.BTN_USER_INFO,
                callback_data=f"{CB_ADM_USER_INFO_PREFIX}{user_id}",
            style='primary'),
        ],
    ]
    if _admin_perm(actor_id, USERS, settings, db):
        ban_btn = (
            InlineKeyboardButton(
                text=texts.BTN_USER_UNBAN, callback_data=f"{CB_ADM_USER_UNBAN_PREFIX}{user_id}", style='success',
            )
            if is_banned
            else InlineKeyboardButton(
                text=texts.BTN_USER_BAN, callback_data=f"{CB_ADM_USER_BAN_PREFIX}{user_id}", style='danger',
            )
        )
        rows.append([ban_btn])
    rows.append([
        InlineKeyboardButton(
            text="🔄 بروزرسانی از تلگرام", callback_data=f"{CB_ADM_USER_UPDATE_PREFIX}{user_id}", style='primary',
        )
    ])
    if order_ids and _admin_perm(actor_id, ORDERS_MANAGE, settings, db):
        order_row: list[InlineKeyboardButton] = []
        for oid in order_ids[:6]:
            order_row.append(
                InlineKeyboardButton(
                    text=f"{texts.ADMIN_BTN_ORDER_MANAGE} #{oid}",
                    callback_data=f"{CB_ADM_ORDER_MANAGE_PREFIX}{oid}",
                style='primary')
            )
            if len(order_row) == 2:
                rows.append(order_row)
                order_row = []
        if order_row:
            rows.append(order_row)
    rows.append([
        InlineKeyboardButton(
            text="🔙 لیست کاربران", callback_data=CB_ADM_USERS,
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_customers_keyboard(
    customers: list, *, page: int, total_pages: int
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    customer_btns: list[InlineKeyboardButton] = []
    for c in customers:
        uid = int(c["user_id"])
        label = (c["first_name"] or "").strip() or (c["username"] or "").strip() or str(uid)
        if len(label) > 16:
            label = label[:15] + "…"
        orders_n = int(c["order_count"])
        customer_btns.append(
            InlineKeyboardButton(
                text=f"🛒 {label} ({orders_n})",
                callback_data=f"{CB_ADM_CUST_DETAIL_PREFIX}{uid}",
            style='primary')
        )
    rows.extend(_chunk_buttons(customer_btns, per_row=3))
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(
            InlineKeyboardButton(
                text="◀️ قبلی",
                callback_data=f"{CB_ADM_CUSTOMERS_PAGE_PREFIX}{page - 1}",
            style='primary')
        )
    if page < total_pages - 1:
        nav.append(
            InlineKeyboardButton(
                text="بعدی ▶️",
                callback_data=f"{CB_ADM_CUSTOMERS_PAGE_PREFIX}{page + 1}",
            style='primary')
        )
    if nav:
        rows.append(nav)
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_CUSTOMERS_SEARCH,
            callback_data=CB_ADM_CUSTOMERS_SEARCH,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_CUSTOMERS,
        style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_customers_search_keyboard(customers: list) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    customer_btns: list[InlineKeyboardButton] = []
    for c in customers:
        uid = int(c["user_id"])
        label = (c["first_name"] or "").strip() or (c["username"] or "").strip() or str(uid)
        if len(label) > 18:
            label = label[:17] + "…"
        customer_btns.append(
            InlineKeyboardButton(
                text=f"🛒 {label}",
                callback_data=f"{CB_ADM_CUST_DETAIL_PREFIX}{uid}",
            style='primary')
        )
    rows.extend(_chunk_buttons(customer_btns, per_row=3))
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_CUSTOMERS_SEARCH,
            callback_data=CB_ADM_CUSTOMERS_SEARCH,
        style='primary'),
        InlineKeyboardButton(
            text="🔙 لیست مشتریان", callback_data=CB_ADM_CUSTOMERS,
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_customer_detail_keyboard(
    user_id: int,
    actor_id: int,
    settings,
    db,
    *,
    is_banned: bool = False,
    order_ids: list[int] | None = None,
) -> InlineKeyboardMarkup:
    from app.admin_perms import ORDERS_MANAGE, USERS

    row2: list[InlineKeyboardButton] = [
        InlineKeyboardButton(
            text="👥 نمای کاربران",
            callback_data=f"{CB_ADM_USER_DETAIL_PREFIX}{user_id}",
        style='primary'),
    ]
    if _admin_perm(actor_id, USERS, settings, db):
        ban_btn = (
            InlineKeyboardButton(
                text=texts.BTN_USER_UNBAN, callback_data=f"{CB_ADM_CUST_UNBAN_PREFIX}{user_id}", style='success',
            )
            if is_banned
            else InlineKeyboardButton(
                text=texts.BTN_USER_BAN, callback_data=f"{CB_ADM_CUST_BAN_PREFIX}{user_id}", style='danger',
            )
        )
        row2.append(ban_btn)
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=texts.BTN_USER_INFO,
                callback_data=f"{CB_ADM_USER_INFO_PREFIX}{user_id}",
            style='primary'),
        ],
        row2,
        [
            InlineKeyboardButton(
                text="🔄 بروزرسانی از تلگرام", callback_data=f"{CB_ADM_USER_UPDATE_PREFIX}{user_id}", style='primary',
            ),
        ],
        [
            InlineKeyboardButton(
                text="📩 ارسال پیام خصوصی", callback_data=f"{CB_ADM_PM_PREFIX}{user_id}", style='primary',
            ),
        ],
    ]
    if order_ids and _admin_perm(actor_id, ORDERS_MANAGE, settings, db):
        order_row: list[InlineKeyboardButton] = []
        for oid in order_ids[:8]:
            order_row.append(
                InlineKeyboardButton(
                    text=f"{texts.ADMIN_BTN_ORDER_MANAGE} #{oid}",
                    callback_data=f"{CB_ADM_ORDER_MANAGE_PREFIX}{oid}",
                style='primary')
            )
            if len(order_row) == 2:
                rows.append(order_row)
                order_row = []
        if order_row:
            rows.append(order_row)
    rows.append([
        InlineKeyboardButton(
            text="🔙 لیست مشتریان", callback_data=CB_ADM_CUSTOMERS,
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order_plan_edit_keyboard(order_id: int) -> InlineKeyboardMarkup:
    """Quick edits for panel traffic + expiry."""
    oid = order_id
    p = CB_ADM_ORDER_ADD_GB_PREFIX
    d = CB_ADM_ORDER_ADD_DAYS_PREFIX
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="+1 GB", callback_data=f"{p}{oid}:1",
                style='primary'),
                InlineKeyboardButton(
                    text="+5 GB", callback_data=f"{p}{oid}:5",
                style='primary'),
                InlineKeyboardButton(
                    text="+10 GB", callback_data=f"{p}{oid}:10",
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_ORDER_SET_GB,
                    callback_data=f"{CB_ADM_ORDER_SET_GB_ASK_PREFIX}{oid}",
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text="+7 روز", callback_data=f"{d}{oid}:7",
                style='primary'),
                InlineKeyboardButton(
                    text="+30 روز", callback_data=f"{d}{oid}:30",
                style='primary'),
                InlineKeyboardButton(
                    text="+90 روز", callback_data=f"{d}{oid}:90",
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_ORDER_ADD_DAYS,
                    callback_data=f"{CB_ADM_ORDER_ADD_DAYS_ASK_PREFIX}{oid}",
                style='success'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.BTN_BACK,
                    callback_data=f"{CB_ADM_ORDER_MANAGE_PREFIX}{oid}",
                style='danger'),
            ],
        ]
    )


def admin_edit_order_keyboard(
    order_id: int,
    *,
    show_panel_actions: bool,
    show_db_delete: bool = True,
    back_data: str | None = CB_ADM_PENDING_LIST,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if show_panel_actions:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_ORDER_EDIT_PLAN,
                callback_data=f"{CB_ADM_ORDER_EDIT_PLAN_PREFIX}{order_id}",
            style='primary'),
        ])
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_ORDER_ENABLE,
                callback_data=f"{CB_ADM_ORDER_ENABLE_PREFIX}{order_id}",
            style='success'),
            InlineKeyboardButton(
                text=texts.BTN_ORDER_DISABLE,
                callback_data=f"{CB_ADM_ORDER_DISABLE_PREFIX}{order_id}",
            style='danger'),
        ])
    if show_db_delete:
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_ORDER_DELETE,
                callback_data=f"{CB_ADM_ORDER_DELETE_ASK_PREFIX}{order_id}",
            style='danger'),
        ])
    if back_data:
        rows.append([
            InlineKeyboardButton(text=texts.BTN_BACK, callback_data=back_data,style='danger'),
        ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_order_delete_confirm(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_ORDER_DELETE_CONFIRM,
                    callback_data=f"{CB_ADM_ORDER_DELETE_OK_PREFIX}{order_id}",
                style='danger'),
                InlineKeyboardButton(
                    text=texts.BTN_CANCEL,
                    callback_data=CB_ADM_ORDER_DELETE_CANCEL,
                style='danger'),
            ],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_SEND,
                    callback_data=CB_BROADCAST_CONFIRM,
                style='primary'),
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_CANCEL,
                    callback_data=CB_BROADCAST_CANCEL,
                style='danger'),
            ],
        ]
    )


def broadcast_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_BROADCAST_CANCEL,
                    callback_data=CB_BROADCAST_CANCEL,
                style='danger'),
            ],
        ]
    )


def admin_tools_inline(
    user_id: int,
    settings,
    db,
    *,
    has_log_channel: bool,
    has_req_channel: bool,
) -> InlineKeyboardMarkup:
    from app.admin_perms import TOOLS_BROADCAST, TOOLS_MISC, TOOLS_SYNC

    rows: list[list[InlineKeyboardButton]] = []
    if _admin_perm(user_id, TOOLS_BROADCAST, settings, db):
        rows.append([
            InlineKeyboardButton(
                text=texts.BTN_ADMIN_BROADCAST, callback_data=CB_ADM_BROADCAST,
            style='primary'),
        ])
    if _admin_perm(user_id, TOOLS_MISC, settings, db):
        log_row: list[InlineKeyboardButton] = [
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_LOG_CHANNEL, callback_data=CB_ADM_LOG_CHANNEL,
            style='primary'),
        ]
        if has_log_channel:
            log_row.append(
                InlineKeyboardButton(
                    text="❌ قطع لاگ", callback_data=CB_ADM_LOG_CHANNEL_OFF,
                style='danger')
            )
        rows.append(log_row)
        req_row: list[InlineKeyboardButton] = [
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_REQ_CHANNEL, callback_data=CB_ADM_REQ_CHANNEL,
            style='primary'),
        ]
        if has_req_channel:
            req_row.append(
                InlineKeyboardButton(
                    text="❌ قطع عضویت اجباری",
                    callback_data=CB_ADM_REQ_CHANNEL_OFF,
                style='danger')
            )
        rows.append(req_row)
        rows.append([
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_TOGGLE_TEST, callback_data=CB_ADM_TOGGLE_TEST,
            style='primary'),
        ])
    if _admin_perm(user_id, TOOLS_SYNC, settings, db):
        rows.append([
            InlineKeyboardButton(
                text="🔄 همگام‌سازی پنل", callback_data=CB_ADM_TOOL_SYNC,
            style='primary'),
            InlineKeyboardButton(
                text="🗑 پاکسازی رد/پرداخت‌نشده", callback_data=CB_ADM_TOOL_CLEAR,
            style='primary'),
        ])
        rows.append([
            InlineKeyboardButton(
                text="🧹 پاکسازی دیتابیس ربات از اکانت های تست (جهت اجازه دادن به کاربران قدیمی برای ساخت مجدد)", callback_data=CB_ADM_TOOL_CLEAR_TEST,
            style='danger'),
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_CMD_HELP_BTN, callback_data=CB_ADM_CMD_HELP,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_TOOLS,
        style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_pending_list(
    orders: list[dict], user_id: int, settings, db
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for o in orders:
        rows.append([
            InlineKeyboardButton(
                text=o["label"],
                callback_data=f"{CB_ADM_ORDER_VIEW_PREFIX}{o['id']}",
            style='primary')
        ])
    footer = (admin_pending_footer(user_id, settings, db)).inline_keyboard
    rows.extend(footer)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_add_client_user_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'
                ),
            ],
        ]
    )


def admin_add_service_locations(locs: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locs:
        emoji = _location_list_emoji(loc)
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} #{loc.id} {loc.name}",
                callback_data=f"{CB_ADM_ADD_SVC_LOC_PREFIX}{loc.id}",
            style='primary')
        ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_SERVICES,style='danger'),
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_add_service_volumes(volume_presets_gb: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(
            text=f"{gb} GB",
            callback_data=f"{CB_ADM_ADD_SVC_VOL_PREFIX}{gb}",
        style='primary')
        for gb in volume_presets_gb
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CUSTOM, callback_data=CB_ADM_ADD_SVC_VOL_CUSTOM,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_ADD_SVC_BACK_LOC,style='danger'),
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_add_service_durations(duration_presets_days: list[int]) -> InlineKeyboardMarkup:
    preset_btns = [
        InlineKeyboardButton(
            text=f"{d} روز",
            callback_data=f"{CB_ADM_ADD_SVC_DUR_PREFIX}{d}",
        style='primary')
        for d in duration_presets_days
    ]
    rows = _chunk_buttons(preset_btns, per_row=3)
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CUSTOM, callback_data=CB_ADM_ADD_SVC_DUR_CUSTOM,
        style='primary'),
    ])
    rows.append([
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_ADD_SVC_BACK_VOL,style='danger'),
        InlineKeyboardButton(text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_add_service_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_ADD_SVC_HELP,
                    callback_data=CB_ADM_ADD_SVC,
                style='success'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_SERVICES, callback_data=CB_ADM_SERVICES,
                style='primary'),
            ],
        ]
    )


def admin_add_client_locations(locs: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locs:
        rows.append([
            InlineKeyboardButton(
                text=loc.name,
                callback_data=f"{CB_ADM_ADD_CLIENT_LOC_PREFIX}{loc.id}",
            style='primary')
        ])
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CANCEL, callback_data=CB_ADM_FLOW_CANCEL, style='danger'
        ),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_add_client_done_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_ADD_CLIENT,
                    callback_data=CB_ADM_ADD_CLIENT,
                style='success'),
            ],
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_PANEL, callback_data=CB_ADM_HOME,
                style='primary'),
            ],
        ]
    )


def _location_list_emoji(loc: Location) -> str:
    if not loc.enabled:
        return "🔴"
    if not loc.purchase_enabled:
        return "🟡"
    return "🟢"


def admin_locations_list(locs: list[Location]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for loc in locs:
        emoji = _location_list_emoji(loc)
        rows.append([
            InlineKeyboardButton(
                text=f"{emoji} #{loc.id} {loc.name}",
                callback_data=f"{CB_ADM_LOC_DETAIL_PREFIX}{loc.id}",
            style='primary')
        ])
    rows.append(admin_locations_list_footer())
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_REFRESH, callback_data=CB_ADM_LOCATIONS_LIST,
        style='primary'),
        InlineKeyboardButton(text=texts.BTN_BACK, callback_data=CB_ADM_HOME,style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_location_detail(
    location_id: int,
    *,
    enabled: bool,
    purchase_enabled: bool,
    is_test: bool = False,
) -> InlineKeyboardMarkup:
    toggle_label = "🔴 غیرفعال کردن لوکیشن" if enabled else "🟢 فعال کردن لوکیشن"
    purchase_label = (
        "🛑 بستن خرید جدید"
        if purchase_enabled
        else "🛒 باز کردن خرید جدید"
    )
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text=texts.ADMIN_BTN_EDIT_LOC,
                callback_data=f"{CB_ADM_LOC_EDIT_PREFIX}{location_id}",
            style='primary'),
        ],
        [
            InlineKeyboardButton(
                text="🎛 دکمه‌های دریافت کانفیگ",
                callback_data=f"{CB_ADM_LOC_BTNS_PREFIX}{location_id}",
            style='primary'),
        ],
        [
            InlineKeyboardButton(
                text=toggle_label,
                callback_data=f"{CB_ADM_LOC_TOGGLE_PREFIX}{location_id}",
            style='primary'),
        ],
    ]
    if not is_test:
        rows.append(
            [
                InlineKeyboardButton(
                    text=purchase_label,
                    callback_data=f"{CB_ADM_LOC_PURCHASE_PREFIX}{location_id}",
                style='primary'),
            ]
        )
    rows.append(
        [
            InlineKeyboardButton(
                text="⚠️ حذف کامل لوکیشن",
                callback_data=f"{CB_ADM_LOC_PURGE_PREFIX}{location_id}",
            style='primary'),
        ]
    )
    if is_test:
        rows.insert(
            1,
            [
                InlineKeyboardButton(
                    text=texts.ADMIN_BTN_TOGGLE_TEST,
                    callback_data=f"{CB_ADM_TOGGLE_TEST_LOC_PREFIX}{location_id}",
                style='primary'),
            ],
        )
    rows.append([
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_ADD_LOC_HELP, callback_data=CB_ADM_ADD_LOC,
        style='success'),
    ])
    rows.append([
        InlineKeyboardButton(
            text="🔙 لیست لوکیشن‌ها", callback_data=CB_ADM_LOCATIONS_LIST,
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_locations_list_footer() -> list[InlineKeyboardButton]:
    return [
        InlineKeyboardButton(
            text=texts.ADMIN_BTN_ADD_LOC_HELP, callback_data=CB_ADM_ADD_LOC,
        style='success'),
    ]


# ---------- admin review ----------
def decline_reason_keyboard(order_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for preset_id, label, _msg in texts.DECLINE_PRESETS:
        row.append(
            InlineKeyboardButton(
                text=label,
                callback_data=(
                    f"{CB_ADMIN_DECLINE_PRESET_PREFIX}{order_id}:{preset_id}"
                ),
            style='primary')
        )
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_CANCEL,
            callback_data=f"{CB_ADMIN_DECLINE_CANCEL_PREFIX}{order_id}",
        style='danger'),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_review(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=texts.BTN_ACCEPT, callback_data=f"{CB_ADMIN_ACCEPT_PREFIX}{order_id}",
                style='success'),
                InlineKeyboardButton(
                    text=texts.BTN_DECLINE, callback_data=f"{CB_ADMIN_DECLINE_PREFIX}{order_id}",
                style='primary'),
            ],
            [
                InlineKeyboardButton(
                    text=f"{texts.ADMIN_BTN_ORDER_MANAGE} #{order_id}",
                    callback_data=f"{CB_ADM_ORDER_MANAGE_PREFIX}{order_id}",
                style='primary'),
                InlineKeyboardButton(
                    text=texts.BTN_USER_INFO,
                    callback_data=f"{CB_ADM_USER_INFO_PREFIX}{user_id}",
                style='primary'),
            ],
        ]
    )

def admin_location_config_buttons(
    location_id: int,
    buttons: list[dict[str, str]]
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    
    for i, btn in enumerate(buttons):
        rows.append([
            InlineKeyboardButton(
                text=f"🗑 حذف: {btn.get('name')}",
                callback_data=f"{CB_ADM_LOC_BTN_DEL_PREFIX}{location_id}:{i}",
                style="danger"
            )
        ])
        
    rows.append([
        InlineKeyboardButton(
            text="➕ افزودن دکمه جدید",
            callback_data=f"{CB_ADM_LOC_BTN_ADD_PREFIX}{location_id}",
            style="primary"
        )
    ])
    rows.append([
        InlineKeyboardButton(
            text=texts.BTN_BACK,
            callback_data=f"{CB_ADM_LOC_DETAIL_PREFIX}{location_id}",
            style="danger"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def view_configs_keyboard(order_id: int, buttons: list[dict[str, str]]) -> InlineKeyboardMarkup:
    rows = []
    for i, btn in enumerate(buttons):
        rows.append([
            InlineKeyboardButton(
                text=btn.get('name', 'دریافت کانفیگ'),
                callback_data=f"{CB_MY_CONFIGS_FILTER_PREFIX}{order_id}:{i}",
                style="primary"
            )
        ])
    rows.append([
        InlineKeyboardButton(
            text="🔙 جزئیات سرویس", 
            callback_data=f"{CB_MY_DETAIL_PREFIX}{order_id}",
            style="danger"
        )
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
