import tempfile
import unittest
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from pathlib import Path
from unittest.mock import patch

from http_client import login
from backend import database
from backend.services import loans, notifications
from backend.server import AppHandler


class MultiArticleLoansTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path_patch = patch.object(database, "DATABASE_PATH", Path(self.temp.name) / "test.db")
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        self.settings_patch = patch.object(loans, "get_system_settings", return_value={"max_loan_days": "90"})
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        database.initialize_database()
        with database.connect() as db:
            db.execute("INSERT INTO users (user_id, name) VALUES ('user', 'Test User')")
            db.execute("INSERT INTO users (user_id, name) VALUES ('other', 'Other User')")
            for object_id in ('A', 'B', 'C'):
                db.execute("""INSERT INTO objects (object_id, name, category, location, tornado_id, door_id,
                    total_quantity, available_quantity, min_quantity, status)
                    VALUES (?, ?, 'Tool', 'Test', 'Store', 'Door', 10, 10, 0, 'Available')""",
                           (object_id, object_id))

    def request(self, items=None, **extra):
        return loans.create_loan_request({
            "user_id": "user", "lending_date": "2026-09-14", "due_time": "2026-09-20",
            "items": items if items is not None else [{"object_id": "A", "quantity": 2}, {"object_id": "B", "quantity": 1}],
            **extra,
        })

    def activate(self, result):
        for status in ("approved", "prepared", "loaned"):
            loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": status})

    def stock(self, object_id):
        return database.row("SELECT available_quantity FROM objects WHERE object_id = ?", (object_id,))["available_quantity"]

    def add_single_stock_object(self):
        with database.connect() as db:
            db.execute("""INSERT INTO objects (object_id, name, category, location, tornado_id, door_id,
                total_quantity, available_quantity, min_quantity, status)
                VALUES ('LAST', 'Last item', 'Tool', 'Test', 'Store', 'Door', 1, 1, 0, 'Available')""")

    def run_simultaneous(self, action):
        def invoke(user_id):
            try:
                action(user_id)
                return True
            except ValueError:
                return False

        with ThreadPoolExecutor(max_workers=2) as executor:
            return list(executor.map(invoke, ("user", "other")))

    def test_concurrent_checkouts_cannot_borrow_the_last_item_twice(self):
        self.add_single_stock_object()
        barrier = threading.Barrier(2)

        def synchronize_validation(*_args, **_kwargs):
            barrier.wait(timeout=5)

        payload = {
            "object_id": "LAST",
            "quantity": 1,
            "lending_date": "2026-10-21",
            "due_time": "2026-10-22",
        }
        with patch.object(loans, "validate_loan_period", side_effect=synchronize_validation), \
                patch.object(loans, "open_door"):
            results = self.run_simultaneous(lambda user_id: loans.checkout({**payload, "user_id": user_id}))

        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.stock("LAST"), 0)
        self.assertEqual(len(loans.list_active_loans()), 1)

    def test_concurrent_issues_cannot_take_the_last_item_twice(self):
        self.add_single_stock_object()
        barrier = threading.Barrier(2)

        def synchronize_time():
            barrier.wait(timeout=5)
            return "2026-10-21 08:00:00"

        with patch.object(loans, "now_text", side_effect=synchronize_time), \
                patch.object(loans, "open_door"):
            results = self.run_simultaneous(
                lambda user_id: loans.issue_item({"object_id": "LAST", "user_id": user_id, "quantity": 1})
            )

        self.assertEqual(sorted(results), [False, True])
        self.assertEqual(self.stock("LAST"), 0)
        self.assertEqual(database.row("SELECT COUNT(*) AS count FROM events WHERE event_type = 'issue'")["count"], 1)

    def test_group_partial_then_all_return_and_repeat(self):
        result = self.request()
        self.assertEqual(len(result['request_ids']), 2)
        self.assertEqual({r['request_group_id'] for r in loans.list_loan_requests()}, {result['request_id']})
        self.activate(result)
        active = loans.list_active_loans()
        self.assertEqual({r['request_group_id'] for r in active}, {result['request_id']})
        first = next(r for r in active if r['object_id'] == 'A')
        payload = {"loan_ids": [first['loan_id']], "user_id": "user"}
        loans.return_item(payload)
        self.assertEqual(self.stock('A'), 10)
        self.assertEqual(self.stock('B'), 9)
        self.assertEqual(len(loans.list_active_loans()), 1)
        self.assertEqual({r['status'] for r in loans.list_loan_requests()}, {'returned', 'loaned'})
        with self.assertRaises(ValueError):
            loans.return_item(payload)
        self.assertEqual(self.stock('A'), 10)
        remaining = loans.list_active_loans()[0]['loan_id']
        loans.return_item({"loan_ids": [remaining, remaining], "user_id": "user"})
        self.assertEqual(self.stock('B'), 10)
        self.assertEqual(loans.list_active_loans(), [])

    def test_invalid_second_article_rolls_back_whole_request(self):
        with self.assertRaises(ValueError):
            self.request([{"object_id": "A"}, {"object_id": "missing"}])
        self.assertEqual(loans.list_loan_requests(), [])
        self.assertEqual(database.rows('SELECT * FROM events'), [])

    def test_request_cannot_exceed_current_stock_even_with_duplicate_rows(self):
        with database.connect() as db:
            db.execute("UPDATE objects SET total_quantity=15, available_quantity=15 WHERE object_id='A'")
        for items in (
            [{"object_id": "A", "quantity": 16}],
            [{"object_id": "A", "quantity": 8}, {"object_id": "A", "quantity": 8}],
            [{"object_id": "B", "quantity": 1}, {"object_id": "A", "quantity": 16}],
        ):
            with self.subTest(items=items), self.assertRaisesRegex(ValueError, "15"):
                self.request(items)
            self.assertEqual(loans.list_loan_requests(), [])
            self.assertEqual(database.rows("SELECT * FROM events"), [])
            self.assertEqual(self.stock("A"), 15)

    def test_request_at_stock_limit_does_not_reserve_inventory(self):
        self.request([{"object_id": "A", "quantity": 10}])
        self.assertEqual(loans.list_loan_requests()[0]["quantity"], 10)
        self.assertEqual(self.stock("A"), 10)

    def test_request_uses_latest_available_not_total_stock(self):
        with database.connect() as db:
            db.execute("UPDATE objects SET available_quantity=0 WHERE object_id='A'")
        with self.assertRaisesRegex(ValueError, "0"):
            self.request([{"object_id": "A", "quantity": 1}])
        self.assertEqual(loans.list_loan_requests(), [])

    def test_duplicate_existing_request_rolls_back_new_rows(self):
        self.request([{"object_id": "B"}])
        with self.assertRaises(ValueError):
            self.request()
        self.assertEqual(len(loans.list_loan_requests()), 1)

    def test_duplicate_articles_merge_and_invalid_quantities_rejected(self):
        self.request([{"object_id": "A", "quantity": 1}, {"object_id": "A", "quantity": 2}])
        self.assertEqual(loans.list_loan_requests()[0]['quantity'], 3)
        for quantity in (0, -1, 1.5, None, True, 'bad'):
            with self.subTest(quantity=quantity), self.assertRaises(ValueError):
                self.request([{"object_id": "C", "quantity": quantity}])

    def test_wrong_user_or_stale_selection_returns_nothing(self):
        result = self.request()
        self.activate(result)
        ids = [r['loan_id'] for r in loans.list_active_loans()]
        for payload in ({"loan_ids": ids, "user_id": "other"}, {"loan_ids": ids + [99999], "user_id": "user"}):
            with self.assertRaises(ValueError):
                loans.return_item(payload)
            self.assertEqual(len(loans.list_active_loans()), 2)
            self.assertEqual(self.stock('A'), 8)
        loans.return_item({"loan_ids": ids, "user_id": "user"})
        self.assertEqual(loans.list_active_loans(), [])
        self.assertEqual(self.stock('A'), 10)
        self.assertEqual(self.stock('B'), 10)

    def test_single_article_api_and_repeat_migration(self):
        result = loans.create_loan_request({"user_id": "user", "object_id": "A", "quantity": 1,
                                           "lending_date": "2026-09-14", "return_date": "2026-09-20"})
        database.initialize_database()
        self.activate(result)
        loan_id = loans.list_active_loans()[0]['loan_id']
        loans.return_item({"identifier": str(loan_id)})
        self.assertEqual(self.stock('A'), 10)

    def test_http_request_with_three_articles_and_empty_legacy_object_id(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), AppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            headers = login(server)
            payload = {"user_id": "user", "object_id": "", "quantity": 1,
                       "lending_date": "2026-09-14", "due_time": "2026-09-21",
                       "items": [{"object_id": item, "quantity": 1} for item in ('A', 'B', 'C')]}
            request = Request(f'http://127.0.0.1:{server.server_port}/api/loan-requests',
                              data=json.dumps(payload).encode(), headers=headers)
            with urlopen(request) as response:
                result = json.load(response)
            self.assertTrue(result['ok'])
            self.assertEqual(len(result['data']['request_ids']), 3)
            self.assertEqual(len({item['request_group_id'] for item in loans.list_loan_requests()}), 1)
            status_request = Request(
                f'http://127.0.0.1:{server.server_port}/api/loan-requests',
                data=json.dumps({"request_group_id": result['data']['request_id'], "status": "approved"}).encode(),
                headers=headers,
                method='PUT',
            )
            with urlopen(status_request) as response:
                status_result = json.load(response)
            self.assertTrue(status_result['ok'])
            self.assertEqual({item['status'] for item in loans.list_loan_requests()}, {'approved'})
        finally:
            server.shutdown()
            thread.join()
            server.server_close()

    def test_group_status_moves_all_articles_through_pickup(self):
        result = self.request()
        group_id = result["request_id"]
        for status in ("approved", "prepared", "loaned"):
            response = loans.update_loan_request_group_status({
                "request_group_id": group_id,
                "status": status,
            })
            self.assertEqual(response["status"], status)
            self.assertEqual({item["status"] for item in loans.list_loan_requests()}, {status})
        self.assertEqual(len(loans.list_active_loans()), 2)
        self.assertEqual(self.stock("A"), 8)
        self.assertEqual(self.stock("B"), 9)
        loans.update_loan_request_group_status({"request_group_id": group_id, "status": "returned"})
        self.assertEqual(loans.list_active_loans(), [])
        self.assertEqual(self.stock("A"), 10)
        self.assertEqual(self.stock("B"), 10)
        loans.update_loan_request_group_status({"request_group_id": group_id, "status": "stocked"})
        self.assertEqual({item["status"] for item in loans.list_loan_requests()}, {"stocked"})

    def test_group_pickup_is_atomic_when_one_article_lacks_stock(self):
        with database.connect() as db:
            db.execute("UPDATE objects SET total_quantity=20, available_quantity=20 WHERE object_id='B'")
        result = self.request([
            {"object_id": "A", "quantity": 2},
            {"object_id": "B", "quantity": 20},
        ])
        with database.connect() as db:
            db.execute("UPDATE objects SET available_quantity=10 WHERE object_id='B'")
        group_id = result["request_id"]
        loans.update_loan_request_group_status({"request_group_id": group_id, "status": "approved"})
        loans.update_loan_request_group_status({"request_group_id": group_id, "status": "prepared"})
        with self.assertRaises(ValueError):
            loans.update_loan_request_group_status({"request_group_id": group_id, "status": "loaned"})
        self.assertEqual({item["status"] for item in loans.list_loan_requests()}, {"prepared"})
        self.assertEqual(loans.list_active_loans(), [])
        self.assertEqual(self.stock("A"), 10)
        self.assertEqual(self.stock("B"), 10)

    def test_group_action_catches_up_one_article_exception(self):
        result = self.request()
        first_id, _ = result["request_ids"]
        with database.connect() as db:
            db.execute("UPDATE loan_requests SET status='approved' WHERE request_id=?", (first_id,))
        response = loans.update_loan_request_group_status({
            "request_group_id": result["request_id"],
            "status": "approved",
        })
        self.assertEqual(len(response["request_ids"]), 1)
        self.assertEqual({item["status"] for item in loans.list_loan_requests()}, {"approved"})

    def test_individual_pre_checkout_transitions_rejected_for_group(self):
        result = self.request()
        for status in ("approved", "prepared", "loaned"):
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, "hela förfrågan"):
                loans.update_loan_request_status({"request_id": result["request_ids"][0], "status": status})
        self.assertEqual({item["status"] for item in loans.list_loan_requests()}, {"requested"})
        self.assertEqual(loans.list_active_loans(), [])
        self.assertEqual(self.stock("A"), 10)

    def test_old_mixed_group_catches_up_without_reopening_advanced_rows(self):
        result = self.request()
        first_id, _ = result["request_ids"]
        with database.connect() as db:
            db.execute("UPDATE loan_requests SET status='prepared' WHERE request_id=?", (first_id,))
        loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": "approved"})
        self.assertEqual(database.row("SELECT status FROM loan_requests WHERE request_id=?", (first_id,))["status"], "prepared")
        loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": "prepared"})
        loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": "loaned"})
        self.assertEqual(len(loans.list_active_loans()), 2)
        self.assertEqual(self.stock("A"), 8)

    def test_remove_unwanted_article_then_advance_group(self):
        result = self.request()
        loans.delete_loan_request(result["request_ids"][1])
        self.activate(result)
        self.assertEqual(len(loans.list_active_loans()), 1)
        self.assertEqual(self.stock("A"), 8)
        self.assertEqual(self.stock("B"), 10)

    def test_job_lists_four_returned_and_eleven_remaining(self):
        with database.connect() as db:
            db.execute("UPDATE objects SET total_quantity=15, available_quantity=15 WHERE object_id='A'")
        result = self.request([{"object_id": "A", "quantity": 15}])
        self.activate(result)
        loan = loans.list_active_loans()[0]
        loans.return_item({"user_id": "user", "items": [{
            "loan_id": loan["loan_id"], "quantity": 4, "expected_returned_quantity": 0,
        }]})
        job = loans.list_loan_requests()[0]
        self.assertEqual((job["quantity"], job["returned_quantity"], job["remaining_quantity"]), (15, 4, 11))
        self.assertEqual(job["status"], "loaned")
        self.assertEqual(self.stock("A"), 4)

    def test_group_cannot_skip_a_workflow_step(self):
        result = self.request()
        with self.assertRaises(ValueError):
            loans.update_loan_request_group_status({
                "request_group_id": result["request_id"],
                "status": "prepared",
            })

    def test_pickup_email_contains_the_whole_request(self):
        with database.connect() as db:
            db.execute("UPDATE users SET email = 'test@example.com' WHERE user_id = 'user'")
        result = self.request()
        loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": "approved"})
        loans.update_loan_request_group_status({"request_group_id": result["request_id"], "status": "prepared"})
        settings = {
            "max_loan_days": "90",
            "notify_pickup_ready": "1",
            "message_pickup_ready_subject": "Förfrågan {request_id}",
            "message_pickup_ready_body": "{object_name}",
        }
        with patch.object(loans, "get_system_settings", return_value=settings), \
                patch.object(loans, "send_email", return_value=1) as send:
            loans.send_pickup_ready_email(result["request_ids"][-1])
        self.assertIn("A (A)", send.call_args.args[1])
        self.assertIn("B (B)", send.call_args.args[1])
        self.assertTrue(all(item["pickup_ready_email_sent_at"] for item in loans.list_loan_requests()))

    def test_new_job_notification_lists_each_article_separately(self):
        settings = notifications.SYSTEM_SETTING_DEFAULTS.copy()
        settings["notify_new_job"] = "1"
        with patch.object(loans, "get_system_settings", return_value=settings), \
                patch.object(loans, "notify_rule_recipients") as notify:
            self.request([
                {"object_id": "A", "quantity": 5},
                {"object_id": "B", "quantity": 1},
                {"object_id": "C", "quantity": 1},
            ])
        body = notify.call_args.args[2]
        self.assertIn("NY LÅNEFÖRFRÅGAN", body)
        self.assertIn("ARTIKLAR (3)", body)
        self.assertIn("• 5 × A\n  Artikel-ID: A", body)
        self.assertIn("• 1 × B\n  Artikel-ID: B", body)
        self.assertIn("• 1 × C\n  Artikel-ID: C", body)
        self.assertIn("Totalt antal: 7", body)

    def test_only_the_legacy_default_notification_template_is_migrated(self):
        legacy = (
            "Ett nytt lånejobb har skapats.\n\n"
            "Användare: {user_name}\n"
            "Objekt: {object_name} ({object_id})\n"
            "Antal: {quantity}\n"
            "Utlåningsdatum: {lending_date}\n"
            "Returdatum: {return_date}"
        )
        with database.connect() as db:
            db.execute("INSERT INTO system_settings (key, value) VALUES ('message_new_job_body', ?)", (legacy,))
        database.initialize_database()
        migrated = database.row(
            "SELECT value FROM system_settings WHERE key = 'message_new_job_body'"
        )["value"]
        self.assertIn("ARTIKLAR ({article_count})", migrated)
        with database.connect() as db:
            db.execute(
                "UPDATE system_settings SET value = 'Min egen mall {user_name}' WHERE key = 'message_new_job_body'"
            )
        database.initialize_database()
        custom = database.row(
            "SELECT value FROM system_settings WHERE key = 'message_new_job_body'"
        )["value"]
        self.assertEqual(custom, "Min egen mall {user_name}")


if __name__ == '__main__':
    unittest.main()
