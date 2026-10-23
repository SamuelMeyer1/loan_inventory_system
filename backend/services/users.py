from __future__ import annotations

import random
import uuid
import re
from typing import Any

from backend.database import connect, row, rows
from backend.services.common import log_event, now_text, optional_text


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_PATTERN = re.compile(r"^[0-9+ ()-]+$")


def list_users(include_inactive: bool = False) -> list[dict[str, Any]]:
    where = "" if include_inactive else "WHERE u.active = 1"
    users = rows(
        f"""
        SELECT u.*,
               (
                   SELECT COUNT(*)
                   FROM loans l
                   WHERE l.user_id = u.user_id
                     AND l.status = 'active'
                     AND l.due_time < datetime('now', 'localtime')
               ) AS overdue_loan_count
        FROM users u
        {where}
        ORDER BY u.active DESC, u.name
        """
    )
    setting = row("SELECT value FROM system_settings WHERE key = 'overdue_block_limit'")
    enabled_setting = row("SELECT value FROM system_settings WHERE key = 'overdue_block_enabled'")
    block_enabled = (enabled_setting or {}).get("value") == "1"
    try:
        block_limit = max(1, int((setting or {}).get("value") or "3"))
    except ValueError:
        block_limit = 3
    for user in users:
        overdue_count = int(user.get("overdue_loan_count") or 0)
        override_enabled = int(user.get("borrow_override") or 0) == 1
        user["borrow_blocked"] = int(block_enabled and overdue_count >= block_limit and not override_enabled)
        user["borrow_block_limit"] = block_limit
    return users


def list_groups() -> list[dict[str, Any]]:
    return rows(
        """
        SELECT g.group_id, g.name, g.department, g.created_at, g.updated_at,
               COUNT(u.user_id) AS user_count
        FROM user_groups g
        LEFT JOIN users u ON lower(u.department_name) = lower(g.name) AND u.active = 1
        GROUP BY g.group_id, g.name, g.department, g.created_at, g.updated_at
        ORDER BY g.name
        """
    )


def create_group(payload: dict[str, Any]) -> dict[str, Any]:
    name = optional_text(payload, "name")
    department = optional_text(payload, "department")
    if not name:
        raise ValueError("Ange gruppnamn.")
    if not department:
        raise ValueError("Ange avdelning för gruppen.")
    if len(name) > 80:
        raise ValueError("Gruppnamnet är för långt.")
    if row("SELECT group_id FROM user_groups WHERE lower(name) = lower(?)", (name,)):
        raise ValueError("Gruppen finns redan.")

    timestamp = now_text()
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO user_groups (name, department, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, department, timestamp, timestamp),
        )
        group_id = int(cursor.lastrowid)
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Grupp skapad: {name}"),
        )
    return {"group_id": group_id, "name": name, "department": department}


def update_group(payload: dict[str, Any]) -> dict[str, Any]:
    group_id = int(payload.get("group_id", 0))
    name = optional_text(payload, "name")
    department = optional_text(payload, "department")
    if group_id <= 0:
        raise ValueError("Ange grupp-ID.")
    if not name:
        raise ValueError("Ange gruppnamn.")
    if not department:
        raise ValueError("Ange avdelning för gruppen.")
    if len(name) > 80:
        raise ValueError("Gruppnamnet är för långt.")

    existing = row("SELECT * FROM user_groups WHERE group_id = ?", (group_id,))
    if existing is None:
        raise ValueError("Gruppen hittades inte.")
    if row("SELECT group_id FROM user_groups WHERE lower(name) = lower(?) AND group_id != ?", (name, group_id)):
        raise ValueError("Gruppen finns redan.")

    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE user_groups SET name = ?, department = ?, updated_at = ? WHERE group_id = ?",
            (name, department, timestamp, group_id),
        )
        db.execute(
            """
            UPDATE users
            SET department_name = ?, department = ?, updated_at = ?
            WHERE lower(department_name) = lower(?)
            """,
            (name, department, timestamp, existing["name"]),
        )
        db.execute(
            """
            UPDATE system_settings
            SET value = ?, updated_at = ?
            WHERE key LIKE 'notification_recipients_%'
              AND lower(value) = lower(?)
            """,
            (name, timestamp, existing["name"]),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Grupp uppdaterad: {existing['name']} -> {name} ({department})"),
        )
    return {"group_id": group_id, "name": name, "department": department}


def delete_group(group_id: int) -> dict[str, Any]:
    if group_id <= 0:
        raise ValueError("Ange grupp-ID.")
    group = row("SELECT * FROM user_groups WHERE group_id = ?", (group_id,))
    if group is None:
        raise ValueError("Gruppen hittades inte.")
    active_users = row(
        "SELECT COUNT(*) AS value FROM users WHERE active = 1 AND lower(department_name) = lower(?)",
        (group["name"],),
    )
    if active_users and int(active_users["value"] or 0) > 0:
        raise ValueError("Gruppen används av aktiva användare och kan inte tas bort.")

    timestamp = now_text()
    with connect() as db:
        db.execute("DELETE FROM user_groups WHERE group_id = ?", (group_id,))
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Grupp borttagen: {group['name']}"),
        )
    return {"group_id": group_id}


def make_user_id(first_name: str, last_name: str, alias: str, email: str) -> str:
    return "usr-" + uuid.uuid4().hex


def make_alias() -> str:
    while True:
        alias = f"A{random.randint(0, 999999):06d}"
        if not row("SELECT user_id FROM users WHERE lower(alias) = lower(?)", (alias,)):
            return alias


def make_rfid_code() -> str:
    while True:
        code = f"KORT-{random.randint(0, 9999999999):010d}"
        if not row("SELECT user_id FROM users WHERE lower(rfid_code) = lower(?)", (code,)):
            return code


def validate_user_fields(first_name: str, last_name: str, email: str, phone: str, company: str, role: str) -> None:
    if not first_name:
        raise ValueError("Ange förnamn.")
    if not last_name:
        raise ValueError("Ange efternamn.")
    if not email:
        raise ValueError("Ange e-postadress.")
    if not EMAIL_PATTERN.fullmatch(email):
        raise ValueError("Ange en giltig e-postadress.")
    if phone and not PHONE_PATTERN.fullmatch(phone):
        raise ValueError("Telefonnummer får bara innehålla siffror och telefontecken.")
    if role not in ("operator", "admin", "superadmin"):
        raise ValueError("Ogiltig roll.")


def group_for_name(department_name: str) -> dict[str, Any] | None:
    if not department_name:
        return None
    return row("SELECT * FROM user_groups WHERE lower(name) = lower(?)", (department_name,))


def resolve_group_department(department_name: str, department: str = "") -> str:
    group = group_for_name(department_name)
    if not department_name:
        return department
    if not group:
        raise ValueError("Välj en befintlig grupp eller skapa gruppen först.")
    return str(group["department"] or "").strip()


def add_user(payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("privacy_notice_acknowledged") is not True:
        raise ValueError("Personen måste först ta del av och bekräfta informationen om personuppgifter.")
    first_name = optional_text(payload, "first_name")
    last_name = optional_text(payload, "last_name")
    email = optional_text(payload, "email")
    phone = optional_text(payload, "phone")
    company = optional_text(payload, "company")
    alias = optional_text(payload, "alias") or make_alias()
    rfid_code = optional_text(payload, "rfid_code")
    department = optional_text(payload, "department")
    department_name = optional_text(payload, "department_name")
    role = optional_text(payload, "role") or "operator"
    active = 1 if payload.get("active", True) else 0

    validate_user_fields(first_name, last_name, email, phone, company, role)
    department = resolve_group_department(department_name, department)
    if email and row("SELECT user_id FROM users WHERE lower(email) = lower(?)", (email,)):
        raise ValueError("Det finns redan en användare med den e-postadressen.")
    if rfid_code and row("SELECT user_id FROM users WHERE lower(rfid_code) = lower(?)", (rfid_code,)):
        raise ValueError("Det finns redan en användare med den kortkoden.")

    user_id = make_user_id(first_name, last_name, alias, email)
    name = f"{first_name} {last_name}".strip()
    timestamp = now_text()

    with connect() as db:
        db.execute(
            """
            INSERT INTO users (
                user_id, name, first_name, last_name, email, phone, company, alias,
                department, department_name, rfid_code, role, created_at, updated_at,
                privacy_notice_acknowledged_at, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                name,
                first_name,
                last_name,
                email,
                phone,
                company,
                alias,
                department,
                department_name,
                rfid_code,
                role,
                timestamp,
                timestamp,
                timestamp,
                active,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Användare skapad: {name} ({user_id})"),
        )

    return {"user_id": user_id}


def update_user(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    if not user_id:
        raise ValueError("Ange användare.")

    existing = row("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing is None:
        raise ValueError("Användaren hittades inte.")

    first_name = optional_text(payload, "first_name")
    last_name = optional_text(payload, "last_name")
    email = optional_text(payload, "email")
    phone = optional_text(payload, "phone")
    company = optional_text(payload, "company")
    alias = optional_text(payload, "alias") or existing["alias"] or make_alias()
    rfid_code = optional_text(payload, "rfid_code")
    department = optional_text(payload, "department")
    department_name = optional_text(payload, "department_name")
    role = optional_text(payload, "role") or "operator"
    active = 1 if payload.get("active", True) else 0

    validate_user_fields(first_name, last_name, email, phone, company, role)
    department = resolve_group_department(department_name, department)
    if email and row("SELECT user_id FROM users WHERE lower(email) = lower(?) AND user_id != ?", (email, user_id)):
        raise ValueError("Det finns redan en användare med den e-postadressen.")
    if rfid_code and row("SELECT user_id FROM users WHERE lower(rfid_code) = lower(?) AND user_id != ?", (rfid_code, user_id)):
        raise ValueError("Det finns redan en användare med den kortkoden.")

    name = f"{first_name} {last_name}".strip()
    timestamp = now_text()
    with connect() as db:
        db.execute(
            """
            UPDATE users
            SET name = ?, first_name = ?, last_name = ?, email = ?, phone = ?, company = ?,
                alias = ?, department = ?, department_name = ?, rfid_code = ?, role = ?, updated_at = ?, active = ?
            WHERE user_id = ?
            """,
            (
                name,
                first_name,
                last_name,
                email,
                phone,
                company,
                alias,
                department,
                department_name,
                rfid_code,
                role,
                timestamp,
                active,
                user_id,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Användare uppdaterad: {name} ({user_id})"),
        )
    return {"user_id": user_id}


def set_user_card(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    rfid_code = optional_text(payload, "rfid_code") or make_rfid_code()
    if not user_id:
        raise ValueError("Ange användare.")
    existing = row("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing is None:
        raise ValueError("Användaren hittades inte.")
    if row("SELECT user_id FROM users WHERE lower(rfid_code) = lower(?) AND user_id != ?", (rfid_code, user_id)):
        raise ValueError("Det finns redan en användare med den kortkoden.")

    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE users SET rfid_code = ?, updated_at = ? WHERE user_id = ?",
            (rfid_code, timestamp, user_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Kortkod uppdaterad: {existing['name']} ({user_id})"),
        )
    return {"user_id": user_id, "rfid_code": rfid_code}


def set_user_borrow_override(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    enabled = 1 if payload.get("enabled") in (True, 1, "1", "true", "yes", "on") else 0
    if not user_id:
        raise ValueError("Ange användare.")
    existing = row("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing is None:
        raise ValueError("Användaren hittades inte.")

    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE users SET borrow_override = ?, updated_at = ? WHERE user_id = ?",
            (enabled, timestamp, user_id),
        )
        message = "Manuell låneoverride aktiverad" if enabled else "Manuell låneoverride borttagen"
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"{message}: {existing['name']} ({user_id})"),
        )
    return {"user_id": user_id, "borrow_override": enabled}


def remove_user(user_id: str) -> dict[str, Any]:
    user_id = user_id.strip()
    if not user_id:
        raise ValueError("Ange användare.")

    existing = row("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if existing is None:
        raise ValueError("Användaren hittades inte.")

    timestamp = now_text()
    with connect() as db:
        db.execute("UPDATE users SET active = 0, updated_at = ? WHERE user_id = ?", (timestamp, user_id))
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "user", f"Användare borttagen/inaktiverad: {existing['name']} ({user_id})"),
        )
    return {"user_id": user_id}
