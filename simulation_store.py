"""Identify and exclusively use launcher-owned simulation databases."""
from __future__ import annotations

from contextlib import closing, contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Iterator
import uuid


APPLICATION_ID = 0x4C495344


def simulation_path(storage: Path) -> Path:
    return storage / "simulations" / "demo.db"


@contextmanager
def simulation_guard(path: Path) -> Iterator[None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(str(path) + ".lock", timeout=0)) as lock:
        try:
            lock.execute("BEGIN EXCLUSIVE")
        except sqlite3.OperationalError as error:
            raise ValueError("Simuleringsdatabasen används eller kan inte låsas. Stoppa simuleringen först.") from error
        try:
            yield
        finally:
            lock.rollback()


def validate_simulation(path: Path) -> None:
    if not path.is_file() or path.is_symlink() or path.stat().st_nlink != 1:
        raise ValueError("Simulering kräver en separat demodatabas skapad av startfönstret.")
    try:
        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
            marker = db.execute("PRAGMA application_id").fetchone()[0]
            metadata = db.execute("SELECT seeded FROM simulation_metadata WHERE id=1").fetchone()
            if marker != APPLICATION_ID or metadata is None or metadata[0] not in (0, 1):
                raise ValueError("Databasen är inte märkt som en separat simuleringsdatabas.")
    except sqlite3.DatabaseError as error:
        raise ValueError("Databasen är inte en giltig simuleringsdatabas. Ingen data har ändrats.") from error


def is_simulation(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size == 0:
        return False
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID


def prepare_simulation(storage: Path) -> Path:
    path = simulation_path(storage)
    with simulation_guard(path):
        if not path.exists():
            path.touch(exist_ok=False)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute(f"PRAGMA application_id={APPLICATION_ID}")
                db.execute("""CREATE TABLE simulation_metadata (
                    id INTEGER PRIMARY KEY CHECK(id=1),
                    seeded INTEGER NOT NULL CHECK(seeded IN (0,1)),
                    generated_at TEXT
                )""")
                db.execute("INSERT INTO simulation_metadata(id,seeded) VALUES (1,0)")
        validate_simulation(path)
    return path


def reset_simulation(storage: Path) -> Path | None:
    path = simulation_path(storage)
    with simulation_guard(path):
        if not path.exists():
            return None
        validate_simulation(path)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"demo.before-reset-{timestamp}-{uuid.uuid4().hex[:8]}.db")
        # Renaming preserves the entire previous demo; the next start creates a fresh one.
        path.rename(backup)
        return backup
