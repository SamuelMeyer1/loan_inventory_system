from __future__ import annotations

from typing import Any

from backend.database import row
from hardware.rfid.reader import read_card_uid


def read_user_card() -> dict[str, Any]:
    uid = read_card_uid()
    user = row("SELECT * FROM users WHERE active = 1 AND lower(rfid_code) = lower(?)", (uid,))
    return {"uid": uid, "user": user}
