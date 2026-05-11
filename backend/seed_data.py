from __future__ import annotations

from datetime import datetime

from backend.database import connect, row


OBJECTS = [
    ("OBJ-1001", "Momentnyckel 20-100 Nm", "Verktyg", "MW-20100", "Tornado A / Hylla 2", "Tornado A", "12", 4, 4, 1, "Tillgänglig"),
    ("OBJ-1002", "Digitalt skjutmått", "Mätning", "CAL-D150", "Tornado A / Hylla 3", "Tornado A", "18", 3, 3, 1, "Tillgänglig"),
    ("OBJ-1003", "M8 insexbits lång", "Bits", "BIT-M8-L", "Tornado B / Fack 7", "Tornado B", "7", 20, 6, 8, "Låg nivå"),
    ("OBJ-1004", "Loctite 243", "Kem", "LOC-243", "Kemskåp 1 / Låda 4", "Kemskåp 1", "4", 12, 12, 3, "Tillgänglig"),
    ("OBJ-1005", "USB-C servicekabel", "Elektronik", "USB-C-SRV", "Servicevagn / Låda 1", "Servicevagn", "1", 8, 8, 2, "Tillgänglig"),
    ("OBJ-1006", "Tryckluftsadapter G1/4", "Pneumatik", "PNE-G14", "Tornado B / Fack 11", "Tornado B", "11", 15, 15, 5, "Tillgänglig"),
    ("OBJ-1007", "Tryckgivare 0-10 bar", "Sensor", "PRS-010B", "Tornado C / Fack 3", "Tornado C", "3", 6, 6, 2, "Tillgänglig"),
    ("OBJ-1008", "Induktiv givare M12", "Sensor", "SEN-M12-IND", "Tornado C / Fack 4", "Tornado C", "4", 10, 10, 3, "Tillgänglig"),
]

USERS = [
    ("USR-001", "Anna Lind", "Underhåll", 1),
    ("USR-002", "Erik Holm", "Produktion", 1),
    ("USR-003", "Sara Nilsson", "Kvalitet", 1),
    ("USR-004", "Jonas Berg", "Automation", 1),
]


def seed_database() -> None:
    count = row("SELECT COUNT(*) AS value FROM objects")
    first_seed = not count or count["value"] == 0

    with connect() as db:
        db.executemany(
            """
            INSERT OR IGNORE INTO objects (
                object_id, name, category, article_number, location, tornado_id, door_id,
                total_quantity, available_quantity, min_quantity, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            OBJECTS,
        )
        if first_seed:
            db.executemany(
                "INSERT OR IGNORE INTO users (user_id, name, department, active) VALUES (?, ?, ?, ?)",
                USERS,
            )
            db.execute(
                "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "system", "Demo data skapad"),
            )
