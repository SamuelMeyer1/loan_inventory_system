import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from backend import database
from backend.services import inventory, loans, notifications, privacy, stats


class PartialReturnsTest(unittest.TestCase):
    def setUp(self):
        workspace = Path(__file__).resolve().parents[1]
        temporary = tempfile.TemporaryDirectory(prefix=".return-tests-", dir=workspace)
        self.addCleanup(temporary.cleanup)
        replacement = patch.object(database, "DATABASE_PATH", Path(temporary.name) / "test.db")
        replacement.start()
        self.addCleanup(replacement.stop)
        for name, value in (("get_system_settings", {"max_loan_days": "90"}), ("open_door", None),
                            ("notify_rule_recipients", None), ("send_email", None)):
            mocked = patch.object(loans, name, return_value=value)
            mocked.start()
            self.addCleanup(mocked.stop)
        database.initialize_database()
        with database.connect() as db:
            db.executemany("INSERT INTO users (user_id, name) VALUES (?, ?)", [("u", "Borrower"), ("v", "Other")])
            for object_id in ("A", "B"):
                db.execute("""INSERT INTO objects (object_id, name, category, location, tornado_id, door_id,
                    total_quantity, available_quantity, min_quantity, status)
                    VALUES (?, ?, 'Tool', 'Shelf', 'Store', 'Door', 10, 10, 0, 'Tillgänglig')""", (object_id, object_id))
        self.loan_id = self.checkout("A", 5)

    def checkout(self, object_id, quantity):
        return loans.checkout({"object_id": object_id, "quantity": quantity, "user_id": "u",
                               "lending_date": "2026-10-20", "due_time": "2026-10-25"})["loan_id"]

    def payload(self, quantity=2, damaged=0, expected=0, loan_id=None):
        return {"user_id": "u", "items": [{"loan_id": loan_id or self.loan_id, "quantity": quantity,
            "damaged_quantity": damaged, "damage_description": "Broken housing" if damaged else "",
            "expected_returned_quantity": expected}]}

    def assert_stock(self, available, total=10, outstanding=0, quarantine=0):
        item = database.row("SELECT * FROM objects WHERE object_id = 'A'")
        self.assertEqual((item["available_quantity"], item["total_quantity"]), (available, total))
        actual_outstanding = database.row("""SELECT COALESCE(SUM(quantity-returned_quantity), 0) AS n
            FROM loans WHERE object_id='A' AND status='active'""")["n"]
        actual_quarantine = sum(item["damaged_quantity"] for item in loans.list_damaged_returns() if item["object_id"] == "A")
        self.assertEqual((actual_outstanding, actual_quarantine), (outstanding, quarantine))
        self.assertEqual(available + outstanding + quarantine, total)

    def test_partial_damage_summary_and_legacy_remaining(self):
        result = loans.return_item(self.payload(3, 1))
        self.assertEqual((result["returned_quantity"], result["damaged_quantity"], result["remaining_quantity"]), (3, 1, 2))
        self.assert_stock(7, outstanding=2, quarantine=1)
        active = loans.list_active_loans()[0]
        self.assertEqual((active["quantity"], active["returned_quantity"], active["remaining_quantity"]), (5, 3, 2))
        self.assertIsNone(active["return_time"])
        self.assertEqual(stats.dashboard_stats()["loaned_quantity"], 2)
        self.assertEqual(stats.statistics_data()["top_borrowers"][0]["value"], 2)
        self.assertEqual(inventory.list_objects()[0]["quarantined_quantity"], 1)
        result = loans.return_item({"user_id": "u", "loan_ids": [self.loan_id, self.loan_id]})
        self.assertEqual(result["returned_quantity"], 2)
        self.assertEqual(loans.list_active_loans(), [])
        self.assert_stock(9, quarantine=1)
        self.assertEqual(sum(r["quantity"] for r in stats.statistics_data()["returns_per_month"]), 5)

    def test_repeat_partial_overreturn_and_wrong_owner_are_atomic(self):
        payload = self.payload()
        loans.return_item(payload)
        for invalid in (payload, self.payload(4, expected=2), {**self.payload(expected=2), "user_id": "v"}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                loans.return_item(invalid)
        self.assert_stock(7, outstanding=3)
        self.assertEqual(len(database.rows("SELECT * FROM loan_returns")), 1)

    def test_invalid_second_row_rolls_back_all_changes(self):
        second = self.checkout("B", 1)
        payload = self.payload(2, 1)
        payload["items"] += self.payload(2, loan_id=second)["items"]
        with self.assertRaises(ValueError):
            loans.return_item(payload)
        self.assert_stock(5, outstanding=5)
        self.assertEqual(database.rows("SELECT * FROM loan_returns"), [])

    def test_strict_quantities_and_damage_description(self):
        invalid = [
            ("quantity", 0), ("quantity", -1), ("quantity", True), ("quantity", 1.5),
            ("quantity", "1.0"), ("quantity", None), ("damaged_quantity", -1),
            ("damaged_quantity", 3), ("expected_returned_quantity", None),
            ("expected_returned_quantity", True), ("loan_id", False),
            ("loan_id", 2**64),
            ("damage_description", "Unneeded"), ("damage_description", {}),
        ]
        for field, value in invalid:
            payload = self.payload()
            payload["items"][0][field] = value
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                loans.return_item(payload)
        for description in ("", "  ", "x" * 2001):
            payload = self.payload(2, 1)
            payload["items"][0]["damage_description"] = description
            with self.assertRaises(ValueError):
                loans.return_item(payload)
        duplicate = self.payload()
        duplicate["items"] *= 2
        with self.assertRaises(ValueError):
            loans.return_item(duplicate)
        with self.assertRaises(ValueError):
            loans.return_item({"user_id": "u", "loan_ids": [2**64]})
        self.assert_stock(5, outstanding=5)

    def run_concurrently(self, action):
        barrier = threading.Barrier(2)
        def invoke(_):
            barrier.wait(timeout=5)
            try:
                action()
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as executor:
            return sorted(executor.map(invoke, range(2)))

    def test_concurrent_partial_return_applies_once(self):
        self.assertEqual(self.run_concurrently(lambda: loans.return_item(self.payload(2, 1))), [False, True])
        self.assert_stock(6, outstanding=3, quarantine=1)
        self.assertEqual(len(database.rows("SELECT * FROM loan_returns")), 1)

    def test_repair_restores_stock_and_cannot_repeat(self):
        return_id = loans.return_item(self.payload(5, 2))["items"][0]["return_id"]
        self.assert_stock(8, quarantine=2)
        payload = {"return_id": return_id, "resolution": "repaired", "confirmed": True}
        self.assertEqual(self.run_concurrently(lambda: loans.resolve_damaged_return(payload)), [False, True])
        self.assert_stock(10)
        with self.assertRaises(ValueError):
            loans.resolve_damaged_return({**payload, "resolution": "discarded"})

    def test_discard_reduces_total_not_available_and_requires_confirmation(self):
        return_id = loans.return_item(self.payload(5, 2))["items"][0]["return_id"]
        payload = {"return_id": return_id, "resolution": "discarded"}
        with self.assertRaises(ValueError):
            loans.resolve_damaged_return(payload)
        loans.resolve_damaged_return({**payload, "confirmed": True})
        self.assert_stock(8, total=8)
        with self.assertRaises(ValueError):
            loans.resolve_damaged_return({**payload, "confirmed": True})

    def test_quarantined_stock_cannot_be_borrowed_edited_or_deleted(self):
        loans.return_item(self.payload(5, 5))
        with self.assertRaises(ValueError):
            self.checkout("A", 6)
        item = database.row("SELECT * FROM objects WHERE object_id='A'")
        with self.assertRaises(ValueError):
            inventory.update_object({**item, "available_quantity": 10})
        with self.assertRaises(ValueError):
            inventory.update_object({**item, "total_quantity": 5})
        with self.assertRaises(ValueError):
            inventory.delete_object("A")
        self.assert_stock(5, quarantine=5)

    def test_partial_job_return_and_stocked_damage_guard(self):
        request = loans.create_loan_request({"user_id": "u", "object_id": "B", "quantity": 4,
            "lending_date": "2026-10-20", "due_time": "2026-10-25"})["request_id"]
        loans.update_loan_request_status({"request_id": request, "status": "loaned"})
        loan_id = database.row("SELECT loan_id FROM loans WHERE loan_request_id=?", (request,))["loan_id"]
        loans.return_item(self.payload(2, 1, loan_id=loan_id))
        self.assertEqual(database.row("SELECT status FROM loan_requests WHERE request_id=?", (request,))["status"], "loaned")
        loans.update_loan_request_group_status({"request_group_id": request, "status": "returned"})
        self.assertEqual(database.row("SELECT available_quantity FROM objects WHERE object_id='B'")["available_quantity"], 9)
        for action in (loans.update_loan_request_status, loans.update_loan_request_group_status):
            with self.assertRaises(ValueError):
                action({"request_id": request, "request_group_id": request, "status": "stocked"})
        with self.assertRaises(ValueError):
            loans.delete_loan_request(request)
        loans.resolve_damaged_return({"return_id": loans.list_damaged_returns()[0]["return_id"],
                                     "resolution": "repaired", "confirmed": True})
        loans.update_loan_request_group_status({"request_group_id": request, "status": "stocked"})
        self.assertEqual(database.row("SELECT available_quantity FROM objects WHERE object_id='B'")["available_quantity"], 10)

    def test_identifier_returns_only_remaining_and_checks_optional_owner(self):
        loans.return_item(self.payload(2))
        with self.assertRaises(ValueError):
            loans.return_item({"identifier": str(self.loan_id), "user_id": "v"})
        loans.return_item({"identifier": "A"})
        self.assert_stock(10)
        with self.assertRaises(ValueError):
            loans.return_item({"identifier": str(self.loan_id)})

    def test_reminder_uses_remaining_quantity(self):
        loans.return_item(self.payload(2))
        with database.connect() as db:
            db.execute("UPDATE users SET email='test@example.invalid' WHERE user_id='u'")
        with patch.object(notifications, "get_system_settings", return_value={"smtp_use_tls": "1"}), \
                patch.object(notifications, "smtp_ready", return_value=True), \
                patch.object(notifications, "message_text", side_effect=lambda settings, key, values: str(values["quantity"])), \
                patch.object(notifications, "send_email", return_value=1) as send:
            notifications.send_loan_reminder(self.loan_id)
        self.assertEqual(send.call_args.args[1], "3")

    def test_legacy_request_link_keeps_partial_damage_guard(self):
        with database.connect() as db:
            cursor = db.execute("""INSERT INTO loan_requests
                (user_id, object_id, quantity, lending_date, return_date, status, created_at, updated_at)
                VALUES ('u','A',5,'2026-10-20','2026-10-25','loaned','2026-10-20','2026-10-20')""")
            request_id = cursor.lastrowid
        loans.return_item(self.payload(2, 1))
        self.assertEqual(database.row("SELECT loan_request_id FROM loans WHERE loan_id=?", (self.loan_id,))["loan_request_id"], request_id)
        loans.update_loan_request_status({"request_id": request_id, "status": "returned"})
        self.assert_stock(9, quarantine=1)
        with self.assertRaises(ValueError):
            loans.update_loan_request_status({"request_id": request_id, "status": "stocked"})
        other = self.checkout("A", 1)
        loans.update_loan_request_status({"request_id": request_id, "status": "returned"})
        self.assertEqual(database.row("SELECT status FROM loans WHERE loan_id=?", (other,))["status"], "active")
        self.assert_stock(8, outstanding=1, quarantine=1)

    def test_privacy_export_erase_and_retention_respect_quarantine(self):
        return_id = loans.return_item(self.payload(5, 1))["items"][0]["return_id"]
        self.assertEqual(len(privacy.export_subject("u")["returns_and_damage"]), 1)
        self.assertTrue(privacy.erase_subject("u")["blocked"])
        with self.assertRaises(ValueError):
            privacy.erase_subject("u", True)
        privacy.save_policy(dict(controller="Test", contact="Test", purpose="Test", lawful_basis="Test",
                                 loan_days="30", event_days="30"))
        self.assertEqual(privacy.retention(now=datetime(2030, 1, 1))["counts"]["loans"], 0)
        loans.resolve_damaged_return({"return_id": return_id, "resolution": "repaired", "confirmed": True})
        self.assertEqual(privacy.retention(now=datetime(2030, 1, 1))["counts"]["loan_returns"], 1)
        privacy.erase_subject("u", True)
        self.assertEqual(database.rows("SELECT * FROM loan_returns"), [])
        self.assert_stock(10)

    def test_retention_cascades_resolved_damage_after_resolution_retention(self):
        return_id = loans.return_item(self.payload(5, 1))["items"][0]["return_id"]
        loans.resolve_damaged_return({"return_id": return_id, "resolution": "discarded", "confirmed": True})
        privacy.save_policy(dict(controller="Test", contact="Test", purpose="Test", lawful_basis="Test",
                                 loan_days="30", event_days="30"))
        with database.connect() as db:
            db.execute("UPDATE loans SET return_time='2000-01-01'")
            db.execute("UPDATE loan_returns SET resolved_at='2029-12-30'")
        self.assertEqual(privacy.retention(now=datetime(2030, 1, 1))["counts"]["loans"], 0)
        privacy.retention(True, now=datetime(2030, 3, 1))
        self.assertEqual(database.rows("SELECT * FROM loan_returns"), [])
        self.assert_stock(9, total=9)

    def test_migration_preserves_partial_quantities_and_damage_idempotently(self):
        loans.return_item(self.payload(2, 1))
        for _ in range(2):
            database.initialize_database()
        self.assert_stock(6, outstanding=3, quarantine=1)
        self.assertEqual(len(database.rows("SELECT * FROM loan_returns")), 1)

    def test_legacy_schema_migration_backfills_completed_loans_once(self):
        active_id = self.checkout("B", 2)
        with database.connect() as db:
            db.execute("DROP TABLE loan_returns")
            db.execute("ALTER TABLE loans DROP COLUMN returned_quantity")
            db.execute("UPDATE loans SET status='returned', return_time='2026-10-21' WHERE loan_id=?", (self.loan_id,))
            db.execute("UPDATE objects SET available_quantity=10 WHERE object_id='A'")
        for _ in range(2):
            database.initialize_database()
        loan = database.row("SELECT * FROM loans WHERE loan_id=?", (self.loan_id,))
        self.assertEqual(loan["returned_quantity"], 5)
        active = database.row("SELECT * FROM loans WHERE loan_id=?", (active_id,))
        self.assertEqual((active["returned_quantity"], active["status"]), (0, "active"))
        self.assertEqual(len(database.rows("SELECT * FROM loan_returns")), 1)
        self.assert_stock(10)


if __name__ == "__main__":
    unittest.main()
