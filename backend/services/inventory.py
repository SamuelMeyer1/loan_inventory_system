from __future__ import annotations

from typing import Any

from backend.database import connect, row, rows
from backend.services.common import log_event, now_text, object_status, optional_text, is_truthy


def with_description_images(objects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    images_by_description: dict[str, str] = {}
    for item in objects:
        description = str(item.get("description") or "").strip().lower()
        image_data = str(item.get("image_data") or "").strip()
        if description and image_data and description not in images_by_description:
            images_by_description[description] = image_data

    for item in objects:
        description = str(item.get("description") or "").strip().lower()
        image_data = str(item.get("image_data") or "").strip()
        shared_image_data = images_by_description.get(description, "") if description else ""
        item["display_image_data"] = image_data or shared_image_data
        item["shared_image_data"] = "" if image_data else shared_image_data
    return objects


def list_objects(search: str = "", category: str = "Alla", status: str = "Alla") -> list[dict[str, Any]]:
    query = "SELECT * FROM objects WHERE 1 = 1"
    params: list[Any] = []

    if search.strip():
        term = f"%{search.strip()}%"
        query += """
        AND (
            object_id LIKE ?
            OR name LIKE ?
            OR article_number LIKE ?
            OR supplier_article_number LIKE ?
            OR description LIKE ?
            OR search_words LIKE ?
            OR location LIKE ?
            OR storage_location_2 LIKE ?
            OR lift_tray LIKE ?
        )
        """
        params.extend([term, term, term, term, term, term, term, term, term])
    if category != "Alla":
        query += " AND category = ?"
        params.append(category)
    if status != "Alla":
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY category, name"
    return with_description_images(rows(query, tuple(params)))


def search_objects(term: str, limit: int = 8) -> list[dict[str, Any]]:
    term = term.strip()
    if not term:
        return []
    like_term = f"%{term}%"
    return with_description_images(rows(
        """
        SELECT *
        FROM objects
        WHERE object_id LIKE ?
           OR name LIKE ?
           OR category LIKE ?
           OR item_type LIKE ?
           OR description LIKE ?
           OR article_number LIKE ?
           OR supplier_article_number LIKE ?
           OR location LIKE ?
           OR storage_location_2 LIKE ?
           OR tornado_id LIKE ?
           OR device LIKE ?
           OR search_words LIKE ?
           OR lift_tray LIKE ?
        ORDER BY
            CASE
                WHEN name LIKE ? THEN 0
                WHEN object_id LIKE ? THEN 1
                ELSE 2
            END,
            name
        LIMIT ?
        """,
        (
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            like_term,
            limit,
        ),
    ))


def add_object(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    item_type = optional_text(payload, "item_type")
    description = optional_text(payload, "description")
    article_number = str(payload.get("article_number", "")).strip()
    supplier_article_number = optional_text(payload, "supplier_article_number")
    location = str(payload.get("location", "")).strip()
    storage_location_2 = optional_text(payload, "storage_location_2")
    tornado_id = str(payload.get("tornado_id", "")).strip()
    door_id = str(payload.get("door_id", "")).strip()
    belongs_to_instrument = optional_text(payload, "belongs_to_instrument")
    device = optional_text(payload, "device")
    belongs_to = optional_text(payload, "belongs_to")
    last_changed = optional_text(payload, "last_changed")
    search_words = optional_text(payload, "search_words")
    tray_for = optional_text(payload, "tray_for")
    lift_tray = optional_text(payload, "lift_tray")
    total_quantity = int(payload.get("total_quantity", 0))
    available_quantity = int(payload.get("available_quantity", total_quantity))
    min_quantity = int(payload.get("min_quantity", 0))
    is_consumable = 1 if is_truthy(payload.get("is_consumable")) else 0
    image_data = str(payload.get("image_data", "")).strip()

    if not object_id:
        raise ValueError("Ange objekt-ID.")
    if not name:
        raise ValueError("Ange namn.")
    if not category:
        raise ValueError("Ange kategori.")
    if not location:
        raise ValueError("Ange plats.")
    if not tornado_id:
        raise ValueError("Ange Tornado/skåp.")
    if not door_id:
        raise ValueError("Ange dörr/fack.")
    if total_quantity < 0 or available_quantity < 0 or min_quantity < 0:
        raise ValueError("Antal får inte vara negativt.")
    if available_quantity > total_quantity:
        raise ValueError("Tillgängligt antal kan inte vara större än totalt antal.")
    if row("SELECT object_id FROM objects WHERE object_id = ?", (object_id,)):
        raise ValueError("Det finns redan ett objekt med det ID:t.")

    status = object_status(available_quantity, min_quantity)
    with connect() as db:
        db.execute(
            """
            INSERT INTO objects (
                object_id, name, category, item_type, description, article_number, supplier_article_number,
                location, storage_location_2, tornado_id, door_id, belongs_to_instrument, device,
                belongs_to, last_changed, search_words, tray_for, lift_tray,
                total_quantity, available_quantity, min_quantity, status, is_consumable, image_data
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                object_id,
                name,
                category,
                item_type,
                description,
                article_number,
                supplier_article_number,
                location,
                storage_location_2,
                tornado_id,
                door_id,
                belongs_to_instrument,
                device,
                belongs_to,
                last_changed,
                search_words,
                tray_for,
                lift_tray,
                total_quantity,
                available_quantity,
                min_quantity,
                status,
                is_consumable,
                image_data or None,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt skapat: {name} ({object_id})"),
        )

    return {"object_id": object_id}


def update_object(payload: dict[str, Any]) -> dict[str, Any]:
    object_id = str(payload.get("object_id", "")).strip()
    existing = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if existing is None:
        raise ValueError("Objektet hittades inte.")

    name = str(payload.get("name", "")).strip()
    category = str(payload.get("category", "")).strip()
    item_type = optional_text(payload, "item_type")
    description = optional_text(payload, "description")
    article_number = str(payload.get("article_number", "")).strip()
    supplier_article_number = optional_text(payload, "supplier_article_number")
    location = str(payload.get("location", "")).strip()
    storage_location_2 = optional_text(payload, "storage_location_2")
    tornado_id = str(payload.get("tornado_id", "")).strip()
    door_id = str(payload.get("door_id", "")).strip()
    belongs_to_instrument = optional_text(payload, "belongs_to_instrument")
    device = optional_text(payload, "device")
    belongs_to = optional_text(payload, "belongs_to")
    last_changed = optional_text(payload, "last_changed")
    search_words = optional_text(payload, "search_words")
    tray_for = optional_text(payload, "tray_for")
    lift_tray = optional_text(payload, "lift_tray")
    total_quantity = int(payload.get("total_quantity", 0))
    available_quantity = int(payload.get("available_quantity", total_quantity))
    min_quantity = int(payload.get("min_quantity", 0))
    is_consumable = 1 if is_truthy(payload.get("is_consumable")) else 0
    image_data = payload.get("image_data", existing.get("image_data"))
    remove_image = bool(payload.get("remove_image", False))

    if not name:
        raise ValueError("Ange namn.")
    if not category:
        raise ValueError("Ange kategori.")
    if not location:
        raise ValueError("Ange plats.")
    if not tornado_id:
        raise ValueError("Ange Tornado/skåp.")
    if not door_id:
        raise ValueError("Ange dörr/fack.")
    if total_quantity < 0 or available_quantity < 0 or min_quantity < 0:
        raise ValueError("Antal får inte vara negativt.")
    if available_quantity > total_quantity:
        raise ValueError("Tillgängligt antal kan inte vara större än totalt antal.")

    if remove_image:
        image_data = None
    elif isinstance(image_data, str):
        image_data = image_data.strip() or existing.get("image_data")

    status = object_status(available_quantity, min_quantity)
    with connect() as db:
        db.execute(
            """
            UPDATE objects
            SET name = ?,
                category = ?,
                item_type = ?,
                description = ?,
                article_number = ?,
                supplier_article_number = ?,
                location = ?,
                storage_location_2 = ?,
                tornado_id = ?,
                door_id = ?,
                belongs_to_instrument = ?,
                device = ?,
                belongs_to = ?,
                last_changed = ?,
                search_words = ?,
                tray_for = ?,
                lift_tray = ?,
                total_quantity = ?,
                available_quantity = ?,
                min_quantity = ?,
                status = ?,
                is_consumable = ?,
                image_data = ?
            WHERE object_id = ?
            """,
            (
                name,
                category,
                item_type,
                description,
                article_number,
                supplier_article_number,
                location,
                storage_location_2,
                tornado_id,
                door_id,
                belongs_to_instrument,
                device,
                belongs_to,
                last_changed,
                search_words,
                tray_for,
                lift_tray,
                total_quantity,
                available_quantity,
                min_quantity,
                status,
                is_consumable,
                image_data,
                object_id,
            ),
        )
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt uppdaterat: {name} ({object_id})"),
        )

    return {"object_id": object_id}


def delete_object(object_id: str) -> dict[str, Any]:
    object_id = object_id.strip()
    if not object_id:
        raise ValueError("Ange objekt-ID.")

    existing = row("SELECT * FROM objects WHERE object_id = ?", (object_id,))
    if existing is None:
        raise ValueError("Objektet hittades inte.")

    active_loan = row("SELECT loan_id FROM loans WHERE object_id = ? AND status = 'active'", (object_id,))
    if active_loan:
        raise ValueError("Objektet har aktiva lån och kan inte tas bort.")

    with connect() as db:
        db.execute("DELETE FROM loans WHERE object_id = ? AND status != 'active'", (object_id,))
        db.execute("DELETE FROM objects WHERE object_id = ?", (object_id,))
        db.execute(
            "INSERT INTO events (event_time, event_type, message) VALUES (?, ?, ?)",
            (now_text(), "object", f"Objekt borttaget: {existing['name']} ({object_id})"),
        )
    return {"object_id": object_id}
