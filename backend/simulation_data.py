"""Deterministic fictional activity for a marked, isolated simulation only."""
from __future__ import annotations

from datetime import datetime, timedelta
import os
import sqlite3

from backend import database
from backend.seed_data import OBJECTS
from backend.services.common import object_status
from simulation_store import validate_simulation


GROUPS = ("Demo Underhåll", "Demo Produktion", "Demo Kvalitet", "Demo Automation", "Demo Externa")
NAMES = (
    ("Anna", "Lind"), ("Erik", "Holm"), ("Sara", "Nilsson"), ("Jonas", "Berg"),
    ("Maja", "Dahl"), ("Oskar", "Lund"), ("Elin", "Sand"), ("Viktor", "Ek"),
    ("Nora", "Lindgren"), ("Leo", "Sjö"), ("Alva", "Björk"), ("Emil", "Strand"),
    ("Ida", "Hed"), ("Axel", "Vik"), ("Ella", "Fors"),
)


def seed_simulation(today: datetime | None = None) -> None:
    if os.environ.get("LOAN_SIMULATION") != "1":
        raise ValueError("Demonstrationsaktivitet får endast skapas i Simulering.")
    validate_simulation(database.DATABASE_PATH)
    base = (today or datetime.now()).replace(hour=12, minute=0, second=0, microsecond=0)

    def at(days: int, hour: int = 12) -> str:
        return (base + timedelta(days=days)).replace(hour=hour).strftime("%Y-%m-%d %H:%M:%S")

    with database.connect() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT seeded FROM simulation_metadata WHERE id=1").fetchone()[0]:
            return
        if any(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
               for table in ("users", "objects", "loans", "loan_requests", "user_groups")):
            raise ValueError("Oväntade data i en oinitierad demo. Återställ demodata i startfönstret.")
        db.executemany(
            """INSERT INTO objects (object_id,name,category,article_number,location,tornado_id,door_id,
               total_quantity,available_quantity,min_quantity,status) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            [(*item[:8], item[7], item[9], object_status(item[7], item[9])) for item in OBJECTS],
        )
        db.execute("UPDATE objects SET is_consumable=1 WHERE object_id='OBJ-1004'")
        for index, group in enumerate(GROUPS, 1):
            db.execute("INSERT INTO user_groups(name,department,created_at,updated_at) VALUES (?,?,?,?)",
                       (group, f"DEMO-{index:02d}", at(-600), at(-600)))
        for index, (first, last) in enumerate(NAMES, 1):
            external = index in (5, 8, 10, 11, 15)
            group_index = 4 if external else (index - 1) % 4
            db.execute(
                """INSERT INTO users (user_id,name,first_name,last_name,email,phone,company,alias,
                   department,department_name,role,active,borrow_override,created_at,updated_at,
                   privacy_notice_acknowledged_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (f"USR-{index:03d}", f"Demo {first} {last}", f"Demo {first}", last,
                 f"demo{index:02d}@example.invalid", "", "Demo Extern AB" if external else "Demo Intern",
                 f"DEMO-{index:03d}", f"DEMO-{group_index + 1:02d}", GROUPS[group_index], "operator",
                 0 if index == 13 else 1, 1 if index == 12 else 0, at(-600), at(-600), at(-600)),
            )
        db.executemany(
            "INSERT INTO system_settings(key,value,updated_at) VALUES (?,?,?)",
            [(key, value, at(0)) for key, value in {
                "overdue_block_enabled": "1", "overdue_block_limit": "3",
                "inactive_user_warning_enabled": "1", "inactive_user_days": "365",
                "notify_admin_new_request": "1", "notify_admin_loaned": "1",
            }.items()],
        )

        def job(user: int, items: list[tuple[str, int]], status: str, start: int, due: int,
                returned: int | None = None, damage: str | None = None, partial: bool = False) -> None:
            group_id = None
            for offset, (object_id, quantity) in enumerate(items):
                request = db.execute(
                    """INSERT INTO loan_requests (user_id,object_id,quantity,engine_id,project_number,
                       lending_date,return_date,status,created_at,updated_at,note,request_group_id)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"USR-{user:03d}", object_id, quantity, f"DEMO-RIG-{user:02d}", f"DEMO-P{user:03d}",
                     at(start)[:10], at(due)[:10], status, at(start - 1), at(returned if returned is not None else start),
                     "Påhittat demonstrationsärende", group_id),
                )
                request_id = request.lastrowid
                if group_id is None:
                    group_id = request_id
                    db.execute("UPDATE loan_requests SET request_group_id=? WHERE request_id=?", (group_id, request_id))
                db.execute("INSERT INTO events(event_time,event_type,message) VALUES (?,'request','Demo')", (at(start - 1),))
                if status in ("requested", "approved", "prepared"):
                    continue
                returned_quantity = 1 if partial and offset == 0 else quantity if returned is not None else 0
                fully_returned = returned_quantity == quantity
                loan_id = db.execute(
                    """INSERT INTO loans (user_id,object_id,quantity,checkout_time,due_time,return_time,
                       status,loan_request_id,returned_quantity,engine_id,project_number)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                    (f"USR-{user:03d}", object_id, quantity, at(start, 8), at(due, 16),
                     at(returned) if fully_returned else None, "returned" if fully_returned else "active",
                     request_id, returned_quantity, f"DEMO-RIG-{user:02d}", f"DEMO-P{user:03d}"),
                ).lastrowid
                db.execute("INSERT INTO events(event_time,event_type,message) VALUES (?,'loan','Demo')", (at(start, 8),))
                if returned_quantity:
                    damage_status = damage if offset == 0 else None
                    db.execute(
                        """INSERT INTO loan_returns (loan_id,quantity,damaged_quantity,damage_description,
                           damage_status,returned_at,resolved_at) VALUES (?,?,?,?,?,?,?)""",
                        (loan_id, returned_quantity, 1 if damage_status else 0,
                         "Demo: skadat hölje vid funktionstest." if damage_status else "", damage_status,
                         at(returned if returned is not None else -1),
                         at(returned + 1) if damage_status in ("repaired", "discarded") else None),
                    )
                    db.execute("INSERT INTO events(event_time,event_type,message) VALUES (?,'return','Demo')",
                               (at(returned if returned is not None else -1),))
                    if damage_status == "discarded":
                        db.execute("UPDATE objects SET total_quantity=total_quantity-1 WHERE object_id=?", (object_id,))

        # Older completed activity fills charts without using fixed calendar dates.
        for index in range(30):
            object_id = ("OBJ-1003", "OBJ-1005", "OBJ-1006", "OBJ-1008")[index % 4]
            start = -250 + index * 7
            damage = "discarded" if index == 3 else "repaired" if index == 5 else None
            job(1 + index % 11, [(object_id, 1 + index % 2)], "stocked", start, start + 10,
                returned=start + 8 + index % 5, damage=damage)
        job(14, [("OBJ-1006", 1)], "stocked", -460, -450, returned=-452)

        # Seven recently returned jobs, including unresolved and repaired damage.
        for index in range(7):
            damage = "quarantined" if index == 0 else "repaired" if index == 1 else None
            job(index + 1, [("OBJ-1007" if index == 0 else "OBJ-1006", 1)],
                "returned", -18 + index, -5 + index, returned=-8 + index, damage=damage)

        active_objects = (
            "OBJ-1001", "OBJ-1002", "OBJ-1003", "OBJ-1005", "OBJ-1006", "OBJ-1007", "OBJ-1008",
            "OBJ-1001", "OBJ-1002", "OBJ-1003", "OBJ-1005", "OBJ-1006", "OBJ-1007", "OBJ-1008",
            "OBJ-1001", "OBJ-1002", "OBJ-1003", "OBJ-1005", "OBJ-1006", "OBJ-1008",
        )
        for index, object_id in enumerate(active_objects):
            user = 2 if index < 3 else 12 if index in (3, 4) else 1 + index % 11
            overdue = index < 5
            items = [(object_id, 3 if index == 3 else 1)]
            if index % 5 == 4:
                items.append(("OBJ-1006", 1))
            job(user, items, "loaned", -25 if overdue else -6,
                -4 if overdue else (0, 3, 7, 14)[index % 4], partial=index == 3)

        for status, count in (("requested", 5), ("approved", 3), ("prepared", 3)):
            for index in range(count):
                items = [("OBJ-1006", 1)]
                if index == 0:
                    items.append(("OBJ-1005", 1))
                job(3 + index, items, status, 0, 10)
        db.execute("UPDATE objects SET available_quantity=0,status='Slut' WHERE object_id='OBJ-1004'")
        db.execute(
            """INSERT INTO consumable_reports(object_id,quantity,reported_by,message,status,created_at,updated_at)
               VALUES ('OBJ-1004',0,NULL,'Demo: behöver fyllas på','open',?,?)""", (at(-1), at(-1)),
        )
        for item in db.execute("SELECT object_id,total_quantity,min_quantity FROM objects WHERE is_consumable=0").fetchall():
            outstanding = db.execute(
                "SELECT COALESCE(SUM(quantity-returned_quantity),0) FROM loans WHERE object_id=?",
                (item["object_id"],),
            ).fetchone()[0]
            quarantined = db.execute(
                """SELECT COALESCE(SUM(r.damaged_quantity),0) FROM loan_returns r
                   JOIN loans l ON l.loan_id=r.loan_id WHERE l.object_id=? AND r.damage_status='quarantined'""",
                (item["object_id"],),
            ).fetchone()[0]
            available = item["total_quantity"] - outstanding - quarantined
            if available < 0:
                raise ValueError(f"Demodata överskrider lagersaldot för {item['object_id']}.")
            db.execute("UPDATE objects SET available_quantity=?,status=? WHERE object_id=?",
                       (available, object_status(available, item["min_quantity"]), item["object_id"]))
        if db.execute("PRAGMA foreign_key_check").fetchone():
            raise sqlite3.IntegrityError("Demodata innehåller en ogiltig databasreferens.")
        db.execute("UPDATE simulation_metadata SET seeded=1,generated_at=? WHERE id=1", (at(0),))
