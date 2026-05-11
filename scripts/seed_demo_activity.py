from __future__ import annotations

import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "inventory.db"
TAG = "[demo-activity-2026-05]"


DEMO_JOBS = [
    # Active loans: mix of overdue, due today, and future due dates.
    ("loaned", "Ronja Viklund", "DA0457SP", 2, "2026-04-24", "2026-05-03", None, "Rig-41", "PRJ-2401"),
    ("loaned", "Anton Hallberg", "OBJ-1007", 1, "2026-04-29", "2026-05-07", None, "Testrigg 2", "PRJ-2402"),
    ("loaned", "Elin Karlsson", "9047010000", 1, "2026-05-02", "2026-05-10", None, "Motorcell 5", "PRJ-2403"),
    ("loaned", "Tommy Eriksson", "MV0235SP", 1, "2026-04-22", "2026-05-02", None, "HIL-rigg", "PRJ-2398"),
    ("loaned", "Oscar Nyberg", "COM-03", 2, "2026-05-05", "2026-05-11", None, "Rig-33", "PRJ-2410"),
    ("loaned", "Maja Svensson", "L8820152-1", 1, "2026-05-06", "2026-05-11", None, "Motorcell 3", "PRJ-2411"),
    ("loaned", "Freja Larsson", "H580383-01-2", 1, "2026-05-07", "2026-05-14", None, "Rig-12", "PRJ-2412"),
    ("loaned", "Viktor Lindgren", "G8812449", 1, "2026-05-08", "2026-05-16", None, "Tornado C", "PRJ-2413"),
    ("loaned", "Nora Bergstrom", "DA0821", 2, "2026-05-09", "2026-05-18", None, "Rig-08", "PRJ-2414"),
    ("loaned", "Emil Andersson", "637092", 1, "2026-05-10", "2026-05-24", None, "Motorcell 1", "PRJ-2415"),

    # Ready for pickup.
    ("prepared", "Anton Hallberg", "H0454881001-1", 1, "2026-05-12", "2026-05-26", None, "Rig-20", "PRJ-2420"),
    ("prepared", "Maja Svensson", "3200082673", 2, "2026-05-13", "2026-05-20", None, "Motorcell 4", "PRJ-2421"),
    ("prepared", "Nora Bergstrom", "MM2202SP", 1, "2026-05-14", "2026-05-28", None, "Rig-02", "PRJ-2422"),
    ("prepared", "Tommy Eriksson", "904702380001", 1, "2026-05-15", "2026-05-29", None, "Provbänk 7", "PRJ-2423"),

    # Incoming requests.
    ("requested", "Ronja Viklund", "DA0943", 1, "2026-05-16", "2026-05-30", None, "Rig-41", "PRJ-2430"),
    ("requested", "Elin Karlsson", "F023370400", 1, "2026-05-17", "2026-05-24", None, "Motorcell 5", "PRJ-2431"),
    ("requested", "Viktor Lindgren", "G0163010", 1, "2026-05-18", "2026-06-01", None, "Tornado A", "PRJ-2432"),
    ("requested", "Oscar Nyberg", "G8812728", 2, "2026-05-19", "2026-06-02", None, "Rig-33", "PRJ-2433"),

    # Historical returns, used by statistics graphs.
    ("returned", "Anton Hallberg", "000290 Tryckgivare", 1, "2026-03-18", "2026-03-28", "2026-03-27", "Testrigg 2", "PRJ-2301"),
    ("returned", "Ronja Viklund", "0-RING", 4, "2026-04-01", "2026-04-08", "2026-04-10", "Rig-41", "PRJ-2302"),
    ("returned", "Elin Karlsson", "MM4894SP", 1, "2026-04-12", "2026-04-21", "2026-04-21", "Motorcell 5", "PRJ-2303"),
    ("returned", "Maja Svensson", "QA3773", 1, "2026-04-20", "2026-05-01", "2026-05-05", "Motorcell 4", "PRJ-2304"),
    ("returned", "Emil Andersson", "000291 Tryckgivare", 1, "2026-05-01", "2026-05-08", "2026-05-09", "Motorcell 1", "PRJ-2305"),
    ("returned", "Freja Larsson", "EU2940", 3, "2026-05-03", "2026-05-07", "2026-05-07", "Rig-12", "PRJ-2306"),

    # Returned and stocked jobs.
    ("stocked", "Oscar Nyberg", "DA1003", 1, "2026-04-05", "2026-04-15", "2026-04-14", "Rig-33", "PRJ-2310"),
    ("stocked", "Nora Bergstrom", "COM-GC3", 1, "2026-04-18", "2026-04-30", "2026-05-02", "Rig-08", "PRJ-2311"),
    ("stocked", "Viktor Lindgren", "H2004452001-2", 1, "2026-05-02", "2026-05-09", "2026-05-10", "Tornado A", "PRJ-2312"),
]


def object_status(available_quantity: int, min_quantity: int) -> str:
    if available_quantity <= 0:
        return "Slut"
    if available_quantity <= min_quantity:
        return "Låg nivå"
    return "Tillgänglig"


def at(date_text: str, hour: int, minute: int = 0) -> str:
    return f"{date_text} {hour:02d}:{minute:02d}:00"


def created_at(lending_date: str) -> str:
    created = datetime.strptime(lending_date, "%Y-%m-%d") - timedelta(days=1)
    return created.strftime("%Y-%m-%d 14:30:00")


def fetch_one(db: sqlite3.Connection, sql: str, params: tuple[object, ...]) -> sqlite3.Row:
    item = db.execute(sql, params).fetchone()
    if item is None:
        raise RuntimeError(f"Saknar data för: {params}")
    return item


def update_available(db: sqlite3.Connection, object_id: str, delta: int) -> None:
    item = fetch_one(
        db,
        "SELECT available_quantity, total_quantity, min_quantity FROM objects WHERE object_id = ?",
        (object_id,),
    )
    available = max(0, min(int(item["total_quantity"] or 0), int(item["available_quantity"] or 0) + delta))
    db.execute(
        "UPDATE objects SET available_quantity = ?, status = ? WHERE object_id = ?",
        (available, object_status(available, int(item["min_quantity"] or 0)), object_id),
    )


def remove_previous_demo(db: sqlite3.Connection) -> int:
    request_ids = [
        int(row["request_id"])
        for row in db.execute("SELECT request_id FROM loan_requests WHERE note LIKE ?", (f"{TAG}%",))
    ]
    if not request_ids:
        return 0

    placeholders = ",".join("?" for _ in request_ids)
    active_loans = db.execute(
        f"SELECT object_id, quantity FROM loans WHERE status = 'active' AND loan_request_id IN ({placeholders})",
        request_ids,
    ).fetchall()
    for loan in active_loans:
        update_available(db, loan["object_id"], int(loan["quantity"]))

    db.execute(f"DELETE FROM loans WHERE loan_request_id IN ({placeholders})", request_ids)
    db.execute(f"DELETE FROM loan_requests WHERE request_id IN ({placeholders})", request_ids)
    return len(request_ids)


def insert_demo_job(
    db: sqlite3.Connection,
    status: str,
    user_name: str,
    object_id: str,
    quantity: int,
    lending_date: str,
    return_date: str,
    return_time_date: str | None,
    engine_id: str,
    project_number: str,
) -> None:
    user = fetch_one(db, "SELECT user_id FROM users WHERE name = ? AND active = 1", (user_name,))
    item = fetch_one(
        db,
        "SELECT name, available_quantity, min_quantity FROM objects WHERE object_id = ?",
        (object_id,),
    )
    if status == "loaned" and int(item["available_quantity"] or 0) < quantity:
        raise RuntimeError(f"För lite saldo för {object_id}: behöver {quantity}.")

    note = f"{TAG} {status} {user_name} {object_id}"
    cursor = db.execute(
        """
        INSERT INTO loan_requests (
            user_id, object_id, quantity, engine_id, project_number,
            lending_date, return_date, status, created_at, updated_at, note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["user_id"],
            object_id,
            quantity,
            engine_id,
            project_number,
            lending_date,
            return_date,
            status,
            created_at(lending_date),
            at(return_time_date or lending_date, 15, 20) if status in {"returned", "stocked"} else at(lending_date, 8, 10),
            note,
        ),
    )
    request_id = int(cursor.lastrowid)

    if status == "loaned":
        db.execute(
            """
            INSERT INTO loans (
                user_id, object_id, quantity, checkout_time, due_time,
                engine_id, project_number, return_time, status, loan_request_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 'active', ?)
            """,
            (
                user["user_id"],
                object_id,
                quantity,
                at(lending_date, 8),
                at(return_date, 16),
                engine_id,
                project_number,
                request_id,
            ),
        )
        update_available(db, object_id, -quantity)

    if status in {"returned", "stocked"}:
        db.execute(
            """
            INSERT INTO loans (
                user_id, object_id, quantity, checkout_time, due_time,
                engine_id, project_number, return_time, status, loan_request_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'returned', ?)
            """,
            (
                user["user_id"],
                object_id,
                quantity,
                at(lending_date, 8),
                at(return_date, 16),
                engine_id,
                project_number,
                at(return_time_date or return_date, 14, 45),
                request_id,
            ),
        )


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit(f"Hittar inte databasen: {DB_PATH}")

    backup_path = DB_PATH.with_name(f"inventory_backup_before_demo_activity_{datetime.now():%Y%m%d_%H%M%S}.db")
    shutil.copy2(DB_PATH, backup_path)

    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        removed = remove_previous_demo(db)
        for job in DEMO_JOBS:
            insert_demo_job(db, *job)
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "system", "Demojobb och demolån uppdaterade för statistik."),
        )

    print(f"Backup skapad: {backup_path}")
    print(f"Tog bort tidigare demojobb: {removed}")
    print(f"Lade till demojobb: {len(DEMO_JOBS)}")


if __name__ == "__main__":
    main()
