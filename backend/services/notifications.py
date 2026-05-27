from __future__ import annotations

import re
import smtplib
import ssl
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

from backend.database import connect, rows


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log_event(event_type: str, message: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), event_type, message),
        )


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
    "notification_recipients_new_job": "",
    "notification_recipients_returned_loan": "",
    "notification_recipients_low_stock": "",
    "notification_recipients_empty_stock": "",
    "notify_new_job": "1",
    "notify_returned_loan": "1",
    "notify_low_stock": "1",
    "notify_empty_stock": "1",
    "notify_loan_reminders": "1",
    "notify_due_soon": "1",
    "loan_reminder_days": "1",
    "due_soon_days": "10",
    "notify_overdue": "1",
    "notify_overdue_repeat": "1",
    "overdue_repeat_days": "3",
    "overdue_block_enabled": "1",
    "overdue_block_limit": "3",
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

    for number_key in ("loan_reminder_days", "due_soon_days", "overdue_repeat_days", "overdue_block_limit"):
        if settings[number_key] and not settings[number_key].isdigit():
            raise ValueError("Inställningar för dagar och lånespärr måste vara tal.")

    if int(settings["overdue_block_limit"] or "0") <= 0:
        raise ValueError("Gränsen för sena lån måste vara minst 1.")

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
        raise ValueError("SMTP är inte komplett konfigurerat.")

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


def notify_rule_recipients(rule_key: str, subject: str, body: str, settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    recipients = parse_email_list(settings.get(rule_key, ""))
    if not recipients:
        recipients = parse_email_list(settings.get("notification_recipients", ""))
    if not recipients or not smtp_ready(settings):
        return 0
    return send_email(subject, body, recipients, settings)


def send_loan_reminders() -> dict[str, int]:
    settings = get_system_settings()
    due_soon_enabled = settings.get("notify_due_soon", settings.get("notify_loan_reminders")) == "1"
    overdue_enabled = settings.get("notify_overdue") == "1" or settings.get("notify_overdue_repeat") == "1"
    if not due_soon_enabled and not overdue_enabled:
        raise ValueError("Lånepåminnelser är inte aktiva.")
    if not smtp_ready(settings):
        raise ValueError("SMTP är inte komplett konfigurerat.")

    reminder_days = int(settings.get("due_soon_days") or settings.get("loan_reminder_days") or "10")
    latest_due = datetime.now() + timedelta(days=reminder_days)
    due_cutoff = latest_due if due_soon_enabled else datetime.now()
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
        (due_cutoff.strftime("%Y-%m-%d %H:%M:%S"),),
    )

    sent = 0
    now = datetime.now()
    for loan in candidates:
        due_date = datetime.fromisoformat((loan["due_time"] or "").replace(" ", "T"))
        is_overdue = due_date < now
        if is_overdue and not overdue_enabled:
            continue
        if not is_overdue and not due_soon_enabled:
            continue
        due_time = (loan["due_time"] or "")[:16]
        subject = (
            f"Sen inlämning: {loan['object_name']}"
            if is_overdue
            else f"Påminnelse: {loan['object_name']} ska lämnas tillbaka"
        )
        body = (
            f"Hej {loan['user_name']},\n\n"
            f"Det här är en påminnelse om att {loan['quantity']} x {loan['object_name']} "
            f"({loan['object_id']}) ska lämnas tillbaka senast {due_time}.\n\n"
            "Tack!"
        )
        sent += send_email(subject, body, [loan["user_email"]], settings)

    log_event("notification", f"Lånepåminnelser skickade: {sent}")
    return {"matched": len(candidates), "sent": sent}
