from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
DATABASE_PATH = DATA_DIR / "inventory.db"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database() -> None:
    with connect() as db:
        db.executescript(
            """
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
                role TEXT NOT NULL DEFAULT 'operator',
                created_at TEXT,
                updated_at TEXT,
                active INTEGER NOT NULL DEFAULT 1
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
            "role": "TEXT NOT NULL DEFAULT 'operator'",
            "created_at": "TEXT",
            "updated_at": "TEXT",
        }
        for column_name, column_type in missing_user_columns.items():
            if column_name not in user_columns:
                db.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")

        loan_columns = [column["name"] for column in db.execute("PRAGMA table_info(loans)").fetchall()]
        missing_loan_columns = {
            "engine_id": "TEXT",
            "project_number": "TEXT",
            "loan_request_id": "INTEGER",
        }
        for column_name, column_type in missing_loan_columns.items():
            if column_name not in loan_columns:
                db.execute(f"ALTER TABLE loans ADD COLUMN {column_name} {column_type}")


def rows(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as db:
        return [dict(row) for row in db.execute(query, params).fetchall()]


def row(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connect() as db:
        result = db.execute(query, params).fetchone()
        return dict(result) if result else None
