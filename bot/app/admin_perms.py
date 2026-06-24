"""Admin roles and permissions (owner + limited staff)."""

from __future__ import annotations

from typing import Final

from app.config import Settings
from app.db import Database

# Permission keys
PANEL = "panel"
DASHBOARD = "dashboard"
ORDERS_REVIEW = "orders_review"
ORDERS_MANAGE = "orders_manage"
USERS = "users"
CUSTOMERS = "customers"
SETTINGS = "settings"
SERVICES = "services"
OFFER = "offer"
LOCATIONS = "locations"
TOOLS_BROADCAST = "tools_broadcast"
TOOLS_SYNC = "tools_sync"
TOOLS_MISC = "tools_misc"
MANAGE_ADMINS = "manage_admins"

ALL_PERMS: frozenset[str] = frozenset({
    PANEL,
    DASHBOARD,
    ORDERS_REVIEW,
    ORDERS_MANAGE,
    USERS,
    CUSTOMERS,
    SETTINGS,
    SERVICES,
    OFFER,
    LOCATIONS,
    TOOLS_BROADCAST,
    TOOLS_SYNC,
    TOOLS_MISC,
    MANAGE_ADMINS,
})

ROLE_OWNER = "owner"
ROLE_MANAGER = "manager"
ROLE_REVIEWER = "reviewer"
ROLE_SUPPORT = "support"
ROLE_VIEWER = "viewer"

VALID_ROLES: Final[tuple[str, ...]] = (
    ROLE_MANAGER,
    ROLE_REVIEWER,
    ROLE_SUPPORT,
    ROLE_VIEWER,
)


def owner_id(settings: Settings) -> int | None:
    return settings.admin_ids[0] if settings.admin_ids else None


def is_staff(user_id: int, settings: Settings) -> bool:
    return user_id in settings.admin_ids


def is_owner(user_id: int, settings: Settings) -> bool:
    oid = owner_id(settings)
    return oid is not None and user_id == oid


def get_role(user_id: int, settings: Settings, db: Database) -> str:
    if is_owner(user_id, settings):
        return ROLE_OWNER
    return db.get_admin_role(user_id)


def permissions_for(user_id: int, settings: Settings, db: Database) -> frozenset[str]:
    from app.role_permissions import permissions_for_role

    role = get_role(user_id, settings, db)
    return permissions_for_role(db, role)


def has_permission(
    user_id: int, perm: str, settings: Settings, db: Database
) -> bool:
    if not is_staff(user_id, settings):
        return False
    if is_owner(user_id, settings):
        return True
    return perm in permissions_for(user_id, settings, db)


def can_access_panel(user_id: int, settings: Settings, db: Database) -> bool:
    return has_permission(user_id, PANEL, settings, db)
