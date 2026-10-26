import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import database
from backend.services import notifications, users


class AdminRulesTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        replacement = patch.object(database, "DATABASE_PATH", Path(directory.name) / "test.db")
        replacement.start()
        self.addCleanup(replacement.stop)
        database.initialize_database()
        with database.connect() as db:
            db.execute("""INSERT INTO users (user_id, name, created_at)
                          VALUES ('old', 'Old test borrower', datetime('now', 'localtime', '-365 days'))""")
            db.execute("""INSERT INTO users (user_id, name, created_at)
                          VALUES ('new', 'New test borrower', datetime('now', 'localtime'))""")
            db.execute("INSERT INTO users (user_id, name) VALUES ('unknown', 'Missing history')")
            db.execute("""INSERT INTO objects (object_id, name, category, location, tornado_id, door_id,
                          total_quantity, available_quantity, min_quantity, status)
                          VALUES ('A', 'Test article', 'Test', 'Test', 'Test', '1', 2, 2, 0, 'Tillgänglig')""")
            db.executemany("""INSERT INTO access_accounts (username, salt, password_hash, role)
                              VALUES (?, 'unused', 'unused', 'admin')""", [("first",), ("second",)])

    def user(self, user_id="old"):
        return next(user for user in users.list_users() if user["user_id"] == user_id)

    def loan(self, days=400, status="returned"):
        with database.connect() as db:
            return db.execute("""INSERT INTO loans (user_id, object_id, quantity, checkout_time,
                                 due_time, return_time, status, returned_quantity)
                                 VALUES ('old', 'A', 1, datetime('now', 'localtime', ?),
                                         '2000-01-01', ?, ?, ?)""",
                              (f"-{days} days", "2000-01-02" if status == "returned" else None,
                               status, 1 if status == "returned" else 0)).lastrowid

    def event(self, kind="request"):
        with database.connect() as db:
            return db.execute("INSERT INTO events (event_time, event_type, message) VALUES ('2026-10-23', ?, 'private')",
                              (kind,)).lastrowid

    def test_defaults_and_inactivity_boundary_without_automatic_blocking(self):
        settings = notifications.get_system_settings()
        self.assertEqual(settings["inactive_user_days"], "365")
        self.assertEqual(settings["notify_admin_new_request"], "1")
        self.assertEqual(settings["notify_admin_loaned"], "0")
        self.assertEqual(self.user()["inactivity_warning"], 1)
        self.assertEqual(self.user()["active"], 1)
        self.assertEqual(self.user()["borrow_blocked"], 0)
        self.assertEqual(self.user("new")["inactivity_warning"], 0)
        self.assertEqual(self.user("unknown")["inactivity_warning"], 0)

    def test_settings_persist_and_apply_without_email_configuration(self):
        notifications.update_system_settings({"inactive_user_days": 400})
        database.initialize_database()
        self.assertEqual(notifications.get_system_settings()["inactive_user_days"], "400")
        self.assertEqual(self.user()["inactivity_warning"], 0)
        notifications.update_system_settings({"inactive_user_days": 300, "inactive_user_warning_enabled": False})
        self.assertEqual(self.user()["inactivity_warning"], 0)
        notifications.update_system_settings({"inactive_user_warning_enabled": True})
        self.assertEqual(self.user()["inactivity_warning"], 1)

    def test_borrower_edit_without_role_or_active_preserves_legacy_values(self):
        with database.connect() as db:
            db.execute("UPDATE users SET role='admin', active=0 WHERE user_id='old'")
        users.update_user({
            "user_id": "old", "first_name": "Old", "last_name": "Borrower",
            "email": "old@example.invalid",
        })
        borrower = database.row("SELECT role, active FROM users WHERE user_id='old'")
        self.assertEqual(borrower["role"], "admin")
        self.assertEqual(borrower["active"], 0)

    def test_invalid_rules_rejected_without_partial_save(self):
        for value in (0, -1, 36501, 1.5, "bad", "", None, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                notifications.update_system_settings({"inactive_user_days": value, "notify_admin_new_request": False})
            self.assertEqual(notifications.get_system_settings()["inactive_user_days"], "365")
            self.assertEqual(notifications.get_system_settings()["notify_admin_new_request"], "1")
        with self.assertRaises(ValueError):
            notifications.update_system_settings({"notify_admin_new_request": "invalid"})

    def test_recent_checkout_survives_history_cleanup_and_migration(self):
        loan_id = self.loan(days=1)
        recorded = self.user()["last_borrowed_at"]
        self.assertEqual(self.user()["inactivity_warning"], 0)
        with database.connect() as db:
            db.execute("DELETE FROM loans WHERE loan_id=?", (loan_id,))
        database.initialize_database()
        self.assertEqual(self.user()["last_borrowed_at"], recorded)
        self.assertEqual(self.user()["inactivity_warning"], 0)

    def test_existing_history_is_backfilled_and_old_import_does_not_replace_new_date(self):
        self.loan(days=10)
        with database.connect() as db:
            db.execute("UPDATE users SET last_borrowed_at=NULL WHERE user_id='old'")
        database.initialize_database()
        recorded = self.user()["last_borrowed_at"]
        self.assertIsNotNone(recorded)
        self.loan(days=400)
        self.assertEqual(self.user()["last_borrowed_at"], recorded)

    def test_outstanding_loans_open_requests_and_damage_prevent_warning(self):
        loan_id = self.loan(status="active")
        self.assertEqual(self.user()["inactivity_warning"], 0)
        with database.connect() as db:
            db.execute("UPDATE loans SET status='returned', returned_quantity=1 WHERE loan_id=?", (loan_id,))
            db.execute("""INSERT INTO loan_returns (loan_id, quantity, damaged_quantity, damage_description,
                          damage_status, returned_at) VALUES (?, 1, 1, 'Test damage', 'quarantined', '2000-01-02')""",
                       (loan_id,))
        self.assertEqual(self.user()["inactivity_warning"], 0)
        with database.connect() as db:
            db.execute("UPDATE loan_returns SET damage_status='repaired'")
        self.assertEqual(self.user()["inactivity_warning"], 1)
        with database.connect() as db:
            db.execute("""INSERT INTO loan_requests (user_id, object_id, quantity, lending_date, return_date,
                          status, created_at, updated_at) VALUES ('old','A',1,'2026-10-23','2026-10-24',
                          'requested','2026-10-23','2026-10-23')""")
        self.assertEqual(self.user()["inactivity_warning"], 0)

    def test_notification_filters_and_shared_read_state_are_per_type(self):
        self.event("loan")
        request = self.event()
        data = notifications.list_admin_notifications()
        self.assertEqual(data["unread_count"], 1)
        self.assertEqual(set(data["items"][0]), {"event_id", "event_type", "event_time", "unread"})
        notifications.mark_admin_notifications_read({"up_to_event_id": request})
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 0)
        notifications.update_system_settings({"notify_admin_loaned": True})
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 1)
        database.initialize_database()
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 1)
        notifications.update_system_settings({"notify_admin_new_request": False, "notify_admin_loaned": False})
        self.assertEqual(notifications.list_admin_notifications(), {"items": [], "unread_count": 0, "latest_event_id": 0})

    def test_notification_limit_and_concurrent_arrival_are_preserved(self):
        for _ in range(25):
            self.event()
        data = notifications.list_admin_notifications()
        self.assertEqual(len(data["items"]), 20)
        self.assertEqual(data["unread_count"], 25)
        self.event()
        notifications.mark_admin_notifications_read({"up_to_event_id": data["latest_event_id"]})
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 1)
        notifications.mark_admin_notifications_read({"up_to_event_id": 1})
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 1)

    def test_invalid_read_cursor_and_account_cleanup(self):
        event_id = self.event()
        for value in (-1, event_id + 1, 1.5, True, None, ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                notifications.mark_admin_notifications_read({"up_to_event_id": value})
        notifications.mark_admin_notifications_read({"up_to_event_id": event_id})
        with database.connect() as db:
            db.execute("DELETE FROM access_accounts WHERE username='first'")
        self.assertEqual(database.rows("SELECT * FROM admin_notification_reads"), [])
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 0)

    def test_migration_preserves_latest_legacy_read_cursor(self):
        first = self.event()
        second = self.event()
        self.event()
        with database.connect() as db:
            db.executemany("INSERT INTO admin_notification_reads VALUES (?, 'request', ?)",
                           [("first", first), ("second", second)])
        database.initialize_database()
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 1)
        latest = notifications.list_admin_notifications()["latest_event_id"]
        notifications.mark_admin_notifications_read({"up_to_event_id": latest})
        database.initialize_database()
        self.assertEqual(notifications.list_admin_notifications()["unread_count"], 0)
