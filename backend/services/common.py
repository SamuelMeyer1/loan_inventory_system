from __future__ import annotations

from datetime import datetime
from typing import Any

from backend.database import connect


def now_text() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def object_status(available_quantity: int, min_quantity: int) -> str:
    if available_quantity <= 0:
        return "Slut"
    if available_quantity <= min_quantity:
        return "Låg nivå"
    return "Tillgänglig"


def is_truthy(value: Any) -> bool:
    return value in (True, 1, "1", "true", "yes", "on")


def is_consumable_object(item: dict[str, Any]) -> bool:
    if is_truthy(item.get("is_consumable")):
        return True
    searchable = " ".join(
        str(item.get(key) or "").lower()
        for key in ("category", "item_type", "description", "search_words", "name")
    )
    return "förbruk" in searchable or "forbruk" in searchable or "consumable" in searchable


def log_event(event_type: str, message: str) -> None:
    with connect() as db:
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), event_type, message),
        )


def open_door(tornado_id: str, door_id: str, reason: str) -> None:
    log_event("lock", f"{tornado_id} - Door {door_id} opened ({reason})")


def optional_text(payload: dict[str, Any], key: str) -> str:
    return str(payload.get(key, "") or "").strip()
