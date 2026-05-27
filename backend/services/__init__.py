from __future__ import annotations

from backend.services.inventory import (
    add_object,
    delete_object,
    list_objects,
    search_objects,
    update_object,
)
from backend.services.loans import (
    checkout,
    close_consumable_report,
    create_consumable_report,
    create_loan_request,
    delete_loan_request,
    issue_item,
    list_active_loans,
    list_consumable_reports,
    list_loan_requests,
    recent_events,
    return_item,
    update_loan_request_status,
)
from backend.services.notifications import get_system_settings, send_loan_reminders, update_system_settings
from backend.services.stats import dashboard_stats, statistics_data
from backend.services.users import add_user, list_users, remove_user, update_user

__all__ = [
    "add_object",
    "add_user",
    "checkout",
    "close_consumable_report",
    "create_consumable_report",
    "create_loan_request",
    "dashboard_stats",
    "delete_loan_request",
    "delete_object",
    "get_system_settings",
    "issue_item",
    "list_active_loans",
    "list_consumable_reports",
    "list_loan_requests",
    "list_objects",
    "list_users",
    "recent_events",
    "remove_user",
    "return_item",
    "search_objects",
    "send_loan_reminders",
    "statistics_data",
    "update_loan_request_status",
    "update_object",
    "update_system_settings",
    "update_user",
]
