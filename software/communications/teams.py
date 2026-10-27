from __future__ import annotations

from software.communications.smtp import send_raw_smtp_message


def send_team_message(
    *,
    server: str,
    port: int,
    mail_from: str,
    group_recipient: str,
    subject_prefix: str,
    subject: str,
    recipient_tag: str,
    body: str,
    ehlo_name: str,
) -> None:
    formatted_subject = f"{subject_prefix} {subject} {recipient_tag}".strip()
    send_raw_smtp_message(
        server, port, mail_from, group_recipient, formatted_subject, body, ehlo_name,
    )