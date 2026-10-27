from __future__ import annotations

import smtplib
import ssl
from email.message import EmailMessage


def send_email_message(subject: str, body: str, recipients: list[str], settings: dict[str, str]) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings["smtp_from_address"]
    message["To"] = ", ".join(recipients)
    message.set_content(body)
    with smtplib.SMTP(settings["smtp_host"], int(settings["smtp_port"]), timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        if settings.get("smtp_username"):
            smtp.login(settings["smtp_username"], settings.get("smtp_password", ""))
        smtp.send_message(message)


def send_raw_smtp_message(
    server: str,
    port: int,
    mail_from: str,
    rcpt_to: str,
    subject: str,
    body: str,
    ehlo_name: str,
) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = mail_from
    message["To"] = rcpt_to
    message.set_content(body)
    with smtplib.SMTP(server, port, timeout=10) as smtp:
        smtp.ehlo(ehlo_name)
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo(ehlo_name)
        smtp.send_message(message)