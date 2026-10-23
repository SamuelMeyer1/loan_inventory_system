"""Paths and upgrade safeguards for the installed Windows application."""
from __future__ import annotations

import ctypes
from contextlib import closing
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys
import time
import uuid

from app_version import VERSION

APP_MUTEX = "Local\\LoanInventorySystem.Running"
_mutex_handle = None


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def storage_directory() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "LoanInventoryLauncher"


def default_database() -> Path:
    root = storage_directory() if is_frozen() else Path(__file__).resolve().parent
    return root / "data" / "inventory.db"


def hold_installation_mutex() -> None:
    """Keep setup/uninstall from replacing binaries used by any bundled process."""
    global _mutex_handle
    if os.name != "nt" or _mutex_handle is not None:
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel.CreateMutexW.restype = ctypes.c_void_p
    _mutex_handle = kernel.CreateMutexW(None, False, APP_MUTEX)
    if not _mutex_handle:
        raise ctypes.WinError(ctypes.get_last_error())


def backup_before_migration(path: Path) -> Path | None:
    """Installed starts fail closed if a consistent pre-migration backup fails."""
    if not is_frozen() or not path.exists() or path.stat().st_size == 0:
        return None
    directory = path.parent / "backups"
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = directory / f"{path.stem[:24]}.before-{VERSION}-{timestamp}-{uuid.uuid4().hex[:8]}.db"
    target.touch(exist_ok=False)
    try:
        deadline = time.monotonic() + 30

        def progress(status: int, remaining: int, total: int) -> None:
            if time.monotonic() > deadline:
                raise TimeoutError("Säkerhetskopieringen tog för lång tid. Stoppa andra databasprocesser och försök igen.")

        with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(target)) as destination:
                source.backup(destination, pages=256, progress=progress)
                if destination.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                    raise sqlite3.DatabaseError("Säkerhetskopian klarade inte SQLite-kontrollen.")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target
