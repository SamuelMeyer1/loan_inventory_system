from contextlib import closing
from datetime import datetime, timedelta
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from backend import database
from backend.server import run_server
from backend.simulation_data import seed_simulation
from backend.services import loans, users, stats
from simulation_store import prepare_simulation, reset_simulation, simulation_guard, validate_simulation


class SimulationDataTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        self.path = prepare_simulation(self.storage)
        path_patch = patch.object(database, "DATABASE_PATH", self.path)
        path_patch.start()
        self.addCleanup(path_patch.stop)
        env = patch.dict(os.environ, {"LOAN_SIMULATION": "1", "LOAN_DATABASE_PATH": str(self.path),
                                     "LOAN_ENABLE_NOTIFICATIONS": "0"})
        env.start()
        self.addCleanup(env.stop)
        database.initialize_database()
        self.base = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        seed_simulation(self.base)

    def test_population_and_all_workflow_examples(self):
        people = users.list_users(include_inactive=True)
        self.assertEqual(len(people), 15)
        self.assertEqual(len(users.list_groups()), 5)
        self.assertEqual(database.row("SELECT COUNT(*) AS n FROM objects")["n"], 8)
        self.assertEqual({person["company"] for person in people}, {"Demo Intern", "Demo Extern AB"})
        self.assertTrue(all(person["email"].endswith("@example.invalid") and not person["phone"] for person in people))
        self.assertTrue(all(person["name"].startswith("Demo ") for person in people))
        indexed = {person["user_id"]: person for person in people}
        self.assertEqual(indexed["USR-002"]["borrow_blocked"], 1)
        self.assertEqual(indexed["USR-012"]["borrow_override"], 1)
        self.assertEqual(indexed["USR-012"]["borrow_blocked"], 0)
        self.assertEqual(indexed["USR-013"]["active"], 0)
        self.assertEqual(indexed["USR-014"]["inactivity_warning"], 1)
        self.assertEqual(indexed["USR-015"]["inactivity_warning"], 1)
        counts = {row["status"]: row["n"] for row in database.rows(
            "SELECT status,COUNT(DISTINCT request_group_id) AS n FROM loan_requests GROUP BY status")}
        self.assertEqual(counts, {"requested": 5, "approved": 3, "prepared": 3, "loaned": 20, "returned": 7, "stocked": 31})
        self.assertEqual(len(loans.list_active_loans()), 24)
        self.assertTrue(any(loan["returned_quantity"] > 0 for loan in loans.list_active_loans()))
        self.assertEqual({row["damage_status"] for row in database.rows(
            "SELECT DISTINCT damage_status FROM loan_returns WHERE damaged_quantity>0")},
            {"quarantined", "repaired", "discarded"})
        chart_data = stats.statistics_data()
        self.assertGreaterEqual(len(chart_data["loans_per_month"]), 8)
        self.assertGreaterEqual(len(chart_data["returns_per_month"]), 8)
        self.assertEqual(chart_data["summary"]["orphan_active_loans"], 0)
        self.assertGreater(chart_data["summary"]["overdue"], 0)
        self.assertGreater(chart_data["summary"]["low_stock"], 0)
        self.assertGreater(chart_data["summary"]["out_of_stock"], 0)
        self.assertEqual(chart_data["summary"]["quarantined_quantity"], 1)

    def test_stock_and_return_history_are_consistent(self):
        with database.connect() as db:
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])
            for item in db.execute("SELECT * FROM objects WHERE is_consumable=0"):
                outstanding = db.execute("SELECT COALESCE(SUM(quantity-returned_quantity),0) FROM loans WHERE object_id=?",
                                         (item["object_id"],)).fetchone()[0]
                quarantined = db.execute("""SELECT COALESCE(SUM(r.damaged_quantity),0)
                    FROM loan_returns r JOIN loans l ON l.loan_id=r.loan_id
                    WHERE l.object_id=? AND r.damage_status='quarantined'""", (item["object_id"],)).fetchone()[0]
                self.assertEqual(item["available_quantity"] + outstanding + quarantined, item["total_quantity"])
            for loan in db.execute("SELECT * FROM loans"):
                returned = db.execute("SELECT COALESCE(SUM(quantity),0) FROM loan_returns WHERE loan_id=?",
                                      (loan["loan_id"],)).fetchone()[0]
                self.assertEqual(loan["returned_quantity"], returned)
                self.assertEqual(loan["status"] == "returned", returned == loan["quantity"])
                self.assertLessEqual(loan["checkout_time"], loan["return_time"] or self.base.isoformat(" "))

    def test_edits_and_deletions_survive_reinitialization(self):
        with database.connect() as db:
            db.execute("UPDATE users SET name='Demo Edited' WHERE user_id='USR-001'")
            db.execute("DELETE FROM users WHERE user_id='USR-015'")
            db.execute("UPDATE system_settings SET value='0' WHERE key='notify_admin_loaned'")
        self.assertEqual(prepare_simulation(self.storage), self.path)
        database.initialize_database()
        seed_simulation(self.base + timedelta(days=20))
        self.assertEqual(database.row("SELECT name FROM users WHERE user_id='USR-001'")["name"], "Demo Edited")
        self.assertIsNone(database.row("SELECT * FROM users WHERE user_id='USR-015'"))
        self.assertEqual(database.row("SELECT value FROM system_settings WHERE key='notify_admin_loaned'")["value"], "0")
        self.assertEqual(database.row("SELECT generated_at FROM simulation_metadata")["generated_at"], self.base.strftime("%Y-%m-%d %H:%M:%S"))

    def test_reset_preserves_old_demo_and_refreshes_dates(self):
        old = self.path.read_bytes()
        unrelated = self.storage / "inventory.db"
        unrelated.write_bytes(b"real data sentinel")
        backup = reset_simulation(self.storage)
        self.assertIsNotNone(backup)
        self.assertEqual(backup.read_bytes(), old)
        self.assertFalse(self.path.exists())
        self.assertEqual(unrelated.read_bytes(), b"real data sentinel")
        prepare_simulation(self.storage)
        database.initialize_database()
        seed_simulation(self.base + timedelta(days=30))
        self.assertEqual(len(users.list_users(True)), 15)
        self.assertEqual(database.row("SELECT generated_at FROM simulation_metadata")["generated_at"],
                         (self.base + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S"))

    def test_running_demo_cannot_be_reset_or_opened_twice(self):
        original = self.path.read_bytes()
        with simulation_guard(self.path):
            for operation in (reset_simulation, prepare_simulation):
                with self.subTest(operation=operation.__name__), self.assertRaisesRegex(ValueError, "Stoppa"):
                    operation(self.storage)
        self.assertEqual(self.path.read_bytes(), original)

    def test_unmarked_data_and_normal_mode_are_refused(self):
        with patch.dict(os.environ, {"LOAN_SIMULATION": "0"}), patch("backend.server.initialize_database") as initialize:
            with self.assertRaisesRegex(ValueError, "bara öppnas i Simulering"):
                run_server("127.0.0.1", 0)
            initialize.assert_not_called()
            with self.assertRaisesRegex(ValueError, "endast.*Simulering"):
                seed_simulation()
        alien = self.storage / "unmarked.db"
        with closing(sqlite3.connect(alien)) as db, db:
            db.execute("CREATE TABLE real_data(value TEXT)")
        original = alien.read_bytes()
        with self.assertRaisesRegex(ValueError, "simuleringsdatabas"):
            validate_simulation(alien)
        self.assertEqual(alien.read_bytes(), original)

    def test_real_business_rules_block_and_return_demo_loans(self):
        for user in ("USR-002", "USR-013"):
            with self.subTest(user=user), self.assertRaises(ValueError):
                loans.create_loan_request({"user_id": user, "object_id": "OBJ-1006", "quantity": 1,
                    "lending_date": self.base.date().isoformat(),
                    "due_time": (self.base + timedelta(days=7)).date().isoformat()})
        active = next(loan for loan in loans.list_active_loans() if loan["returned_quantity"])
        old_stock = database.row("SELECT available_quantity FROM objects WHERE object_id=?", (active["object_id"],))["available_quantity"]
        with patch.object(loans, "get_system_settings", return_value={}):
            loans.return_item({"user_id": active["user_id"], "items": [{
                "loan_id": active["loan_id"], "quantity": active["remaining_quantity"],
                "expected_returned_quantity": active["returned_quantity"],
            }]})
        new_stock = database.row("SELECT available_quantity FROM objects WHERE object_id=?", (active["object_id"],))["available_quantity"]
        self.assertEqual(new_stock - old_stock, active["remaining_quantity"])
