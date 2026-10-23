from __future__ import annotations

import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from app_runtime import backup_before_migration, default_database

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATABASE_PATH = Path(os.environ.get("LOAN_DATABASE_PATH", str(default_database())))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    backup_before_migration(DATABASE_PATH)
    with connect() as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS access_accounts (
                username TEXT PRIMARY KEY,
                salt TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('operator','admin','superadmin')),
                user_id TEXT,
                revision INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
            CREATE TABLE IF NOT EXISTS privacy_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS local_test_accounts (
                username TEXT PRIMARY KEY
            );
            CREATE TABLE IF NOT EXISTS security_audit (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                actor TEXT NOT NULL,
                user_id TEXT,
                action TEXT NOT NULL,
                status INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS objects (
                object_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                item_type TEXT,
                description TEXT,
                article_number TEXT,
                supplier_article_number TEXT,
                location TEXT NOT NULL,
                storage_location_2 TEXT,
                tornado_id TEXT NOT NULL,
                door_id TEXT NOT NULL,
                belongs_to_instrument TEXT,
                device TEXT,
                belongs_to TEXT,
                last_changed TEXT,
                search_words TEXT,
                tray_for TEXT,
                lift_tray TEXT,
                total_quantity INTEGER NOT NULL CHECK(total_quantity >= 0),
                available_quantity INTEGER NOT NULL CHECK(available_quantity >= 0),
                min_quantity INTEGER NOT NULL CHECK(min_quantity >= 0),
                status TEXT NOT NULL,
                is_consumable INTEGER NOT NULL DEFAULT 0,
                image_data TEXT
            );

            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                first_name TEXT,
                last_name TEXT,
                email TEXT,
                phone TEXT,
                company TEXT,
                alias TEXT,
                department TEXT,
                department_name TEXT,
                rfid_code TEXT,
                role TEXT NOT NULL DEFAULT 'operator',
                created_at TEXT,
                updated_at TEXT,
                privacy_notice_acknowledged_at TEXT,
                active INTEGER NOT NULL DEFAULT 1,
                borrow_override INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS loans (
                loan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                object_id TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                checkout_time TEXT NOT NULL,
                due_time TEXT NOT NULL,
                engine_id TEXT,
                project_number TEXT,
                return_time TEXT,
                status TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(object_id) REFERENCES objects(object_id)
            );

            CREATE TABLE IF NOT EXISTS events (
                event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_time TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS loan_returns (
                return_id INTEGER PRIMARY KEY AUTOINCREMENT,
                loan_id INTEGER NOT NULL REFERENCES loans(loan_id) ON DELETE CASCADE,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                damaged_quantity INTEGER NOT NULL DEFAULT 0 CHECK(damaged_quantity >= 0 AND damaged_quantity <= quantity),
                damage_description TEXT NOT NULL DEFAULT '',
                damage_status TEXT CHECK(damage_status IN ('quarantined', 'repaired', 'discarded')),
                returned_at TEXT NOT NULL,
                resolved_at TEXT,
                CHECK((damaged_quantity = 0 AND damage_status IS NULL) OR
                      (damaged_quantity > 0 AND damage_status IS NOT NULL))
            );
            CREATE INDEX IF NOT EXISTS loan_returns_loan ON loan_returns(loan_id);

            CREATE TRIGGER IF NOT EXISTS minimize_new_event_text
            AFTER INSERT ON events WHEN NEW.event_type != 'privacy'
            BEGIN
                UPDATE events SET message = 'Händelse registrerad; personuppgifter utelämnas'
                WHERE event_id = NEW.event_id;
            END;
            CREATE TABLE IF NOT EXISTS loan_requests (
                request_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                object_id TEXT NOT NULL,
                quantity INTEGER NOT NULL CHECK(quantity > 0),
                engine_id TEXT,
                project_number TEXT,
                lending_date TEXT NOT NULL,
                return_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'requested',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                note TEXT,
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(object_id) REFERENCES objects(object_id)
            );

            CREATE TABLE IF NOT EXISTS consumable_reports (
                report_id INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id TEXT NOT NULL,
                quantity INTEGER,
                reported_by TEXT,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(object_id) REFERENCES objects(object_id)
            );

            CREATE TABLE IF NOT EXISTS system_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS user_groups (
                group_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                department TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            """
        )
        columns = [column["name"] for column in db.execute("PRAGMA table_info(objects)").fetchall()]
        missing_columns = {
            "item_type": "TEXT",
            "description": "TEXT",
            "supplier_article_number": "TEXT",
            "storage_location_2": "TEXT",
            "belongs_to_instrument": "TEXT",
            "device": "TEXT",
            "belongs_to": "TEXT",
            "last_changed": "TEXT",
            "search_words": "TEXT",
            "tray_for": "TEXT",
            "lift_tray": "TEXT",
            "is_consumable": "INTEGER NOT NULL DEFAULT 0",
            "image_data": "TEXT",
        }
        for column_name, column_type in missing_columns.items():
            if column_name not in columns:
                db.execute(f"ALTER TABLE objects ADD COLUMN {column_name} {column_type}")

        user_columns = [column["name"] for column in db.execute("PRAGMA table_info(users)").fetchall()]
        missing_user_columns = {
            "first_name": "TEXT",
            "last_name": "TEXT",
            "email": "TEXT",
            "phone": "TEXT",
            "company": "TEXT",
            "alias": "TEXT",
            "department_name": "TEXT",
            "rfid_code": "TEXT",
            "role": "TEXT NOT NULL DEFAULT 'operator'",
            "created_at": "TEXT",
            "updated_at": "TEXT",
            "privacy_notice_acknowledged_at": "TEXT",
            "borrow_override": "INTEGER NOT NULL DEFAULT 0",
        }
        for column_name, column_type in missing_user_columns.items():
            if column_name not in user_columns:
                db.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")

        loan_columns = [column["name"] for column in db.execute("PRAGMA table_info(loans)").fetchall()]
        missing_loan_columns = {
            "engine_id": "TEXT",
            "project_number": "TEXT",
            "loan_request_id": "INTEGER",
            "last_reminder_sent_at": "TEXT",
            "returned_quantity": "INTEGER NOT NULL DEFAULT 0 CHECK(returned_quantity >= 0 AND returned_quantity <= quantity)",
        }
        for column_name, column_type in missing_loan_columns.items():
            if column_name not in loan_columns:
                db.execute(f"ALTER TABLE loans ADD COLUMN {column_name} {column_type}")

        if "returned_quantity" not in loan_columns:
            db.execute("UPDATE loans SET returned_quantity = quantity WHERE status = 'returned'")
            db.execute("""INSERT INTO loan_returns (loan_id, quantity, returned_at)
                          SELECT loan_id, quantity, COALESCE(return_time, checkout_time)
                          FROM loans WHERE status = 'returned'""")

        request_columns = [column["name"] for column in db.execute("PRAGMA table_info(loan_requests)").fetchall()]
        missing_request_columns = {
            "pickup_ready_email_sent_at": "TEXT",
            "request_group_id": "INTEGER",
        }
        for column_name, column_type in missing_request_columns.items():
            if column_name not in request_columns:
                db.execute(f"ALTER TABLE loan_requests ADD COLUMN {column_name} {column_type}")

        group_columns = [column["name"] for column in db.execute("PRAGMA table_info(user_groups)").fetchall()]
        missing_group_columns = {
            "department": "TEXT",
        }
        for column_name, column_type in missing_group_columns.items():
            if column_name not in group_columns:
                db.execute(f"ALTER TABLE user_groups ADD COLUMN {column_name} {column_type}")

        legacy_new_job_message = (
            "Ett nytt lånejobb har skapats.\n\n"
            "Användare: {user_name}\n"
            "Objekt: {object_name} ({object_id})\n"
            "Antal: {quantity}\n"
            "Utlåningsdatum: {lending_date}\n"
            "Returdatum: {return_date}"
        )
        formatted_new_job_message = (
            "NY LÅNEFÖRFRÅGAN\n\n"
            "Förfrågan: #{request_id}\n"
            "Användare: {user_name}\n"
            "Utlåningsdatum: {lending_date}\n"
            "Återlämningsdatum: {return_date}\n\n"
            "ARTIKLAR ({article_count})\n"
            "{object_list}\n\n"
            "Totalt antal: {quantity}"
        )
        db.execute(
            """UPDATE system_settings SET value = ?, updated_at = datetime('now', 'localtime')
               WHERE key = 'message_new_job_body' AND trim(value) = ?""",
            (formatted_new_job_message, legacy_new_job_message),
        )

        status_replacements = (
            ("L?g niv?", "Låg nivå"),
            ("L\u00c3\u00a5g niv\u00c3\u00a5", "Låg nivå"),
            ("Tillg?nglig", "Tillgänglig"),
            ("Tillg\u00c3\u00a4nglig", "Tillgänglig"),
        )
        db.executemany(
            "UPDATE objects SET status = ? WHERE status = ?",
            [(replacement, broken) for broken, replacement in status_replacements],
        )

        db.execute(
            """
            INSERT OR IGNORE INTO user_groups (name, department, created_at, updated_at)
            SELECT trim(department_name), trim(COALESCE(MAX(department), '')), datetime('now', 'localtime'), datetime('now', 'localtime')
            FROM users
            WHERE department_name IS NOT NULL
              AND trim(department_name) != ''
            GROUP BY trim(department_name)
            """
        )
        db.execute(
            """
            UPDATE user_groups
            SET department = (
                SELECT trim(COALESCE(MAX(users.department), ''))
                FROM users
                WHERE lower(users.department_name) = lower(user_groups.name)
                  AND trim(COALESCE(users.department, '')) != ''
            )
            WHERE trim(COALESCE(department, '')) = ''
              AND EXISTS (
                SELECT 1 FROM users
                WHERE lower(users.department_name) = lower(user_groups.name)
                  AND trim(COALESCE(users.department, '')) != ''
              )
            """
        )


def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as db:
        return [dict(row) for row in db.execute(query, params).fetchall()]


def row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as db:
        result = db.execute(query, params).fetchone()
        return dict(result) if result else None
