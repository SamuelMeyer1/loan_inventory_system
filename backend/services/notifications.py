from __future__ import annotations

import re
import os
from datetime import datetime, timedelta
from typing import Any

from backend.database import connect, row, rows
from software.communications.smtp import send_email_message, send_raw_smtp_message
from software.communications.teams import send_team_message


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
    "smtp_host": "mailgot.it.volvo.com",
    "smtp_port": "25",
    "smtp_username": "",
    "smtp_password": "",
    "smtp_from_address": "",
    "smtp_use_tls": "1",
    "teams_enabled": "0",
    "teams_group_recipient": "group.id.a474985@volvo.com",
    "teams_subject_prefix": "TEAMS",
    "teams_ehlo_name": "mailgot.ut.volvo.com",
    "notification_simulation_enabled": "1",
    "notification_simulation_recipient": "",
    "notification_recipients": "",
    "notification_recipients_new_job": "",
    "notification_recipients_returned_loan": "",
    "notification_recipients_low_stock": "",
    "notification_recipients_empty_stock": "",
    "notify_new_job": "1",
    "notify_pickup_ready": "1",
    "notify_returned_loan": "1",
    "notify_low_stock": "1",
    "notify_empty_stock": "1",
    "notify_loan_reminders": "1",
    "notify_due_soon": "1",
    "loan_reminder_days": "1",
    "due_soon_days": "10",
    "max_loan_days": "90",
    "notify_overdue": "1",
    "notify_overdue_repeat": "1",
    "overdue_repeat_days": "3",
    "overdue_block_enabled": "1",
    "overdue_block_limit": "3",
    "inactive_user_warning_enabled": "1",
    "inactive_user_days": "365",
    "notify_admin_new_request": "1",
    "notify_admin_loaned": "0",
    "message_new_job_subject": "Nytt lånejobb #{request_id}",
    "message_new_job_body": (
        "NY LÅNEFÖRFRÅGAN\n\n"
        "Förfrågan: #{request_id}\n"
        "Användare: {user_name}\n"
        "Utlåningsdatum: {lending_date}\n"
        "Återlämningsdatum: {return_date}\n\n"
        "ARTIKLAR ({article_count})\n"
        "{object_list}\n\n"
        "Totalt antal: {quantity}"
    ),
    "message_returned_loan_subject": "Lån återlämnat #{request_id}",
    "message_returned_loan_body": (
        "Ett lån har markerats som återlämnat.\n\n"
        "Användare: {user_name}\n"
        "Objekt: {object_name} ({object_id})\n"
        "Antal: {quantity}\n"
    ),
    "message_pickup_ready_subject": "Din artikel är klar att hämta",
    "message_pickup_ready_body": (
        "Hej {user_name},\n\n"
        "{quantity} x {object_name} ({object_id}) är nu klar att hämta.\n\n"
        "Utlåningsdatum: {lending_date}\n"
        "Returdatum: {return_date}\n\n"
        "Tack!"
    ),
    "message_stock_alert_subject": "Lagerlarm: {object_name}",
    "message_stock_alert_body": (
        "{object_name} ({object_id}) har {level}.\n\n"
        "Saldo efter utlåning: {available}\n"
        "Beställningspunkt: {min_quantity}\n"
    ),
    "message_loan_reminder_subject": "Påminnelse: {object_name} ska lämnas tillbaka",
    "message_loan_overdue_subject": "Sen inlämning: {object_name}",
    "message_loan_reminder_body": (
        "Hej {user_name},\n\n"
        "Det här är en påminnelse om att {quantity} x {object_name} "
        "({object_id}) ska lämnas tillbaka senast {due_time}.\n\n"
        "Tack!"
    ),
}

ADMIN_RULE_KEYS = {
    "inactive_user_warning_enabled", "inactive_user_days",
    "notify_admin_new_request", "notify_admin_loaned",
}
ADMIN_NOTIFICATION_SETTINGS = {"request": "notify_admin_new_request", "loan": "notify_admin_loaned"}


def get_system_settings() -> dict[str, str]:
    settings = SYSTEM_SETTING_DEFAULTS.copy()
    for item in rows("SELECT key, value FROM system_settings"):
        settings[item["key"]] = item["value"]
    if "LOAN_SMTP_PASSWORD" in os.environ:
        settings["smtp_password"] = os.environ["LOAN_SMTP_PASSWORD"]
    return settings


def get_public_system_settings(settings: dict[str, str] | None = None) -> dict[str, str | bool]:
    if settings is None:
        settings = get_system_settings()
    public_settings: dict[str, str | bool] = {
        key: value for key, value in settings.items() if key != "smtp_password"
    }
    public_settings["smtp_password_configured"] = bool(settings.get("smtp_password", "").strip())
    return public_settings


def update_system_settings(payload: dict[str, Any]) -> dict[str, str | bool]:
    settings = get_system_settings()
    for key in SYSTEM_SETTING_DEFAULTS:
        value = payload.get(key, settings[key])
        if key in ADMIN_RULE_KEYS - {"inactive_user_days"} and value not in (
            True, False, "1", "0", "true", "false", "yes", "no", "on", "off"
        ):
            raise ValueError("Välj på eller av för inaktivitetsvarning och Adminnotiser.")
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

    for number_key in ("loan_reminder_days", "due_soon_days", "max_loan_days", "overdue_repeat_days", "overdue_block_limit"):
        if settings[number_key] and not settings[number_key].isdigit():
            raise ValueError("Inställningar för dagar och lånespärr måste vara tal.")

    if int(settings["overdue_block_limit"] or "0") <= 0:
        raise ValueError("Gränsen för sena lån måste vara minst 1.")
    if int(settings["max_loan_days"] or "0") <= 0:
        raise ValueError("Max lånetid måste vara minst 1 dag.")
    days = settings["inactive_user_days"]
    if not days.isascii() or not days.isdigit() or not 1 <= int(days) <= 36500:
        raise ValueError("Inaktivitetsgränsen måste vara ett heltal mellan 1 och 36500 dagar.")
    # Internal rules do not require configuring an external email transport.
    internal_rules_only = bool(payload) and set(payload) <= ADMIN_RULE_KEYS
    if not internal_rules_only and simulation_enabled(settings) and not simulation_recipient(settings):
        raise ValueError("Ange testmottagare eller stäng av simuleringsläge.")

    timestamp = now_text()
    with connect() as db:
        for key, value in settings.items():
            if key == "smtp_password" and "LOAN_SMTP_PASSWORD" in os.environ:
                continue
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
    return get_public_system_settings(settings)

def list_admin_notifications() -> dict[str, Any]:
    settings = get_system_settings()
    event_types = [kind for kind, key in ADMIN_NOTIFICATION_SETTINGS.items() if settings[key] == "1"]
    if not event_types:
        return {"items": [], "unread_count": 0, "latest_event_id": 0}
    placeholders = ",".join("?" for _ in event_types)
    with connect() as db:
        db.execute("BEGIN")
        items = [dict(item) for item in db.execute(
            f"""SELECT e.event_id, e.event_time, e.event_type,
                       e.event_id > COALESCE(r.last_event_id, 0) AS unread
                FROM events e LEFT JOIN admin_notification_shared_reads r
                    ON r.event_type = e.event_type
                WHERE e.event_type IN ({placeholders}) ORDER BY e.event_id DESC LIMIT 20""",
            event_types,
        )]
        unread = db.execute(
            f"""SELECT COUNT(*) FROM events e LEFT JOIN admin_notification_shared_reads r
                    ON r.event_type = e.event_type
                WHERE e.event_id > COALESCE(r.last_event_id, 0) AND e.event_type IN ({placeholders})""",
            event_types,
        ).fetchone()[0]
    return {"items": items, "unread_count": unread,
            "latest_event_id": items[0]["event_id"] if items else 0}


def mark_admin_notifications_read(payload: dict[str, Any]) -> dict[str, int]:
    try:
        event_id = int(str(payload.get("up_to_event_id", "")))
    except (ValueError, TypeError) as error:
        raise ValueError("Ange ett giltigt notis-ID.") from error
    settings = get_system_settings()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        maximum = db.execute("SELECT COALESCE(MAX(event_id), 0) FROM events").fetchone()[0]
        if event_id < 0 or event_id > maximum:
            raise ValueError("Notis-ID ligger utanför tillgänglig historik.")
        for kind, key in ADMIN_NOTIFICATION_SETTINGS.items():
            if settings[key] == "1":
                db.execute("""
                    INSERT INTO admin_notification_shared_reads (event_type, last_event_id) VALUES (?, ?)
                    ON CONFLICT(event_type) DO UPDATE
                    SET last_event_id = MAX(last_event_id, excluded.last_event_id)
                """, (kind, event_id))
    return {"up_to_event_id": event_id}


def parse_email_list(value: str) -> list[str]:
    return [email.strip() for email in re.split(r"[,;\n]+", value or "") if email.strip()]


class SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def message_text(settings: dict[str, str], key: str, values: dict[str, Any]) -> str:
    template = settings.get(key) or SYSTEM_SETTING_DEFAULTS.get(key, key)
    return template.format_map(SafeFormatDict({name: "" if value is None else value for name, value in values.items()}))


def simulation_recipient(settings: dict[str, str]) -> str:
    return str(settings.get("notification_simulation_recipient", "")).strip()


def simulation_enabled(settings: dict[str, str]) -> bool:
    return settings.get("notification_simulation_enabled") == "1"


def effective_recipients(recipients: list[str], settings: dict[str, str]) -> list[str]:
    recipients = [recipient for recipient in recipients if recipient]
    if not simulation_enabled(settings):
        return recipients
    recipient = simulation_recipient(settings)
    if not recipient:
        raise ValueError("Simuleringsläge är aktivt men testmottagare saknas.")
    return [recipient]


def smtp_ready(settings: dict[str, str]) -> bool:
    return (
        settings.get("smtp_enabled") == "1"
        and bool(settings.get("smtp_host"))
        and bool(settings.get("smtp_port"))
        and bool(settings.get("smtp_from_address"))
    )


def teams_ready(settings: dict[str, str]) -> bool:
    return (
        settings.get("teams_enabled") == "1"
        and bool(settings.get("smtp_host"))
        and bool(settings.get("smtp_port"))
        and bool(settings.get("smtp_from_address"))
        and bool(settings.get("teams_group_recipient"))
    )


def email_msg(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    if os.environ.get("LOAN_SIMULATION") == "1":
        raise ValueError("Simuleringsmiljön tillåter inga externa utskick.")
    if os.environ.get("LOAN_ENABLE_NOTIFICATIONS") != "1":
        raise ValueError("Externa notiser är spärrade. IT-godkänd konfiguration krävs innan LOAN_ENABLE_NOTIFICATIONS=1 sätts.")
    settings = settings or get_system_settings()
    original_recipients = [recipient for recipient in recipients if recipient]
    recipients = effective_recipients(original_recipients, settings)
    if not recipients:
        return 0
    if not smtp_ready(settings):
        raise ValueError("SMTP är inte komplett konfigurerat.")
    if settings.get("smtp_use_tls") != "1":
        raise ValueError("TLS krävs för e-posttransport.")

    if simulation_enabled(settings):
        subject = f"[SIMULERING] {subject}"
        body = (
            "SIMULERINGSLÄGE ÄR AKTIVT.\n"
            f"Ursprungliga mottagare: {', '.join(original_recipients) or '-'}\n\n"
            f"{body}"
        )

    send_email_message(subject, body, recipients, settings)
    return len(recipients)


def send_email(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    return email_msg(subject, body, recipients, settings)


def raw_smtp_message(server: str, port: int, mail_from: str, rcpt_to: str, subject: str, body: str, ehlo_name: str) -> None:
    if os.environ.get("LOAN_SIMULATION") == "1":
        raise ValueError("Simuleringsmiljön tillåter inga externa utskick.")
    if os.environ.get("LOAN_ENABLE_NOTIFICATIONS") != "1":
        raise ValueError("Externa notiser är spärrade.")
    send_raw_smtp_message(server, port, mail_from, rcpt_to, subject, body, ehlo_name)


def team_msg(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    if os.environ.get("LOAN_SIMULATION") == "1":
        raise ValueError("Simuleringsmiljön tillåter inga externa utskick.")
    if os.environ.get("LOAN_ENABLE_NOTIFICATIONS") != "1":
        raise ValueError("Externa notiser är spärrade. IT-godkänd konfiguration krävs innan LOAN_ENABLE_NOTIFICATIONS=1 sätts.")
    settings = settings or get_system_settings()
    original_recipients = [recipient for recipient in recipients if recipient]
    recipients = effective_recipients(original_recipients, settings)
    if not recipients:
        return 0

    is_simulation = simulation_enabled(settings)
    mode = "SIMULERING" if is_simulation else "TEAMS"
    if not teams_ready(settings):
        raise ValueError("Teams är inte komplett konfigurerat.")

    sent = 0
    group_recipient = settings["teams_group_recipient"].strip()
    prefix = (settings.get("teams_subject_prefix") or "TEAMS").strip()
    for recipient in recipients:
        send_team_message(
            server=settings["smtp_host"],
            port=int(settings["smtp_port"]),
            mail_from=settings["smtp_from_address"],
            group_recipient=group_recipient,
            subject_prefix=prefix,
            subject=subject,
            recipient_tag=recipient,
            body=body,
            ehlo_name=settings.get("teams_ehlo_name") or "mailgot.ut.volvo.com",
        )
        sent += 1

    log_event("teams", f"{mode} Teams-meddelande: {subject} -> {', '.join(recipients)}")
    return sent


def send_teams_message(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    return team_msg(subject, body, recipients, settings)


def send_teams_test_message() -> dict[str, Any]:
    settings = get_system_settings()
    recipients = [simulation_recipient(settings)] if simulation_recipient(settings) else ["teams-test"]
    sent = send_teams_message(
        "Test från Loan Inventory System",
        "Det här är ett testmeddelande från Teams-integrationen.",
        recipients,
        settings,
    )
    return {"sent": sent, "simulation": simulation_enabled(settings)}


def notify_recipients(subject: str, body: str, settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    recipients = parse_email_list(settings.get("notification_recipients", ""))
    if not recipients:
        return 0
    return send_teams_message(subject, body, recipients, settings)


def notify_rule_recipients(rule_key: str, subject: str, body: str, settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    recipients = parse_email_list(settings.get(rule_key, ""))
    if not recipients:
        return 0
    return send_teams_message(subject, body, recipients, settings)


def send_loan_reminders() -> dict[str, int]:
    settings = get_system_settings()
    due_soon_enabled = settings.get("notify_due_soon", settings.get("notify_loan_reminders")) == "1"
    overdue_enabled = settings.get("notify_overdue") == "1" or settings.get("notify_overdue_repeat") == "1"
    if not due_soon_enabled and not overdue_enabled:
        raise ValueError("Lånepåminnelser är inte aktiva.")
    if not smtp_ready(settings):
        raise ValueError("SMTP är inte komplett konfigurerat.")
    if settings.get("smtp_use_tls") != "1":
        raise ValueError("TLS krävs för e-posttransport.")

    reminder_days = int(settings.get("due_soon_days") or settings.get("loan_reminder_days") or "10")
    repeat_days = max(1, int(settings.get("overdue_repeat_days") or "3"))
    repeat_cutoff = datetime.now() - timedelta(days=repeat_days)
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
    matched = 0
    skipped_recent = 0
    now = datetime.now()
    for loan in candidates:
        due_date = datetime.fromisoformat((loan["due_time"] or "").replace(" ", "T"))
        is_overdue = due_date < now
        if is_overdue and not overdue_enabled:
            continue
        if not is_overdue and not due_soon_enabled:
            continue
        last_sent_text = str(loan["last_reminder_sent_at"] or "").strip()
        if last_sent_text:
            try:
                last_sent = datetime.fromisoformat(last_sent_text.replace(" ", "T"))
                if not is_overdue or settings.get("notify_overdue_repeat") != "1" or last_sent > repeat_cutoff:
                    skipped_recent += 1
                    continue
            except ValueError:
                pass
        matched += 1
        due_time = (loan["due_time"] or "")[:16]
        message_values = {
            "loan_id": loan["loan_id"],
            "user_name": loan["user_name"],
            "object_name": loan["object_name"],
            "object_id": loan["object_id"],
            "quantity": loan["quantity"] - loan["returned_quantity"],
            "due_time": due_time,
        }
        subject_key = "message_loan_overdue_subject" if is_overdue else "message_loan_reminder_subject"
        subject = message_text(settings, subject_key, message_values)
        body = message_text(settings, "message_loan_reminder_body", message_values)
        sent += send_email(subject, body, [loan["user_email"]], settings)
        with connect() as db:
            db.execute(
                "UPDATE loans SET last_reminder_sent_at = ? WHERE loan_id = ?",
                (now_text(), loan["loan_id"]),
            )

    log_event("notification", f"Lånepåminnelser skickade: {sent}, nyligen påminda hoppades över: {skipped_recent}")
    return {"matched": matched, "sent": sent, "skipped_recent": skipped_recent}


def send_loan_reminder(loan_id: int) -> dict[str, Any]:
    if loan_id <= 0:
        raise ValueError("Ange lån-ID.")

    settings = get_system_settings()
    if not smtp_ready(settings):
        raise ValueError("SMTP är inte komplett konfigurerat.")
    if settings.get("smtp_use_tls") != "1":
        raise ValueError("TLS krävs för e-posttransport.")

    loan = row(
        """
        SELECT l.*, u.name AS user_name, u.email AS user_email,
               o.name AS object_name, o.object_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        WHERE l.loan_id = ?
          AND l.status = 'active'
        """,
        (loan_id,),
    )
    if loan is None:
        raise ValueError("Aktivt lån hittades inte.")
    if not str(loan["user_email"] or "").strip():
        raise ValueError("Låntagaren saknar e-postadress.")

    due_date = datetime.fromisoformat((loan["due_time"] or "").replace(" ", "T"))
    is_overdue = due_date < datetime.now()
    due_time = (loan["due_time"] or "")[:16]
    message_values = {
        "loan_id": loan["loan_id"],
        "user_name": loan["user_name"],
        "object_name": loan["object_name"],
        "object_id": loan["object_id"],
        "quantity": loan["quantity"] - loan["returned_quantity"],
        "due_time": due_time,
    }
    subject_key = "message_loan_overdue_subject" if is_overdue else "message_loan_reminder_subject"
    subject = message_text(settings, subject_key, message_values)
    body = message_text(settings, "message_loan_reminder_body", message_values)
    sent = send_email(subject, body, [loan["user_email"]], settings)
    timestamp = now_text()
    with connect() as db:
        db.execute(
            "UPDATE loans SET last_reminder_sent_at = ? WHERE loan_id = ?",
            (timestamp, loan_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (
                timestamp,
                "notification",
                f"Manuell lånepåminnelse skickad till {loan['user_name']} för {loan['object_name']} ({loan['object_id']})",
            ),
        )
    return {"loan_id": loan_id, "sent": sent, "last_reminder_sent_at": timestamp}
