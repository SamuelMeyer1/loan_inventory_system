"""Explicit, preview-first privacy operations; never run at application startup."""
from __future__ import annotations

from datetime import datetime, timedelta
import json

from backend.database import connect

FIELDS = ("controller", "contact", "purpose", "lawful_basis", "loan_days", "event_days")


def policy():
    with connect() as db:
        values = {r["key"]: r["value"] for r in db.execute("SELECT key, value FROM privacy_settings")}
    result = {field: values.get(field, "") for field in FIELDS}
    result["configured"] = all(result.values())
    return result


def save_policy(payload):
    values = {field: str(payload.get(field, "")).strip() for field in FIELDS}
    if any(not value or len(value) > 2000 for value in values.values()):
        raise ValueError("Fyll i alla policyfält, högst 2000 tecken per fält.")
    for field in ("loan_days", "event_days"):
        if not values[field].isdigit() or not 1 <= int(values[field]) <= 36500:
            raise ValueError("Gallringstider måste vara 1–36500 dagar och beslutade av verksamheten.")
    with connect() as db:
        db.executemany("INSERT INTO privacy_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", values.items())
        audit(db, "Dataskyddspolicy uppdaterad")
    return policy()


def audit(db, message):
    db.execute("INSERT INTO events (event_time, event_type, message) VALUES (?, 'privacy', ?)",
               (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message))


def _subject(db, user_id):
    user = db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if user is None:
        raise ValueError("Användaren hittades inte.")
    return dict(user)


def _legacy_events(db, user):
    # Old logs have no subject relation. This is a best-effort search, not a
    # claim that all historical personal data can be identified automatically.
    tokens = {str(user.get(k) or "").strip().casefold() for k in
              ("user_id", "name", "email", "phone", "alias", "rfid_code")}
    tokens.discard("")
    return [dict(r) for r in db.execute("SELECT * FROM events")
            if any(token in r["message"].casefold() for token in tokens)]


def export_subject(user_id):
    with connect() as db:
        user = _subject(db, user_id)
        return {"user": user,
                "loans": [dict(r) for r in db.execute("SELECT * FROM loans WHERE user_id = ?", (user_id,))],
                "requests": [dict(r) for r in db.execute("SELECT * FROM loan_requests WHERE user_id = ?", (user_id,))],
                "accounts": [dict(r) for r in db.execute("SELECT username, role FROM access_accounts WHERE user_id = ?", (user_id,))],
                "security_audit": [dict(r) for r in db.execute("SELECT * FROM security_audit WHERE user_id = ?", (user_id,))],
                "legacy_events_for_manual_review": _legacy_events(db, user),
                "scope": "Aktuell databas. Granska äldre fritext, säkerhetskopior, exporter, mejl och Git-historik separat. Loggträffar kan avse andra personer och måste granskas före utlämnande."}


def erase_subject(user_id, apply=False):
    with connect() as db:
        db.execute("PRAGMA secure_delete = ON")
        db.execute("BEGIN IMMEDIATE")
        user = _subject(db, user_id)
        active = db.execute("SELECT COUNT(*) FROM loans WHERE user_id = ? AND (status != 'returned' OR return_time IS NULL)", (user_id,)).fetchone()[0]
        pending = db.execute("SELECT COUNT(*) FROM loan_requests WHERE user_id = ? AND status != 'stocked'", (user_id,)).fetchone()[0]
        events = _legacy_events(db, user)
        counts = {table: db.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (user_id,)).fetchone()[0]
                  for table in ("loans", "loan_requests", "access_accounts")}
        result = {"counts": {**counts, "users": 1, "legacy_events_to_redact": len(events)},
                  "blocked": bool(active or pending), "applied": False,
                  "warning": "Äldre fritext och externa kopior måste granskas separat. Loggträffar maskeras i sin helhet och kan innehålla andra personers uppgifter."}
        if not apply:
            return result
        if result["blocked"]:
            raise ValueError("Avsluta aktiva lån och lagerför alla förfrågningar före radering. Verksamheten måste bedöma rätten till radering.")
        # Explicit deletion removes the current subject rows, rather than
        # claiming that reversible pseudonyms are anonymous.
        db.execute("DELETE FROM access_accounts WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM loans WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM loan_requests WHERE user_id = ?", (user_id,))
        db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        db.execute("UPDATE security_audit SET actor='removed', user_id=NULL WHERE user_id=?", (user_id,))
        db.executemany("UPDATE events SET message = 'Äldre loggtext maskerad vid dataskyddsåtgärd' WHERE event_id = ?",
                       [(event["event_id"],) for event in events])
        audit(db, "Registerposter raderade efter uttrycklig begäran")
        result["applied"] = True
        return result


def retention(apply=False, now=None):
    settings = policy()
    if not settings["configured"]:
        raise ValueError("Dokumentera beslutad dataskyddspolicy och gallringstider först.")
    today = now or datetime.now()
    loan_cutoff = (today-timedelta(days=int(settings["loan_days"]))).strftime("%Y-%m-%d %H:%M:%S")
    event_cutoff = (today-timedelta(days=int(settings["event_days"]))).strftime("%Y-%m-%d %H:%M:%S")
    with connect() as db:
        db.execute("PRAGMA secure_delete = ON")
        db.execute("BEGIN IMMEDIATE")
        # Do not purge loans belonging to an unfinished request group.
        requests = [r[0] for r in db.execute("""SELECT r.request_id FROM loan_requests r
          WHERE r.status = 'stocked' AND r.updated_at < ?
          AND NOT EXISTS (SELECT 1 FROM loan_requests s
             WHERE COALESCE(s.request_group_id,s.request_id)=COALESCE(r.request_group_id,r.request_id)
             AND (s.status != 'stocked' OR s.updated_at >= ?))""", (loan_cutoff, loan_cutoff))]
        request_set = set(requests)
        loans = [r["loan_id"] for r in db.execute("SELECT loan_id, loan_request_id FROM loans WHERE status='returned' AND return_time < ?", (loan_cutoff,))
                 if r["loan_request_id"] is None or r["loan_request_id"] in request_set]
        loan_set = set(loans)
        requests = [request_id for request_id in requests if all(r[0] in loan_set for r in db.execute("SELECT loan_id FROM loans WHERE loan_request_id = ?", (request_id,)))]
        events = [r[0] for r in db.execute("SELECT event_id FROM events WHERE event_time < ?", (event_cutoff,))]
        access_events = [r[0] for r in db.execute("SELECT audit_id FROM security_audit WHERE event_time < ?", (event_cutoff,))]
        result = {"counts": {"loans": len(loans), "loan_requests": len(requests), "events": len(events), "security_audit": len(access_events)}, "applied": False,
                  "scope": "Avslutade lån/förfrågningar och gamla loggar i aktuell databas. Användarprofiler, externa kopior och fritext gallras separat."}
        if apply:
            for table, key, ids in (("loans", "loan_id", loans), ("loan_requests", "request_id", requests), ("events", "event_id", events), ("security_audit", "audit_id", access_events)):
                db.executemany(f"DELETE FROM {table} WHERE {key} = ?", [(value,) for value in ids])
            audit(db, "Gallring utförd: " + json.dumps(result["counts"]))
            result["applied"] = True
        return result
