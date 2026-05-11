from __future__ import annotations

import re
import smtplib
import random
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

from backend.database import connect, row, rows


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def object_status(available_quantity: int, min_quantity: int) -> str:
    if available_quantity <= 0:
        return "Slut"
    if available_quantity <= min_quantity:
        return "Låg nivå"
    return "Tillgänglig"


def log_event(event_type: str, message: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), event_type, message),
        )


def open_door(tornado_id: str, door_id: str, reason: str) -> None:
    log_event("lock", f"{tornado_id} - Door {door_id} opened ({reason})")


def dashboard_stats() -> dict[str, int]:
    object_count = row("SELECT COUNT(*) AS value FROM objects")
    loaned_count = row("SELECT COALESCE(SUM(quantity), 0) AS value FROM loans WHERE status = 'active'")
    overdue_count = row(
        """
        SELECT COUNT(*) AS value
        FROM loans
        WHERE status = 'active' AND due_time < datetime('now', 'localtime')
        """
    )
    low_stock_count = row("SELECT COUNT(*) AS value FROM objects WHERE available_quantity <= min_quantity")
    jobs_count = row("SELECT COUNT(*) AS value FROM loan_requests WHERE status IN ('requested', 'prepared', 'loaned', 'returned')")
    consumable_count = row("SELECT COUNT(*) AS value FROM consumable_reports WHERE status = 'open'")
    return {
        "objects": int(object_count["value"] if object_count else 0),
        "loaned": int(loaned_count["value"] if loaned_count else 0),
        "overdue": int(overdue_count["value"] if overdue_count else 0),
        "low_stock": int(low_stock_count["value"] if low_stock_count else 0),
        "jobs": int(jobs_count["value"] if jobs_count else 0),
        "consumable_reports": int(consumable_count["value"] if consumable_count else 0),
    }


SYSTEM_SETTING_DEFAULTS = {
    "modbus_enabled": "0",
    "modbus_host": "",
    "modbus_port": "502",
    "modbus_unit_id": "1",
    "modbus_register_start": "",
    "smtp_enabled": "0",
    "smtp_host": "",
    "smtp_port": "587",
    "smtp_username": "",
    "smtp_password": "",
    "smtp_from_address": "",
    "smtp_use_tls": "1",
    "notification_recipients": "",
    "notify_new_job": "1",
    "notify_low_stock": "1",
    "notify_loan_reminders": "1",
    "loan_reminder_days": "1",
}


def get_system_settings() -> dict[str, str]:
    settings = SYSTEM_SETTING_DEFAULTS.copy()
    for item in rows("SELECT key, value FROM system_settings"):
        settings[item["key"]] = item["value"]
    return settings


def update_system_settings(payload: dict[str, Any]) -> dict[str, str]:
    settings = get_system_settings()
    for key in SYSTEM_SETTING_DEFAULTS:
        value = payload.get(key, settings[key])
        if key.endswith("_enabled") or key.startswith("notify_"):
            settings[key] = "1" if value in (True, "1", "true", "yes", "on") else "0"
        elif key == "smtp_use_tls":
            settings[key] = "1" if value in (True, "1", "true", "yes", "on") else "0"
        elif key == "smtp_password" and str(value or "") == "":
            settings[key] = settings.get(key, "")
        else:
            settings[key] = str(value or "").strip()

    if settings["modbus_port"] and not settings["modbus_port"].isdigit():
        raise ValueError("Modbus-port måste vara ett tal.")
    if settings["modbus_unit_id"] and not settings["modbus_unit_id"].isdigit():
        raise ValueError("Modbus Unit ID måste vara ett tal.")
    if settings["smtp_port"] and not settings["smtp_port"].isdigit():
        raise ValueError("SMTP-port måste vara ett tal.")

    if settings["loan_reminder_days"] and not settings["loan_reminder_days"].isdigit():
        raise ValueError("PÃ¥minnelsedagar mÃ¥ste vara ett tal.")

    timestamp = now_text()
    with connect() as db:
        for key, value in settings.items():
            db.execute(
                """
                INSERT INTO system_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
                """,
                (key, value, timestamp),
            )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "settings", "Systeminställningar uppdaterades"),
        )
    return settings


def parse_email_list(value: str) -> list[str]:
    return [email.strip() for email in re.split(r"[,;\n]+", value or "") if email.strip()]


def smtp_ready(settings: dict[str, str]) -> bool:
    return (
        settings.get("smtp_enabled") == "1"
        and bool(settings.get("smtp_host"))
        and bool(settings.get("smtp_port"))
        and bool(settings.get("smtp_from_address"))
    )


def send_email(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    recipients = [recipient for recipient in recipients if recipient]
    if not recipients:
        return 0
    if not smtp_ready(settings):
        raise ValueError("SMTP Ã¤r inte komplett konfigurerat.")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["smtp_from_address"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)

    with smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=15) as smtp:
        smtp.ehlo()
        if settings.get("smtp_use_tls", "1") == "1":
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if settings.get("smtp_username"):
            smtp.login(settings["smtp_username"], settings.get("smtp_password", ""))
        smtp.send_message(message)
    return len(recipients)


def notify_recipients(subject: str, body: str, settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    recipients = parse_email_list(settings.get("notification_recipients", ""))
    if not recipients or not smtp_ready(settings):
        return 0
    return send_email(subject, body, recipients, settings)


def send_loan_reminders() -> dict[str, int]:
    settings = get_system_settings()
    if settings.get("notify_loan_reminders") != "1":
        raise ValueError("LÃ¥nepÃ¥minnelser Ã¤r inte aktiva.")
    if not smtp_ready(settings):
        raise ValueError("SMTP Ã¤r inte komplett konfigurerat.")

    reminder_days = int(settings.get("loan_reminder_days") or "1")
    latest_due = datetime.now() + timedelta(days=reminder_days)
    candidates = rows(
        """
        SELECT l.*, u.name AS user_name, u.email AS user_email,
               o.name AS object_name, o.object_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        WHERE l.status = 'active'
          AND u.email IS NOT NULL
          AND trim(u.email) != ''
          AND l.due_time <= ?
        ORDER BY l.due_time ASC
        """,
        (latest_due.strftime("%Y-%m-%d %H:%M:%S"),),
    )

    sent = 0
    for loan in candidates:
        due_time = (loan["due_time"] or "")[:16]
        subject = f"PÃ¥minnelse: {loan['object_name']} ska lÃ¤mnas tillbaka"
        body = (
            f"Hej {loan['user_name']},\n\n"
            f"Det hÃ¤r Ã¤r en pÃ¥minnelse om att {loan['quantity']} x {loan['object_name']} "
            f"({loan['object_id']}) ska lÃ¤mnas tillbaka senast {due_time}.\n\n"
            "Tack!"
        )
        sent += send_email(subject, body, [loan["user_email"]], settings)

    log_event("notification", f"LÃ¥nepÃ¥minnelser skickade: {sent}")
    return {"matched": len(candidates), "sent": sent}


def list_objects(search: str = "", category: str = "Alla", status: str = "Alla") -> list[dict[str, Any]]:
    query = "SELECT * FROM objects WHERE 1 = 1"
    params: list[Any] = []

    if search.strip():
        term = f"%{search.strip()}%"
        query += """
        AND (
            object_id LIKE ?
            OR name LIKE ?
            OR article_number LIKE ?
            OR supplier_article_number LIKE ?
            OR description LIKE ?
            OR search_words LIKE ?
            OR location LIKE ?
            OR storage_location_2 LIKE ?
            OR lift_tray LIKE ?
        )
        """
        params.extend([term, term, term, term, term, term, term, term, term])
    if category != "Alla":
        query += " AND category = ?"
        params.append(category)
    if status != "Alla":
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY category, name"
    return rows(query, tuple(params))


def search_objects(term: str, limit: int = 8) -> list[dict[str, Any]]:
    term = term.strip()
    if not term:
        return []
    like_term = f"%{term}%"
    return rows(
        """
        SELECT *
        FROM objects
        WHERE object_id LIKE ?
           OR name LIKE ?
           OR category LIKE ?
           OR item_type LIKE ?
           OR description LIKE ?
           OR article_number LIKE ?
           OR supplier_article_number LIKE ?
           OR location LIKE ?
           OR storage_location_2 LIKE ?
           OR tornado_id LIKE ?
           OR device LIKE ?
           OR search_words LIKE ?
           OR lift_tray LIKE ?
        ORDER BY
            CASE
                WHEN name LIKE ? THEN 0
                WHEN object_id LIKE ? THEN 1
                ELSE 2
            END,
            name
        LIMIT ?
        """,
        (
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            limit,
        ),
    )


def optional_text(payload: dict[str, Any], key: str) -> str:
    return str(payload.get(key, "") or "").strip()


def add_object(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    item_type = optional_text(payload, "item_type")
    description = optional_text(payload, "description")
    article_number = str(payload.get("article_number", "")).strip()
    supplier_article_number = optional_text(payload, "supplier_article_number")
    location = str(payload.get("location", "")).strip()
    storage_location_2 = optional_text(payload, "storage_location_2")
    tornado_id = str(payload.get("tornado_id", "")).strip()
    door_id = str(payload.get("door_id", "")).strip()
    belongs_to_instrument = optional_text(payload, "belongs_to_instrument")
    device = optional_text(payload, "device")
    belongs_to = optional_text(payload, "belongs_to")
    last_changed = optional_text(payload, "last_changed")
    search_words = optional_text(payload, "search_words")
    tray_for = optional_text(payload, "tray_for")
    lift_tray = optional_text(payload, "lift_tray")
    total_quantity = int(payload.get("total_quantity", 0))
    available_quantity = int(payload.get("available_quantity", total_quantity))
    min_quantity = int(payload.get("min_quantity", 0))
    image_data = str(payload.get("image_data", "")).strip()

    if not object_id:
        raise ValueError("Ange objekt-ID.")
    if not name:
        raise ValueError("Ange namn.")
    if not category:
        raise ValueError("Ange kategori.")
    if not location:
        raise ValueError("Ange plats.")
    if not tornado_id:
        raise ValueError("Ange Tornado/skåp.")
    if not door_id:
        raise ValueError("Ange dörr/fack.")
    if total_quantity < 0 or available_quantity < 0 or min_quantity < 0:
        raise ValueError("Antal får inte vara negativt.")
    if available_quantity > total_quantity:
        raise ValueError("Tillgängligt antal kan inte vara större än totalt antal.")
    if row("SELECT object_id FROM objects WHERE object_id = ?", (object_id,)):
        raise ValueError("Det finns redan ett objekt med det ID:t.")

    status = object_status(available_quantity, min_quantity)
    with connect() as db:
        db.execute(
            """
            INSERT INTO objects (
                object_id, name, category, item_type, description, article_number, supplier_article_number,
                location, storage_location_2, tornado_id, door_id, belongs_to_instrument, device,
                belongs_to, last_changed, search_words, tray_for, lift_tray,
                total_quantity, available_quantity, min_quantity, status, image_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                object_id,
                name,
                category,
                item_type,
                description,
                article_number,
                supplier_article_number,
                location,
                storage_location_2,
                tornado_id,
                door_id,
                belongs_to_instrument,
                device,
                belongs_to,
                last_changed,
                search_words,
                tray_for,
                lift_tray,
                total_quantity,
                available_quantity,
                min_quantity,
                status,
                image_data or None,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt skapat: {name} ({object_id})"),
        )

    return {"object_id": object_id}


def update_object(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    existing = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if existing is None:
        raise ValueError("Objektet hittades inte.")

    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    item_type = optional_text(payload, "item_type")
    description = optional_text(payload, "description")
    article_number = str(payload.get("article_number", "")).strip()
    supplier_article_number = optional_text(payload, "supplier_article_number")
    location = str(payload.get("location", "")).strip()
    storage_location_2 = optional_text(payload, "storage_location_2")
    tornado_id = str(payload.get("tornado_id", "")).strip()
    door_id = str(payload.get("door_id", "")).strip()
    belongs_to_instrument = optional_text(payload, "belongs_to_instrument")
    device = optional_text(payload, "device")
    belongs_to = optional_text(payload, "belongs_to")
    last_changed = optional_text(payload, "last_changed")
    search_words = optional_text(payload, "search_words")
    tray_for = optional_text(payload, "tray_for")
    lift_tray = optional_text(payload, "lift_tray")
    total_quantity = int(payload.get("total_quantity", 0))
    available_quantity = int(payload.get("available_quantity", total_quantity))
    min_quantity = int(payload.get("min_quantity", 0))
    image_data = payload.get("image_data", existing.get("image_data"))
    remove_image = bool(payload.get("remove_image", False))

    if not name:
        raise ValueError("Ange namn.")
    if not category:
        raise ValueError("Ange kategori.")
    if not location:
        raise ValueError("Ange plats.")
    if not tornado_id:
        raise ValueError("Ange Tornado/skåp.")
    if not door_id:
        raise ValueError("Ange dörr/fack.")
    if total_quantity < 0 or available_quantity < 0 or min_quantity < 0:
        raise ValueError("Antal får inte vara negativt.")
    if available_quantity > total_quantity:
        raise ValueError("Tillgängligt antal kan inte vara större än totalt antal.")

    if remove_image:
        image_data = None
    elif isinstance(image_data, str):
        image_data = image_data.strip() or existing.get("image_data")

    status = object_status(available_quantity, min_quantity)
    with connect() as db:
        db.execute(
            """
            UPDATE objects
            SET name = ?,
                category = ?,
                item_type = ?,
                description = ?,
                article_number = ?,
                supplier_article_number = ?,
                location = ?,
                storage_location_2 = ?,
                tornado_id = ?,
                door_id = ?,
                belongs_to_instrument = ?,
                device = ?,
                belongs_to = ?,
                last_changed = ?,
                search_words = ?,
                tray_for = ?,
                lift_tray = ?,
                total_quantity = ?,
                available_quantity = ?,
                min_quantity = ?,
                status = ?,
                image_data = ?
            WHERE object_id = ?
            """,
            (
                name,
                category,
                item_type,
                description,
                article_number,
                supplier_article_number,
                location,
                storage_location_2,
                tornado_id,
                door_id,
                belongs_to_instrument,
                device,
                belongs_to,
                last_changed,
                search_words,
                tray_for,
                lift_tray,
                total_quantity,
                available_quantity,
                min_quantity,
                status,
                image_data,
                object_id,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt uppdaterat: {name} ({object_id})"),
        )

    return {"object_id": object_id}


def delete_object(object_id: str) -> dict[str, Any]:
    object_id = object_id.strip()
    if not object_id:
        raise ValueError("Ange objekt-ID.")

    existing = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if existing is None:
        raise ValueError("Objektet hittades inte.")

    active_loan = row("SELECT loan_id FROM loans WHERE object_id = ? AND status = 'active'", (object_id,))
    if active_loan:
        raise ValueError("Objektet har aktiva lån och kan inte tas bort.")

    with connect() as db:
        db.execute("DELETE FROM loans WHERE object_id = ? AND status != 'active'", (object_id,))
        db.execute("DELETE FROM objects WHERE object_id = ?", (object_id,))
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt borttaget: {existing['name']} ({object_id})"),
        )
    return {"object_id": object_id}


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


def list_active_loans() -> list[dict[str, Any]]:
    loans = rows(
        """
        SELECT l.*, u.name AS user_name, u.department AS user_department, o.name AS object_name, o.tornado_id, o.door_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        WHERE l.status = 'active'
        ORDER BY l.due_time ASC
        """
    )
    current = datetime.now()
    for loan in loans:
        loan["overdue"] = datetime.fromisoformat(loan["due_time"]) < current
    return loans


def recent_events(limit: int = 100) -> list[dict[str, Any]]:
    return rows("SELECT * FROM events ORDER BY event_id DESC LIMIT ?", (limit,))


def list_consumable_reports() -> list[dict[str, Any]]:
    return rows(
        """
        SELECT r.*, o.name AS object_name, o.article_number, o.location, o.tornado_id
        FROM consumable_reports r
        JOIN objects o ON o.object_id = r.object_id
        WHERE r.status = 'open'
        ORDER BY r.created_at DESC
        """
    )


def create_consumable_report(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    quantity_value = payload.get("quantity", "")
    quantity = int(quantity_value) if str(quantity_value).strip() else None
    reported_by = optional_text(payload, "reported_by")
    message = optional_text(payload, "message")

    if not object_id:
        raise ValueError("Ange artikel eller objekt.")
    if quantity is not None and quantity < 0:
        raise ValueError("Antal kan inte vara negativt.")

    object_item = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if object_item is None:
        raise ValueError("Artikeln hittades inte.")

    timestamp = now_text()
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO consumable_reports (
                object_id, quantity, reported_by, message, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """,
            (object_id, quantity, reported_by, message, timestamp, timestamp),
        )
        report_id = int(cursor.lastrowid)
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "consumable", f"Förbrukningsvara rapporterad slut: {object_item['name']} ({object_id})"),
        )
    return {"report_id": report_id}


def close_consumable_report(report_id: int) -> dict[str, Any]:
    if report_id <= 0:
        raise ValueError("Ange rapport-ID.")
    report = row("SELECT * FROM consumable_reports WHERE report_id = ?", (report_id,))
    if report is None:
        raise ValueError("Rapporten hittades inte.")
    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE consumable_reports SET status = 'closed', updated_at = ? WHERE report_id = ?",
            (timestamp, report_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "consumable", f"Förbrukningsrapport {report_id} markerad åtgärdad"),
        )
    return {"report_id": report_id}


REQUEST_STATUSES = ("requested", "prepared", "loaned", "returned", "stocked")


def list_loan_requests() -> list[dict[str, Any]]:
    return rows(
        """
        SELECT r.*, u.name AS user_name, u.department AS user_department,
               o.name AS object_name, o.location AS object_location,
               o.tornado_id AS object_store
        FROM loan_requests r
        JOIN users u ON u.user_id = r.user_id
        JOIN objects o ON o.object_id = r.object_id
        ORDER BY
            CASE r.status
                WHEN 'requested' THEN 1
                WHEN 'prepared' THEN 2
                WHEN 'loaned' THEN 3
                WHEN 'returned' THEN 4
                WHEN 'stocked' THEN 5
                ELSE 6
            END,
            r.updated_at DESC
        """
    )


def create_loan_request(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()
    quantity = int(payload.get("quantity", 1))
    lending_date = str(payload.get("lending_date", "")).strip()
    return_date = str(payload.get("due_time", "") or payload.get("return_date", "")).strip()
    engine_id = optional_text(payload, "engine_id")
    project_number = optional_text(payload, "project_number")
    note = optional_text(payload, "note")

    if not object_id:
        raise ValueError("Ange objekt-ID.")
    if not user_id:
        raise ValueError("Välj användare.")
    if quantity <= 0:
        raise ValueError("Antal måste vara större än 0.")
    if not lending_date:
        raise ValueError("Ange utlåningsdatum.")
    if not return_date:
        raise ValueError("Ange returdatum.")

    object_item = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if object_item is None:
        raise ValueError("Objektet hittades inte.")
    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    timestamp = now_text()
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO loan_requests (
                user_id, object_id, quantity, engine_id, project_number,
                lending_date, return_date, status, created_at, updated_at, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'requested', ?, ?, ?)
            """,
            (user_id, object_id, quantity, engine_id, project_number, lending_date, return_date, timestamp, timestamp, note),
        )
        request_id = int(cursor.lastrowid)
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "request", f"Låneförfrågan skapad: {user['name']} vill låna {quantity} x {object_item['name']} ({object_id})"),
        )
    settings = get_system_settings()
    if settings.get("notify_new_job") == "1":
        try:
            notify_recipients(
                f"Nytt lÃ¥nejobb #{request_id}",
                (
                    f"Ett nytt lÃ¥nejobb har skapats.\n\n"
                    f"AnvÃ¤ndare: {user['name']}\n"
                    f"Objekt: {object_item['name']} ({object_id})\n"
                    f"Antal: {quantity}\n"
                    f"UtlÃ¥ningsdatum: {lending_date}\n"
                    f"Returdatum: {return_date}\n"
                ),
                settings,
            )
        except Exception as error:
            log_event("notification", f"Kunde inte skicka jobbnotis #{request_id}: {error}")
    return {"request_id": request_id}


def update_loan_request_status(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = int(payload.get("request_id", 0))
    status = str(payload.get("status", "")).strip()
    if request_id <= 0:
        raise ValueError("Ange jobb-ID.")
    if status not in REQUEST_STATUSES:
        raise ValueError("Ogiltig jobbstatus.")

    request = row(
        """
        SELECT r.*, u.name AS user_name, o.name AS object_name
        FROM loan_requests r
        JOIN users u ON u.user_id = r.user_id
        JOIN objects o ON o.object_id = r.object_id
        WHERE r.request_id = ?
        """,
        (request_id,),
    )
    if request is None:
        raise ValueError("Jobbet hittades inte.")

    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE loan_requests SET status = ?, updated_at = ? WHERE request_id = ?",
            (status, timestamp, request_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "job", f"Jobb {request_id} ändrades till {status}: {request['object_name']} för {request['user_name']}"),
        )
    return {"request_id": request_id, "status": status}


def checkout(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()
    quantity = int(payload.get("quantity", 1))
    lending_date = str(payload.get("lending_date", "")).strip()
    due_time = str(payload.get("due_time", "")).strip()
    engine_id = optional_text(payload, "engine_id")
    project_number = optional_text(payload, "project_number")

    if not object_id:
        raise ValueError("Ange objekt-ID.")
    if not user_id:
        raise ValueError("Välj användare.")
    if quantity <= 0:
        raise ValueError("Antal måste vara större än 0.")
    if not lending_date:
        raise ValueError("Ange utlåningsdatum.")
    if not due_time:
        raise ValueError("Ange returdatum.")

    object_item = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if object_item is None:
        raise ValueError("Objektet hittades inte.")
    if object_item["available_quantity"] < quantity:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt.")

    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    checkout_time = f"{lending_date} 08:00:00" if len(lending_date) == 10 else lending_date
    due_value = f"{due_time} 16:00:00" if len(due_time) == 10 else due_time

    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO loans (
                user_id, object_id, quantity, checkout_time, due_time,
                engine_id, project_number, return_time, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'active')
            """,
            (user_id, object_id, quantity, checkout_time, due_value, engine_id, project_number),
        )
        loan_id = int(cursor.lastrowid)
        available = object_item["available_quantity"] - quantity
        db.execute(
            "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
            (available, object_status(available, object_item["min_quantity"]), object_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (checkout_time, "loan", f"{user['name']} lånade {quantity} x {object_item['name']} ({object_id})"),
        )

    open_door(object_item["tornado_id"], object_item["door_id"], "checkout")
    return {"loan_id": loan_id}


def issue_item(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    user_id = str(payload.get("user_id", "")).strip()
    quantity = int(payload.get("quantity", 1))

    if not object_id:
        raise ValueError("Ange objekt-ID.")
    if not user_id:
        raise ValueError("Välj användare.")
    if quantity <= 0:
        raise ValueError("Antal måste vara större än 0.")

    object_item = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if object_item is None:
        raise ValueError("Objektet hittades inte.")
    if object_item["available_quantity"] < quantity:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt.")

    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    issued_at = now_text()
    available = object_item["available_quantity"] - quantity
    with connect() as db:
        db.execute(
            "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
            (available, object_status(available, object_item["min_quantity"]), object_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (issued_at, "issue", f"{user['name']} checkade ut {quantity} x {object_item['name']} ({object_id}) utan retur"),
        )

    open_door(object_item["tornado_id"], object_item["door_id"], "issue")
    return {"object_id": object_id}


def return_item(payload: dict[str, Any]) -> dict[str, Any]:
    identifier = str(payload.get("identifier", "")).strip()
    if not identifier:
        raise ValueError("Ange objekt-ID eller lån-ID.")

    if identifier.isdigit():
        active_loan = row(_active_loan_query("l.loan_id = ?"), (int(identifier),))
    else:
        active_loan = row(_active_loan_query("l.object_id = ?"), (identifier,))

    if active_loan is None:
        raise ValueError("Inget aktivt lån hittades.")

    returned_at = now_text()
    with connect() as db:
        object_item = db.execute("SELECT * FROM objects WHERE object_id = ?", (active_loan["object_id"],)).fetchone()
        available = object_item["available_quantity"] + active_loan["quantity"]
        db.execute(
            "UPDATE loans SET return_time = ?, status = 'returned' WHERE loan_id = ?",
            (returned_at, active_loan["loan_id"]),
        )
        db.execute(
            "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
            (available, object_status(available, object_item["min_quantity"]), active_loan["object_id"]),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (
                returned_at,
                "return",
                f"{active_loan['user_name']} lämnade tillbaka {active_loan['quantity']} x {active_loan['object_name']} ({active_loan['object_id']})",
            ),
        )

    open_door(active_loan["tornado_id"], active_loan["door_id"], "return")
    return {"loan_id": active_loan["loan_id"]}


def _active_loan_query(condition: str) -> str:
    return f"""
        SELECT l.*, u.name AS user_name, u.department AS user_department, o.name AS object_name, o.tornado_id, o.door_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        WHERE l.status = 'active' AND {condition}
        ORDER BY l.checkout_time ASC
    """
