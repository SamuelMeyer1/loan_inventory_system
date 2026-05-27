from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.database import connect, row, rows
from backend.services.notifications import get_system_settings, notify_rule_recipients
from backend.services.common import (
    is_consumable_object,
    log_event,
    now_text,
    object_status,
    open_door,
    optional_text,
)


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
    quantity = 0

    if not object_id:
        raise ValueError("Ange artikel eller objekt.")

    object_item = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if object_item is None:
        raise ValueError("Artikeln hittades inte.")
    if not is_consumable_object(dict(object_item)):
        raise ValueError("Välj en artikel som är markerad som förbrukningsvara.")

    timestamp = now_text()
    with connect() as db:
        cursor = db.execute(
            """
            INSERT INTO consumable_reports (
                object_id, quantity, reported_by, message, status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, 'open', ?, ?)
            """,
            (object_id, quantity, None, None, timestamp, timestamp),
        )
        report_id = int(cursor.lastrowid)
        db.execute(
            "UPDATE objects SET available_quantity = 0, status = ? WHERE object_id = ?",
            (object_status(0, int(object_item["min_quantity"] or 0)), object_id),
        )
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


def overdue_loan_count(user_id: str, db=None) -> int:
    query = """
        SELECT COUNT(*) AS overdue_count
        FROM loans
        WHERE user_id = ?
          AND status = 'active'
          AND due_time < ?
    """
    params = (user_id, now_text())
    if db is not None:
        result = db.execute(query, params).fetchone()
        return int(result["overdue_count"] or 0)

    result = row(query, params)
    return int(result["overdue_count"] or 0) if result else 0


def ensure_user_can_borrow(user_id: str, user_name: str = "", db=None) -> None:
    settings = get_system_settings()
    if settings.get("overdue_block_enabled") != "1":
        return

    try:
        limit = int(settings.get("overdue_block_limit") or "3")
    except ValueError:
        limit = 3
    limit = max(1, limit)

    overdue_count = overdue_loan_count(user_id, db)
    if overdue_count < limit:
        return

    borrower = user_name or "Användaren"
    raise ValueError(
        f"{borrower} är spärrad för nya lån eftersom {overdue_count} aktiva lån är sena. "
        f"Gränsen är {limit}. Lämna tillbaka sena lån eller ändra spärrgränsen i Admin."
    )


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
    if is_consumable_object(dict(object_item)):
        raise ValueError("Förbrukningsvaror kan inte lånas. Använd sidan Anmäl slut på lager.")
    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    ensure_user_can_borrow(user_id, user["name"])

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
            notify_rule_recipients(
                "notification_recipients_new_job",
                f"Nytt lånejobb #{request_id}",
                (
                    f"Ett nytt lånejobb har skapats.\n\n"
                    f"Användare: {user['name']}\n"
                    f"Objekt: {object_item['name']} ({object_id})\n"
                    f"Antal: {quantity}\n"
                    f"Utlåningsdatum: {lending_date}\n"
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
        SELECT r.*, u.name AS user_name, u.email AS user_email, o.name AS object_name,
               o.available_quantity, o.min_quantity, o.tornado_id, o.door_id
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
        if status == "loaned":
            ensure_loan_for_request(db, request, timestamp)
        elif status == "returned":
            return_linked_loan_for_request(db, request, timestamp)

        db.execute(
            "UPDATE loan_requests SET status = ?, updated_at = ? WHERE request_id = ?",
            (status, timestamp, request_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "job", f"Jobb {request_id} ändrades till {status}: {request['object_name']} för {request['user_name']}"),
        )
    settings = get_system_settings()
    if status == "returned" and settings.get("notify_returned_loan") == "1":
        try:
            notify_rule_recipients(
                "notification_recipients_returned_loan",
                f"Lån återlämnat #{request_id}",
                (
                    "Ett lån har markerats som återlämnat.\n\n"
                    f"Användare: {request['user_name']}\n"
                    f"Objekt: {request['object_name']} ({request['object_id']})\n"
                    f"Antal: {request['quantity']}\n"
                ),
                settings,
            )
        except Exception as error:
            log_event("notification", f"Kunde inte skicka återlämningsnotis #{request_id}: {error}")
    if status == "loaned":
        quantity = int(request["quantity"])
        available = int(request["available_quantity"]) - quantity
        min_quantity = int(request["min_quantity"] or 0)
        should_notify_empty = available <= 0 and settings.get("notify_empty_stock") == "1"
        should_notify_low = 0 < available <= min_quantity and settings.get("notify_low_stock") == "1"
        if should_notify_empty or should_notify_low:
            try:
                level = "tomt lager" if should_notify_empty else "låg lagernivå"
                notify_rule_recipients(
                    "notification_recipients_empty_stock" if should_notify_empty else "notification_recipients_low_stock",
                    f"Lagerlarm: {request['object_name']}",
                    (
                        f"{request['object_name']} ({request['object_id']}) har {level}.\n\n"
                        f"Saldo efter utlåning: {available}\n"
                        f"Beställningspunkt: {min_quantity}\n"
                    ),
                    settings,
                )
            except Exception as error:
                log_event("notification", f"Kunde inte skicka lagerlarm för jobb #{request_id}: {error}")
    return {"request_id": request_id, "status": status}


def ensure_loan_for_request(db, request: dict[str, Any], timestamp: str) -> None:
    existing = db.execute(
        "SELECT loan_id FROM loans WHERE loan_request_id = ?",
        (request["request_id"],),
    ).fetchone()
    if existing:
        return

    quantity = int(request["quantity"])
    ensure_user_can_borrow(request["user_id"], request.get("user_name", ""), db)
    if int(request["available_quantity"]) < quantity:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt för att låna ut jobbet.")

    checkout_time = f"{request['lending_date']} 08:00:00" if len(request["lending_date"]) == 10 else request["lending_date"]
    due_time = f"{request['return_date']} 16:00:00" if len(request["return_date"]) == 10 else request["return_date"]
    db.execute(
        """
        INSERT INTO loans (
            user_id, object_id, quantity, checkout_time, due_time,
            engine_id, project_number, return_time, status, loan_request_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'active', ?)
        """,
        (
            request["user_id"],
            request["object_id"],
            quantity,
            checkout_time,
            due_time,
            request["engine_id"],
            request["project_number"],
            request["request_id"],
        ),
    )
    available = int(request["available_quantity"]) - quantity
    db.execute(
        "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
        (available, object_status(available, int(request["min_quantity"] or 0)), request["object_id"]),
    )
    db.execute(
        "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
        (timestamp, "loan", f"{request['user_name']} lånade {quantity} x {request['object_name']} ({request['object_id']}) via jobb {request['request_id']}"),
    )


def return_linked_loan_for_request(db, request: dict[str, Any], timestamp: str) -> None:
    active_loan = db.execute(
        "SELECT * FROM loans WHERE loan_request_id = ? AND status = 'active'",
        (request["request_id"],),
    ).fetchone()
    if not active_loan:
        active_loan = db.execute(
            """
            SELECT * FROM loans
            WHERE user_id = ?
              AND object_id = ?
              AND status = 'active'
            ORDER BY checkout_time DESC
            LIMIT 1
            """,
            (request["user_id"], request["object_id"]),
        ).fetchone()
    if not active_loan:
        return

    object_item = db.execute("SELECT * FROM objects WHERE object_id = ?", (active_loan["object_id"],)).fetchone()
    available = int(object_item["available_quantity"]) + int(active_loan["quantity"])
    db.execute(
        "UPDATE loans SET return_time = ?, status = 'returned' WHERE loan_id = ?",
        (timestamp, active_loan["loan_id"]),
    )
    db.execute(
        "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
        (available, object_status(available, int(object_item["min_quantity"] or 0)), active_loan["object_id"]),
    )


def delete_loan_request(request_id: int) -> dict[str, Any]:
    if request_id <= 0:
        raise ValueError("Ange jobb-ID.")

    request = row(
        """
        SELECT r.*, u.name AS user_name, o.name AS object_name,
               o.available_quantity, o.min_quantity, o.tornado_id, o.door_id
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
        db.execute("DELETE FROM loan_requests WHERE request_id = ?", (request_id,))
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "job", f"Jobb {request_id} togs bort: {request['object_name']} för {request['user_name']}"),
        )
    return {"request_id": request_id}


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
    if is_consumable_object(dict(object_item)):
        raise ValueError("Förbrukningsvaror kan inte lånas. Använd sidan Anmäl slut på lager.")
    if object_item["available_quantity"] < quantity:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt.")

    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    ensure_user_can_borrow(user_id, user["name"])

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
        if active_loan.get("loan_request_id"):
            db.execute(
                "UPDATE loan_requests SET status = 'returned', updated_at = ? WHERE request_id = ?",
                (returned_at, active_loan["loan_request_id"]),
            )
        else:
            db.execute(
                """
                UPDATE loan_requests
                SET status = 'returned', updated_at = ?
                WHERE request_id = (
                    SELECT request_id FROM loan_requests
                    WHERE user_id = ?
                      AND object_id = ?
                      AND status = 'loaned'
                    ORDER BY updated_at DESC
                    LIMIT 1
                )
                """,
                (returned_at, active_loan["user_id"], active_loan["object_id"]),
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
