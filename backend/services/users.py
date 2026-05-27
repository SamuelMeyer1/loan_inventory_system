from __future__ import annotations

import random
import re
from typing import Any

from backend.database import connect, row, rows
from backend.services.common import log_event, now_text, optional_text


def list_users(include_inactive: bool = False) -> list[dict[str, Any]]:
    if include_inactive:
        return rows("SELECT * FROM users ORDER BY active DESC, name")
    return rows("SELECT * FROM users WHERE active = 1 ORDER BY name")


def make_user_id(first_name: str, last_name: str, alias: str, email: str) -> str:
    if alias:
        base = alias
    elif email:
        base = email.split("@")[0]
    else:
        base = f"{first_name}.{last_name}"
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base.strip().lower()).strip("-")
    base = base or "user"
    candidate = base
    counter = 1
    while row("SELECT user_id FROM users WHERE user_id = ?", (candidate,)):
        counter += 1
        candidate = f"{base}-{counter}"
    return candidate


def make_alias() -> str:
    while True:
        alias = f"A{random.randint(0, 999999):06d}"
        if not row("SELECT user_id FROM users WHERE lower(alias) = lower(?)", (alias,)):
            return alias


def add_user(payload: dict[str, Any]) -> dict[str, Any]:
    first_name = optional_text(payload, "first_name")
    last_name = optional_text(payload, "last_name")
    email = optional_text(payload, "email")
    phone = optional_text(payload, "phone")
    company = optional_text(payload, "company")
    alias = optional_text(payload, "alias") or make_alias()
    department = optional_text(payload, "department")
    department_name = optional_text(payload, "department_name")
    role = optional_text(payload, "role") or "operator"
    active = 1 if payload.get("active", True) else 0

    if not first_name:
        raise ValueError("Ange förnamn.")
    if not last_name:
        raise ValueError("Ange efternamn.")
    if email and "@" not in email:
        raise ValueError("Ange en giltig e-postadress.")
    if role not in ("operator", "admin", "superadmin"):
        raise ValueError("Ogiltig roll.")
    if email and row("SELECT user_id FROM users WHERE lower(email) = lower(?)", (email,)):
        raise ValueError("Det finns redan en användare med den e-postadressen.")
    if not re.fullmatch(r"A\d{6}", alias):
        raise ValueError("Alias ska vara A följt av 6 siffror, t.ex. A123456.")
    if alias and row("SELECT user_id FROM users WHERE lower(alias) = lower(?)", (alias,)):
        raise ValueError("Det finns redan en användare med det aliaset.")

    user_id = make_user_id(first_name, last_name, alias, email)
    name = f"{first_name} {last_name}".strip()
    timestamp = now_text()

    with connect() as db:
        db.execute(
            """
            INSERT INTO users (
                user_id, name, first_name, last_name, email, phone, company, alias,
                department, department_name, role, created_at, updated_at, active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                role,
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
    alias = optional_text(payload, "alias") or existing.get("alias") or make_alias()
    department = optional_text(payload, "department")
    department_name = optional_text(payload, "department_name")
    role = optional_text(payload, "role") or "operator"
    active = 1 if payload.get("active", True) else 0

    if not first_name:
        raise ValueError("Ange förnamn.")
    if not last_name:
        raise ValueError("Ange efternamn.")
    if email and "@" not in email:
        raise ValueError("Ange en giltig e-postadress.")
    if role not in ("operator", "admin", "superadmin"):
        raise ValueError("Ogiltig roll.")
    if email and row("SELECT user_id FROM users WHERE lower(email) = lower(?) AND user_id != ?", (email, user_id)):
        raise ValueError("Det finns redan en användare med den e-postadressen.")
    if not re.fullmatch(r"A\d{6}", alias):
        raise ValueError("Alias ska vara A följt av 6 siffror, t.ex. A123456.")
    if alias and row("SELECT user_id FROM users WHERE lower(alias) = lower(?) AND user_id != ?", (alias, user_id)):
        raise ValueError("Det finns redan en användare med det aliaset.")

    name = f"{first_name} {last_name}".strip()
    timestamp = now_text()
    with connect() as db:
        db.execute(
            """
            UPDATE users
            SET name = ?, first_name = ?, last_name = ?, email = ?, phone = ?, company = ?,
                alias = ?, department = ?, department_name = ?, role = ?, updated_at = ?, active = ?
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
