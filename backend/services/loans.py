from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.database import connect, row, rows
from backend.services.notifications import get_system_settings, message_text, notify_rule_recipients, send_email
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
        SELECT l.*, u.name AS user_name, u.department AS user_department, u.email AS user_email,
               o.name AS object_name, o.tornado_id, o.door_id,
               COALESCE(r.request_group_id, r.request_id) AS request_group_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        LEFT JOIN loan_requests r ON r.request_id = l.loan_request_id
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


REQUEST_STATUSES = ("requested", "approved", "prepared", "loaned", "returned", "stocked")


def validate_loan_period(lending_date: str, return_date: str, settings: dict[str, str] | None = None) -> None:
    settings = settings or get_system_settings()
    try:
        start = datetime.fromisoformat(lending_date.replace(" ", "T")).date()
        end = datetime.fromisoformat(return_date.replace(" ", "T")).date()
    except ValueError:
        raise ValueError("Ange giltiga lånedatum.")
    if end < start:
        raise ValueError("Returdatum kan inte vara före utlåningsdatum.")
    max_days = max(1, int(settings.get("max_loan_days") or "90"))
    if (end - start).days > max_days:
        raise ValueError(f"Max lånetid är {max_days} dagar.")


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
    user_query = "SELECT borrow_override FROM users WHERE user_id = ?"
    if db is not None:
        user_override = db.execute(user_query, (user_id,)).fetchone()
    else:
        user_override = row(user_query, (user_id,))
    if user_override and int(user_override["borrow_override"] or 0) == 1:
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
        f"ERROR {borrower} är spärrad för nya lån eftersom aktiva lån inte lämnats tillbaka. Kontakta ELLAB."
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
                WHEN 'approved' THEN 2
                WHEN 'prepared' THEN 3
                WHEN 'loaned' THEN 4
                WHEN 'returned' THEN 5
                WHEN 'stocked' THEN 6
                ELSE 7
            END,
            r.updated_at DESC
        """
    )


def create_loan_request(payload: dict[str, Any]) -> dict[str, Any]:
    user_id = str(payload.get("user_id", "")).strip()
    lending_date = str(payload.get("lending_date", "")).strip()
    return_date = str(payload.get("due_time", "") or payload.get("return_date", "")).strip()
    items = payload.get("items", [{"object_id": payload.get("object_id", ""), "quantity": payload.get("quantity", 1)}])
    if not isinstance(items, list) or not items or len(items) > 100:
        raise ValueError("Välj mellan 1 och 100 artiklar.")
    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("Ogiltig artikelrad.")
        object_id = str(item.get("object_id", "")).strip()
        raw_quantity = item.get("quantity", 1)
        try:
            quantity = int(str(raw_quantity))
        except (ValueError, TypeError):
            raise ValueError("Antal måste vara ett positivt heltal.")
        if not object_id or quantity <= 0:
            raise ValueError("Välj artikel och ange ett positivt heltal.")
        quantities[object_id] = quantities.get(object_id, 0) + quantity
    settings = get_system_settings()
    validate_loan_period(lending_date, return_date, settings)
    timestamp = now_text()
    request_ids = []
    names = []
    article_lines = []
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        user = db.execute("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,)).fetchone()
        if user is None:
            raise ValueError("Välj en aktiv användare.")
        ensure_user_can_borrow(user_id, user["name"], db)
        for object_id, quantity in quantities.items():
            object_item = db.execute("SELECT * FROM objects WHERE object_id = ?", (object_id,)).fetchone()
            if object_item is None:
                raise ValueError(f"Objektet {object_id} hittades inte.")
            if is_consumable_object(dict(object_item)):
                raise ValueError("Förbrukningsvaror kan inte lånas. Använd sidan Förbrukningsvara.")
            duplicate = db.execute(
                """SELECT request_id FROM loan_requests
                   WHERE user_id = ? AND object_id = ? AND lending_date = ? AND return_date = ?
                     AND status IN ('requested', 'approved', 'prepared') LIMIT 1""",
                (user_id, object_id, lending_date, return_date),
            ).fetchone()
            if duplicate:
                raise ValueError(f"Det finns redan en öppen låneförfrågan #{duplicate['request_id']} för {object_item['name']}.")
            cursor = db.execute(
                """INSERT INTO loan_requests (
                    user_id, object_id, quantity, engine_id, project_number,
                    lending_date, return_date, status, created_at, updated_at, note
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'requested', ?, ?, ?)""",
                (user_id, object_id, quantity, optional_text(payload, "engine_id"),
                 optional_text(payload, "project_number"), lending_date, return_date,
                 timestamp, timestamp, optional_text(payload, "note")),
            )
            request_ids.append(int(cursor.lastrowid))
            names.append(f"{quantity} x {object_item['name']} ({object_id})")
            article_lines.append(f"• {quantity} × {object_item['name']}\n  Artikel-ID: {object_id}")
            db.execute("UPDATE loan_requests SET request_group_id = ? WHERE request_id = ?",
                       (request_ids[0], request_ids[-1]))
        db.execute("INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
                   (timestamp, "request", f"Låneförfrågan #{request_ids[0]} skapad: {user['name']}: {', '.join(names)}"))
    if settings.get("notify_new_job") == "1":
        try:
            message_values = {
                "request_id": request_ids[0], "user_name": user["name"],
                "object_name": ", ".join(names), "object_id": ", ".join(quantities),
                "quantity": sum(quantities.values()), "lending_date": lending_date, "return_date": return_date,
                "article_count": len(quantities), "object_list": "\n\n".join(article_lines),
            }
            notify_rule_recipients(
                "notification_recipients_new_job",
                message_text(settings, "message_new_job_subject", message_values),
                message_text(settings, "message_new_job_body", message_values), settings,
            )
        except Exception as error:
            log_event("notification", f"Kunde inte skicka jobbnotis #{request_ids[0]}: {error}")
    return {"request_id": request_ids[0], "request_ids": request_ids}


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
    new_available_quantity = None
    with connect() as db:
        if status == "loaned":
            new_available_quantity = ensure_loan_for_request(db, request, timestamp)
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
            message_values = {
                "request_id": request_id,
                "user_name": request["user_name"],
                "object_name": request["object_name"],
                "object_id": request["object_id"],
                "quantity": request["quantity"],
            }
            notify_rule_recipients(
                "notification_recipients_returned_loan",
                message_text(settings, "message_returned_loan_subject", message_values),
                message_text(settings, "message_returned_loan_body", message_values),
                settings,
            )
        except Exception as error:
            log_event("notification", f"Kunde inte skicka återlämningsnotis #{request_id}: {error}")
    if status == "loaned":
        quantity = int(request["quantity"])
        available = new_available_quantity
        if available is None:
            current_object = row("SELECT available_quantity FROM objects WHERE object_id = ?", (request["object_id"],))
            available = int(current_object["available_quantity"]) if current_object else 0
        min_quantity = int(request["min_quantity"] or 0)
        should_notify_empty = available <= 0 and settings.get("notify_empty_stock") == "1"
        should_notify_low = 0 < available <= min_quantity and settings.get("notify_low_stock") == "1"
        if should_notify_empty or should_notify_low:
            try:
                level = "tomt lager" if should_notify_empty else "låg lagernivå"
                message_values = {
                    "object_name": request["object_name"],
                    "object_id": request["object_id"],
                    "level": level,
                    "available": available,
                    "min_quantity": min_quantity,
                }
                notify_rule_recipients(
                    "notification_recipients_empty_stock" if should_notify_empty else "notification_recipients_low_stock",
                    message_text(settings, "message_stock_alert_subject", message_values),
                    message_text(settings, "message_stock_alert_body", message_values),
                    settings,
                )
            except Exception as error:
                log_event("notification", f"Kunde inte skicka lagerlarm för jobb #{request_id}: {error}")
    return {"request_id": request_id, "status": status}


def update_loan_request_group_status(payload: dict[str, Any]) -> dict[str, Any]:
    group_id = int(payload.get("request_group_id", 0))
    status = str(payload.get("status", "")).strip()
    if group_id <= 0:
        raise ValueError("Ange förfrågnings-ID.")
    if status not in REQUEST_STATUSES:
        raise ValueError("Ogiltig jobbstatus.")

    previous_status = {
        "approved": "requested",
        "prepared": "approved",
        "loaned": "prepared",
        "returned": "loaned",
        "stocked": "returned",
    }.get(status)
    if previous_status is None:
        raise ValueError("En samlad förfrågan kan bara flyttas framåt ett steg i taget.")

    timestamp = now_text()
    changed_requests: list[dict[str, Any]] = []
    stock_levels: list[tuple[dict[str, Any], int | None]] = []
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        request_rows = db.execute(
            """
            SELECT r.*, u.name AS user_name, u.email AS user_email, o.name AS object_name,
                   o.available_quantity, o.min_quantity, o.tornado_id, o.door_id
            FROM loan_requests r
            JOIN users u ON u.user_id = r.user_id
            JOIN objects o ON o.object_id = r.object_id
            WHERE COALESCE(r.request_group_id, r.request_id) = ?
            ORDER BY r.request_id
            """,
            (group_id,),
        ).fetchall()
        if not request_rows:
            raise ValueError("Förfrågan hittades inte.")

        invalid = [request for request in request_rows if request["status"] not in (previous_status, status)]
        if invalid:
            raise ValueError(
                f"Alla artiklar måste vara {previous_status} innan förfrågan kan ändras till {status}."
            )

        for request_row in request_rows:
            if request_row["status"] == status:
                continue
            request = dict(request_row)
            available = None
            if status == "loaned":
                available = ensure_loan_for_request(db, request, timestamp)
            elif status == "returned":
                return_linked_loan_for_request(db, request, timestamp)
            db.execute(
                "UPDATE loan_requests SET status = ?, updated_at = ? WHERE request_id = ?",
                (status, timestamp, request["request_id"]),
            )
            changed_requests.append(request)
            stock_levels.append((request, available))

        if changed_requests:
            db.execute(
                "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
                (
                    timestamp,
                    "job",
                    f"Förfrågan {group_id} ändrades till {status}: {len(changed_requests)} artikelrader",
                ),
            )

    settings = get_system_settings()
    if status == "returned" and changed_requests and settings.get("notify_returned_loan") == "1":
        try:
            first = changed_requests[0]
            names = ", ".join(
                f"{request['quantity']} x {request['object_name']} ({request['object_id']})"
                for request in changed_requests
            )
            message_values = {
                "request_id": group_id,
                "user_name": first["user_name"],
                "object_name": names,
                "object_id": ", ".join(request["object_id"] for request in changed_requests),
                "quantity": sum(int(request["quantity"]) for request in changed_requests),
            }
            notify_rule_recipients(
                "notification_recipients_returned_loan",
                message_text(settings, "message_returned_loan_subject", message_values),
                message_text(settings, "message_returned_loan_body", message_values),
                settings,
            )
        except Exception as error:
            log_event("notification", f"Kunde inte skicka återlämningsnotis för förfrågan #{group_id}: {error}")

    if status == "loaned":
        for request, available in stock_levels:
            if available is None:
                continue
            min_quantity = int(request["min_quantity"] or 0)
            should_notify_empty = available <= 0 and settings.get("notify_empty_stock") == "1"
            should_notify_low = 0 < available <= min_quantity and settings.get("notify_low_stock") == "1"
            if not (should_notify_empty or should_notify_low):
                continue
            try:
                level = "tomt lager" if should_notify_empty else "låg lagernivå"
                message_values = {
                    "object_name": request["object_name"],
                    "object_id": request["object_id"],
                    "level": level,
                    "available": available,
                    "min_quantity": min_quantity,
                }
                notify_rule_recipients(
                    "notification_recipients_empty_stock" if should_notify_empty else "notification_recipients_low_stock",
                    message_text(settings, "message_stock_alert_subject", message_values),
                    message_text(settings, "message_stock_alert_body", message_values),
                    settings,
                )
            except Exception as error:
                log_event("notification", f"Kunde inte skicka lagerlarm för förfrågan #{group_id}: {error}")

    return {
        "request_group_id": group_id,
        "request_ids": [request["request_id"] for request in changed_requests],
        "status": status,
    }


def update_loan_request_details(payload: dict[str, Any]) -> dict[str, Any]:
    request_id = int(payload.get("request_id", 0))
    if request_id <= 0:
        raise ValueError("Ange jobb-ID.")

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
    if request["status"] in ("returned", "stocked"):
        raise ValueError("Återlämnade och lagerförda jobb kan inte ändras.")

    engine_id = optional_text(payload, "engine_id")
    project_number = optional_text(payload, "project_number")
    return_date = str(payload.get("return_date", "")).strip()
    if not return_date:
        raise ValueError("Ange returdatum.")

    active_loan = row("SELECT * FROM loans WHERE loan_request_id = ? AND status = 'active'", (request_id,))
    if active_loan:
        lending_date = str(request["lending_date"])
        quantity = int(request["quantity"])
    else:
        lending_date = str(payload.get("lending_date", "")).strip()
        quantity = int(payload.get("quantity", request["quantity"]))
        if not lending_date:
            raise ValueError("Ange utlåningsdatum.")
        if quantity <= 0:
            raise ValueError("Antal måste vara större än 0.")

    validate_loan_period(lending_date, return_date)
    timestamp = now_text()
    with connect() as db:
        db.execute(
            """
            UPDATE loan_requests
            SET quantity = ?, engine_id = ?, project_number = ?,
                lending_date = ?, return_date = ?, updated_at = ?
            WHERE request_id = ?
            """,
            (quantity, engine_id, project_number, lending_date, return_date, timestamp, request_id),
        )
        if active_loan:
            due_value = f"{return_date} 16:00:00" if len(return_date) == 10 else return_date
            db.execute(
                """
                UPDATE loans
                SET due_time = ?, engine_id = ?, project_number = ?
                WHERE loan_id = ?
                """,
                (due_value, engine_id, project_number, active_loan["loan_id"]),
            )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "job", f"Jobb {request_id} uppdaterades: {request['object_name']} för {request['user_name']}"),
        )
    return {"request_id": request_id}


def ensure_loan_for_request(db, request: dict[str, Any], timestamp: str) -> int | None:
    existing = db.execute(
        "SELECT loan_id FROM loans WHERE loan_request_id = ?",
        (request["request_id"],),
    ).fetchone()
    if existing:
        return None

    quantity = int(request["quantity"])
    ensure_user_can_borrow(request["user_id"], request["user_name"] or "", db)
    object_item = db.execute(
        "SELECT available_quantity, min_quantity FROM objects WHERE object_id = ?",
        (request["object_id"],),
    ).fetchone()
    if object_item is None:
        raise ValueError("Objektet hittades inte.")
    current_available = int(object_item["available_quantity"])
    min_quantity = int(object_item["min_quantity"] or 0)
    if current_available < quantity:
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
    available = current_available - quantity
    cursor = db.execute(
        """
        UPDATE objects
        SET available_quantity = ?, status = ?
        WHERE object_id = ?
          AND available_quantity >= ?
        """,
        (available, object_status(available, min_quantity), request["object_id"], quantity),
    )
    if cursor.rowcount != 1:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt för att låna ut jobbet.")
    db.execute(
        "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
        (timestamp, "loan", f"{request['user_name']} lånade {quantity} x {request['object_name']} ({request['object_id']}) via jobb {request['request_id']}"),
    )
    return available


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
              AND loan_request_id IS NULL
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


def send_pickup_ready_email(request_id: int) -> dict[str, Any]:
    if request_id <= 0:
        raise ValueError("Ange jobb-ID.")

    request = row(
        """
        SELECT r.*, u.name AS user_name, u.email AS user_email, o.name AS object_name
        FROM loan_requests r
        JOIN users u ON u.user_id = r.user_id
        JOIN objects o ON o.object_id = r.object_id
        WHERE r.request_id = ? OR COALESCE(r.request_group_id, r.request_id) = ?
        ORDER BY CASE WHEN r.request_id = ? THEN 0 ELSE 1 END, r.request_id
        LIMIT 1
        """,
        (request_id, request_id, request_id),
    )
    if request is None:
        raise ValueError("Jobbet hittades inte.")
    group_id = int(request.get("request_group_id") or request["request_id"])
    requests = rows(
        """
        SELECT r.*, u.name AS user_name, u.email AS user_email, o.name AS object_name
        FROM loan_requests r
        JOIN users u ON u.user_id = r.user_id
        JOIN objects o ON o.object_id = r.object_id
        WHERE COALESCE(r.request_group_id, r.request_id) = ?
        ORDER BY r.request_id
        """,
        (group_id,),
    )
    if any(item["status"] != "prepared" for item in requests):
        raise ValueError("Alla artiklar måste vara Redo att hämta innan mail kan skickas.")
    if not str(requests[0]["user_email"] or "").strip():
        raise ValueError("Låntagaren saknar e-postadress.")

    settings = get_system_settings()
    if settings.get("notify_pickup_ready") != "1":
        raise ValueError("Mail för klar att hämta är avstängt i Admin-inställningar.")
    message_values = {
        "request_id": group_id,
        "user_name": requests[0]["user_name"],
        "object_name": ", ".join(
            f"{item['quantity']} x {item['object_name']} ({item['object_id']})" for item in requests
        ),
        "object_id": ", ".join(item["object_id"] for item in requests),
        "quantity": sum(int(item["quantity"]) for item in requests),
        "lending_date": requests[0]["lending_date"],
        "return_date": requests[0]["return_date"],
    }
    sent = send_email(
        message_text(settings, "message_pickup_ready_subject", message_values),
        message_text(settings, "message_pickup_ready_body", message_values),
        [requests[0]["user_email"]],
        settings,
    )
    timestamp = now_text()
    with connect() as db:
        db.execute(
            """UPDATE loan_requests SET pickup_ready_email_sent_at = ?, updated_at = ?
               WHERE COALESCE(request_group_id, request_id) = ?""",
            (timestamp, timestamp, group_id),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (timestamp, "notification", f"Mail om redo att hämta skickat för förfrågan #{group_id}: {sent}"),
        )
    return {"request_id": group_id, "request_group_id": group_id, "sent": sent, "pickup_ready_email_sent_at": timestamp}


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
        raise ValueError("Förbrukningsvaror kan inte lånas. Använd sidan Förbrukningsvara.")
    if object_item["available_quantity"] < quantity:
        raise ValueError("Det finns inte tillräckligt antal tillgängligt.")

    user = row("SELECT * FROM users WHERE user_id = ? AND active = 1", (user_id,))
    if user is None:
        raise ValueError("Användaren hittades inte.")

    ensure_user_can_borrow(user_id, user["name"])
    validate_loan_period(lending_date, due_time)

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
    loan_ids = payload.get("loan_ids")
    identifier = str(payload.get("identifier", "")).strip()
    if loan_ids is not None:
        if not isinstance(loan_ids, list) or not loan_ids:
            raise ValueError("Välj minst ett aktivt lån.")
        try:
            loan_ids = list(dict.fromkeys(int(str(value)) for value in loan_ids))
        except (ValueError, TypeError):
            raise ValueError("Ogiltigt lån-ID.")
        if len(loan_ids) > 500 or any(value <= 0 for value in loan_ids):
            raise ValueError("Ogiltigt urval av lån.")
        if not payload.get("user_id"):
            raise ValueError("Välj användare.")
    elif not identifier:
        raise ValueError("Ange objekt-ID eller lån-ID.")
    returned_at = now_text()
    with connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if loan_ids is None:
            condition = "l.loan_id = ?" if identifier.isdigit() else "l.object_id = ?"
            found = db.execute(_active_loan_query(condition), (identifier,)).fetchone()
            active_loans = [found] if found else []
        else:
            active_loans = [db.execute(_active_loan_query("l.loan_id = ? AND l.user_id = ?"),
                                      (loan_id, str(payload["user_id"]))).fetchone() for loan_id in loan_ids]
        if not active_loans or any(loan is None for loan in active_loans):
            raise ValueError("Ett valt lån är inte längre aktivt eller tillhör inte användaren. Uppdatera listan.")
        for loan in active_loans:
            object_item = db.execute("SELECT * FROM objects WHERE object_id = ?", (loan["object_id"],)).fetchone()
            available = object_item["available_quantity"] + loan["quantity"]
            db.execute("UPDATE loans SET return_time = ?, status = 'returned' WHERE loan_id = ?",
                       (returned_at, loan["loan_id"]))
            db.execute("UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
                       (available, object_status(available, object_item["min_quantity"]), loan["object_id"]))
            if loan["loan_request_id"]:
                db.execute("UPDATE loan_requests SET status = 'returned', updated_at = ? WHERE request_id = ?",
                           (returned_at, loan["loan_request_id"]))
            else:
                db.execute("""UPDATE loan_requests SET status = 'returned', updated_at = ? WHERE request_id = (
                    SELECT request_id FROM loan_requests WHERE user_id = ? AND object_id = ? AND status = 'loaned'
                    ORDER BY updated_at DESC LIMIT 1)""", (returned_at, loan["user_id"], loan["object_id"]))
            db.execute("INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
                       (returned_at, "return", f"{loan['user_name']} lämnade tillbaka {loan['quantity']} x {loan['object_name']} ({loan['object_id']})"))
    for loan in active_loans:
        open_door(loan["tornado_id"], loan["door_id"], "return")
    return {"loan_id": active_loans[0]["loan_id"], "loan_ids": [loan["loan_id"] for loan in active_loans]}


def _active_loan_query(condition: str) -> str:
    return f"""
        SELECT l.*, u.name AS user_name, u.department AS user_department, o.name AS object_name, o.tornado_id, o.door_id
        FROM loans l
        JOIN users u ON u.user_id = l.user_id
        JOIN objects o ON o.object_id = l.object_id
        WHERE l.status = 'active' AND {condition}
        ORDER BY l.checkout_time ASC
    """
