from aiogram import Router

from app.handlers import (
    admin,
    admin_broadcast,
    admin_customers,
    admin_offer,
    admin_location_edit,
    admin_location_config_buttons,
    admin_add_client,
    admin_add_service,
    admin_order,
    admin_roles,
    admin_permission_management,
    log_channel,
    required_channel,
    admin_panel,
    my_services,
    order,
    review,
    start,
    support,
    test_sub,
)


def build_root_router() -> Router:
    """Combine all feature routers into a single router for the dispatcher.

    Order matters slightly: state-scoped handlers in `order`, `review` and
    `my_services` are evaluated before the generic command/menu handlers,
    so things like /cancel inside an FSM flow are caught first.
    """
    root = Router(name="root")
    root.include_router(order.router)
    root.include_router(review.router)
    root.include_router(my_services.router)
    root.include_router(test_sub.router)
    root.include_router(start.router)
    root.include_router(support.router)
    root.include_router(admin_broadcast.router)
    root.include_router(admin_order.router)
    root.include_router(log_channel.router)
    root.include_router(required_channel.router)
    root.include_router(admin_customers.router)
    root.include_router(admin_offer.router)
    root.include_router(admin_location_edit.router)
    root.include_router(admin_location_config_buttons.router)
    root.include_router(admin_add_client.router)
    root.include_router(admin_add_service.router)
    root.include_router(admin_roles.router)
    root.include_router(admin_permission_management.router)
    root.include_router(admin_panel.router)
    root.include_router(admin.router)
    return root
