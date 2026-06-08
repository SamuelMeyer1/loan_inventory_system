from __future__ import annotations

import re
import smtplib
import ssl
import socket
import time
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Any

from backend.database import connect, row, rows


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
    "smtp_use_tls": "0",
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
    "message_new_job_subject": "Nytt lånejobb #{request_id}",
    "message_new_job_body": (
        "Ett nytt lånejobb har skapats.\n\n"
        "Användare: {user_name}\n"
        "Objekt: {object_name} ({object_id})\n"
        "Antal: {quantity}\n"
        "Utlåningsdatum: {lending_date}\n"
        "Returdatum: {return_date}\n"
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

    for number_key in ("loan_reminder_days", "due_soon_days", "max_loan_days", "overdue_repeat_days", "overdue_block_limit"):
        if settings[number_key] and not settings[number_key].isdigit():
            raise ValueError("Inställningar för dagar och lånespärr måste vara tal.")

    if int(settings["overdue_block_limit"] or "0") <= 0:
        raise ValueError("Gränsen för sena lån måste vara minst 1.")
    if int(settings["max_loan_days"] or "0") <= 0:
        raise ValueError("Max lånetid måste vara minst 1 dag.")
    if simulation_enabled(settings) and not simulation_recipient(settings):
        raise ValueError("Ange testmottagare eller stäng av simuleringsläge.")

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
    settings = settings or get_system_settings()
    original_recipients = [recipient for recipient in recipients if recipient]
    recipients = effective_recipients(original_recipients, settings)
    if not recipients:
        return 0
    if not smtp_ready(settings):
        raise ValueError("SMTP är inte komplett konfigurerat.")

    if simulation_enabled(settings):
        subject = f"[SIMULERING] {subject}"
        body = (
            "SIMULERINGSLÄGE ÄR AKTIVT.\n"
            f"Ursprungliga mottagare: {', '.join(original_recipients) or '-'}\n\n"
            f"{body}"
        )

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


def send_email(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    return email_msg(subject, body, recipients, settings)


def raw_smtp_message(server: str, port: int, mail_from: str, rcpt_to: str, subject: str, body: str, ehlo_name: str) -> None:
    with socket.create_connection((server, port), timeout=10) as connection:
        reader = connection.makefile("rb")

        def read_response(expected_codes: tuple[int, ...], command_name: str) -> None:
            lines: list[str] = []
            while True:
                line = reader.readline()
                if not line:
                    raise ValueError(f"SMTP-servern stängde anslutningen vid {command_name}.")
                text = line.decode("utf-8", errors="replace").rstrip("\r\n")
                lines.append(text)
                if len(text) < 4 or text[3:4] != "-":
                    break
            code_text = lines[-1][:3]
            code = int(code_text) if code_text.isdigit() else 0
            if code not in expected_codes:
                raise ValueError(f"SMTP {command_name} misslyckades: {' | '.join(lines)}")

        def send(command: str, expected_codes: tuple[int, ...] | None = None, command_name: str | None = None) -> None:
            print(">>", command)
            connection.sendall((command + "\r\n").encode("utf-8"))
            time.sleep(0.5)
            if expected_codes is not None:
                read_response(expected_codes, command_name or command.split(" ", 1)[0])

        read_response((220,), "anslutning")
        send(f"EHLO {ehlo_name}", (250,), "EHLO")
        send(f"MAIL FROM: <{mail_from}>", (250,), "MAIL FROM")
        send(f"RCPT TO: <{rcpt_to}>", (250, 251), "RCPT TO")
        send("DATA", (354,), "DATA")
        send("Content-Type: text/plain; charset=UTF-8")
        send("Content-Transfer-Encoding: 8bit")
        send(f"Subject: {subject}")
        send("")
        for line in body.splitlines():
            send(f".{line}" if line == "." else line)
        send(".", (250,), "DATA avslut")
        send("QUIT", (221,), "QUIT")


def team_msg(subject: str, body: str, recipients: list[str], settings: dict[str, str] | None = None) -> int:
    settings = settings or get_system_settings()
    original_recipients = [recipient for recipient in recipients if recipient]
    recipients = effective_recipients(original_recipients, settings)
    if not recipients:
        return 0

    timestamp = now_text()
    is_simulation = simulation_enabled(settings)
    mode = "SIMULERING" if is_simulation else "TEAMS"
    print("=" * 72)
    print(f"{mode} TEAMS {timestamp}")
    print(f"Ursprungliga mottagare: {', '.join(original_recipients) or '-'}")
    print(f"Skickas/visas för: {', '.join(recipients)}")
    print(f"Rubrik: {subject}")
    print(body)
    print("=" * 72)

    if not teams_ready(settings):
        raise ValueError("Teams är inte komplett konfigurerat.")

    sent = 0
    group_recipient = settings["teams_group_recipient"].strip()
    prefix = (settings.get("teams_subject_prefix") or "TEAMS").strip()
    for recipient in recipients:
        raw_smtp_message(
            settings["smtp_host"],
            int(settings["smtp_port"]),
            settings["smtp_from_address"],
            group_recipient,
            f"{prefix} {subject} {recipient}".strip(),
            body,
            settings.get("teams_ehlo_name") or "mailgot.ut.volvo.com",
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
            "quantity": loan["quantity"],
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
        "quantity": loan["quantity"],
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
