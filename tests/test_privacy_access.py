import json
import tempfile
import threading
import time
import unittest
from datetime import datetime
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import Mock, patch

from backend import database
from backend.server import AppHandler, run_server
from backend.security import AccessState, create_account
from backend.services import privacy, users, notifications
from http_client import login


class PrivacyAccessTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        replacement = patch.object(database, "DATABASE_PATH", Path(temporary.name)/"test.db")
        replacement.start()
        self.addCleanup(replacement.stop)
        database.initialize_database()
        with database.connect() as db:
            db.executemany("INSERT INTO users (user_id, name, email) VALUES (?, ?, ?)",
                           [("u1", "Testperson A", "a@example.invalid"), ("u2", "Testperson B", "b@example.invalid")])
            db.execute("""INSERT INTO objects (object_id, name, category, location, tornado_id, door_id,
                total_quantity, available_quantity, min_quantity, status) VALUES ('M','Multimeter','Test','Test','Test','1',2,2,0,'Tillgänglig')""")
            db.executemany("""INSERT INTO loans (user_id, object_id, quantity, checkout_time, due_time, status)
                         VALUES (?, 'M', 1, '2026-01-01', '2026-01-02', 'active')""", [("u1",), ("u2",)])
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.operator = login(self.server, "operator-test", role="operator", user_id="u1")
        self.admin = login(self.server, "admin-test", role="admin")
        self.superadmin = login(self.server)

    def call(self, path, headers=None, method="GET", payload=None):
        data = json.dumps(payload).encode() if payload is not None else None
        request = Request(f"http://127.0.0.1:{self.server.server_port}"+path, data=data, headers=headers or {}, method=method)
        try:
            response = urlopen(request)
        except HTTPError as error:
            response = error
        with response:
            return response.status, json.load(response), response.headers

    def test_unauthenticated_api_denied_and_notice_public(self):
        for path in ("/api/users", "/api/loans", "/api/events", "/api/system-settings", "/api/privacy/export?user_id=u1"):
            with self.subTest(path=path):
                self.assertEqual(self.call(path)[0], 401)
        self.assertEqual(self.call("/api/privacy/notice")[0], 200)
        self.assertFalse(privacy.policy()["configured"])

    def test_operator_sees_only_self_and_cannot_get_private_settings(self):
        for path in ("/api/users", "/api/loans"):
            status, payload, headers = self.call(path, self.operator)
            self.assertEqual(status, 200)
            self.assertEqual({r["user_id"] for r in payload["data"]}, {"u1"})
            self.assertNotIn("rfid_code", payload["data"][0])
            self.assertEqual(headers["Cache-Control"], "no-store")
        with database.connect() as db:
            db.execute("INSERT INTO system_settings(key,value) VALUES ('smtp_username','private@example.invalid')")
        self.assertEqual(self.call("/api/system-settings", self.operator)[1]["data"], {"max_loan_days": "90"})
        for path in ("/api/statistics", "/api/events", "/api/groups", "/api/privacy/policy"):
            self.assertEqual(self.call(path, self.operator)[0], 403)

    def test_operator_cannot_write_other_borrower_or_use_legacy_return(self):
        self.assertEqual(self.call("/api/loan-requests", self.operator, "POST", {"user_id": "u2"})[0], 403)
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"identifier": "2"})[0], 403)
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"user_id": "u1", "loan_ids": [2]})[0], 400)
        self.assertEqual(database.row("SELECT status FROM loans WHERE loan_id=2")["status"], "active")
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"loan_ids": [1]})[0], 200)

    def test_role_tampering_and_admin_privacy_access_denied(self):
        self.assertEqual(self.call("/api/users", {**self.operator, "X-Role": "superadmin"}, "POST", {"role": "superadmin"})[0], 403)
        for path in ("/api/privacy/export?user_id=u1", "/api/privacy/erase?user_id=u1", "/api/events"):
            self.assertEqual(self.call(path, self.admin)[0], 403)
        self.assertEqual(self.call("/api/system-settings", self.admin, "PUT", {})[0], 403)

    def test_partial_return_ownership_and_admin_damage_resolution(self):
        item = {"loan_id": 1, "quantity": 1, "damaged_quantity": 1,
                "damage_description": "Cracked case", "expected_returned_quantity": 0}
        self.assertEqual(self.call("/api/damaged-returns")[0], 401)
        self.assertEqual(self.call("/api/damaged-returns", self.operator)[0], 403)
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"user_id": "u2", "items": [item]})[0], 403)
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"items": [{**item, "loan_id": 2}]})[0], 400)
        status, response, _ = self.call("/api/return", self.operator, "POST", {"items": [item]})
        self.assertEqual(status, 200, response)
        report_id = response["data"]["items"][0]["return_id"]
        self.assertEqual(self.call("/api/return", self.operator, "POST", {"items": [item]})[0], 400)
        status, queue, _ = self.call("/api/damaged-returns", self.admin)
        self.assertEqual(status, 200)
        self.assertEqual(queue["data"][0]["damage_description"], "Cracked case")
        payload = {"return_id": report_id, "resolution": "discarded", "confirmed": True}
        self.assertEqual(self.call("/api/damaged-returns/resolve", self.operator, "POST", payload)[0], 403)
        without_csrf = {key: value for key, value in self.admin.items() if key != "X-CSRF-Token"}
        self.assertEqual(self.call("/api/damaged-returns/resolve", without_csrf, "POST", payload)[0], 403)
        with database.connect() as db:
            db.execute("UPDATE objects SET available_quantity=0 WHERE object_id='M'")
        self.assertEqual(self.call("/api/damaged-returns/resolve", self.admin, "POST", payload)[0], 200)
        self.assertEqual(self.call("/api/damaged-returns/resolve", self.superadmin, "POST", payload)[0], 400)
        self.assertEqual(self.call("/api/damaged-returns", self.admin)[1]["data"], [])

    def test_new_user_requires_privacy_notice_acknowledgement_and_records_time(self):
        payload = {
            "first_name": "New",
            "last_name": "Borrower",
            "email": "new.borrower@example.invalid",
            "rfid_code": "test-card-code",
            "role": "operator",
            "active": True,
        }
        status, response, _ = self.call("/api/users", self.admin, "POST", payload)
        self.assertEqual(status, 400)
        self.assertIn("bekräfta informationen", response["error"])
        self.assertIsNone(database.row("SELECT user_id FROM users WHERE email=?", (payload["email"],)))

        payload["privacy_notice_acknowledged"] = True
        status, response, _ = self.call("/api/users", self.admin, "POST", payload)
        self.assertEqual(status, 200, response)
        user_id = response["data"]["user_id"]
        created = database.row(
            "SELECT privacy_notice_acknowledged_at FROM users WHERE user_id=?",
            (user_id,),
        )
        self.assertTrue(created["privacy_notice_acknowledged_at"])

        self.server.anonymous_operator = True
        status, response, _ = self.call("/api/users")
        self.assertEqual(status, 200)
        new_user = next(user for user in response["data"] if user["user_id"] == user_id)
        self.assertNotIn("privacy_notice_acknowledged_at", new_user)
        self.assertNotIn("rfid_code", new_user)

    def test_csrf_and_cross_origin_and_host_checks(self):
        headers = {key: value for key, value in self.operator.items() if key != "X-CSRF-Token"}
        self.assertEqual(self.call("/api/loan-requests", headers, "POST", {})[0], 403)
        for extra in ({"Origin": "https://attacker.invalid"}, {"Sec-Fetch-Site": "cross-site"}, {"Host": "attacker.invalid"}):
            self.assertEqual(self.call("/api/loan-requests", {**self.operator, **extra}, "POST", {})[0], 403)

    def test_logout_expiry_and_account_change_invalidate_session(self):
        self.assertEqual(self.call("/api/auth/logout", self.operator, "POST", {})[0], 200)
        self.assertEqual(self.call("/api/users", self.operator)[0], 401)
        create_account("admin-test", "another-fictitious-password", "admin")
        self.assertEqual(self.call("/api/users", self.admin)[0], 401)
        for session in self.server.access.sessions.values():
            session["expires"] = time.monotonic()-1
        self.assertEqual(self.call("/api/users", self.superadmin)[0], 401)

    def test_disabled_borrower_cannot_continue_session(self):
        with database.connect() as db:
            db.execute("UPDATE users SET active=0 WHERE user_id='u1'")
        self.assertEqual(self.call("/api/users", self.operator)[0], 401)

    def test_password_hash_and_cookie_and_rate_limit(self):
        account = database.row("SELECT * FROM access_accounts WHERE username='test-admin'")
        self.assertNotEqual(account["password_hash"], "fictitious-test-password")
        headers = {"Content-Type": "application/json", "X-Loan-Client": "browser"}
        status, payload, response_headers = self.call("/api/auth/login", headers, "POST", {"username": "test-admin", "password": "fictitious-test-password"})
        self.assertEqual(status, 200)
        self.assertIn("HttpOnly", response_headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", response_headers["Set-Cookie"])
        self.assertNotIn("password_hash", json.dumps(payload))
        self.call("/api/auth/login", headers, "POST", {"username": "missing", "password": "wrong"})
        self.assertEqual(self.call("/api/auth/login", headers, "POST", {"username": "test-admin", "password": "fictitious-test-password"})[0], 400)

    def test_export_excludes_credentials_and_other_persons_structured_data(self):
        export = privacy.export_subject("u1")
        self.assertEqual({r["user_id"] for r in export["loans"]}, {"u1"})
        self.assertNotIn("password_hash", json.dumps(export))
        self.assertNotIn("b@example.invalid", json.dumps(export))

    def test_erase_is_preview_first_blocks_obligations_then_removes_account(self):
        self.assertTrue(privacy.erase_subject("u1")["blocked"])
        with self.assertRaises(ValueError):
            privacy.erase_subject("u1", True)
        with database.connect() as db:
            db.execute("UPDATE loans SET status='returned', return_time='2026-02-01' WHERE user_id='u1'")
            db.execute("UPDATE events SET message='Testperson A a@example.invalid' WHERE 0")
        self.assertFalse(privacy.erase_subject("u1")["blocked"])
        self.assertIsNotNone(database.row("SELECT * FROM users WHERE user_id='u1'"))
        self.assertEqual(self.call("/api/privacy/erase", self.superadmin, "POST", {"user_id": "u1"})[0], 400)
        self.assertTrue(privacy.erase_subject("u1", True)["applied"])
        self.assertIsNone(database.row("SELECT * FROM users WHERE user_id='u1'"))
        self.assertIsNotNone(database.row("SELECT * FROM users WHERE user_id='u2'"))
        self.assertEqual(self.call("/api/users", self.operator)[0], 401)

    def test_retention_requires_policy_preserves_active_rows_and_is_idempotent(self):
        with self.assertRaises(ValueError):
            privacy.retention()
        privacy.save_policy({"controller": "Testorganisation", "contact": "test@example.invalid", "purpose": "Test", "lawful_basis": "Testunderlag, ej produktionsbeslut", "loan_days": "30", "event_days": "10"})
        with database.connect() as db:
            db.execute("UPDATE loans SET status='returned', return_time='2026-01-03' WHERE loan_id=1")
            db.execute("INSERT INTO events(event_time,event_type,message) VALUES ('2026-01-01','test','Old')")
        now = datetime(2026, 10, 15)
        preview = privacy.retention(now=now)
        self.assertEqual(preview["counts"]["loans"], 1)
        self.assertEqual(len(database.rows("SELECT * FROM loans")), 2)
        privacy.retention(True, now)
        self.assertEqual(database.row("SELECT user_id FROM loans")["user_id"], "u2")
        self.assertEqual(privacy.retention(now=now)["counts"]["loans"], 0)

    def test_new_event_text_minimized_and_phone_company_optional(self):
        with database.connect() as db:
            db.execute("INSERT INTO events(event_time,event_type,message) VALUES ('2026-10-15','user','Testperson A a@example.invalid')")
        self.assertNotIn("a@example.invalid", database.rows("SELECT message FROM events")[-1]["message"])
        users.validate_user_fields("Testperson", "C", "c@example.invalid", "", "", "operator")
        self.assertTrue(users.make_user_id("A", "B", "email-alias", "a@example.invalid").startswith("usr-"))

    def test_migrations_repeat_without_changing_existing_data(self):
        database.initialize_database()
        database.initialize_database()
        self.assertEqual(database.row("SELECT name FROM users WHERE user_id='u1'")["name"], "Testperson A")
        self.assertEqual(database.row("SELECT COUNT(*) AS n FROM access_accounts")["n"], 3)

    def test_upgrade_from_older_user_schema_preserves_rows_and_legacy_events(self):
        legacy = database.DATABASE_PATH.parent/"legacy.db"
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(legacy)) as db:
            db.executescript("""CREATE TABLE users(user_id TEXT PRIMARY KEY,name TEXT NOT NULL,department TEXT,active INTEGER DEFAULT 1);
                INSERT INTO users(user_id,name,department) VALUES('legacy','Fiktiv äldre profil','Test');
                CREATE TABLE events(event_id INTEGER PRIMARY KEY AUTOINCREMENT,event_time TEXT NOT NULL,event_type TEXT NOT NULL,message TEXT NOT NULL);
                INSERT INTO events(event_time,event_type,message) VALUES('2026-01-01','test','Fiktiv äldre profil');""")
        with patch.object(database, "DATABASE_PATH", legacy):
            database.initialize_database()
            database.initialize_database()
            self.assertEqual(database.row("SELECT name FROM users")["name"], "Fiktiv äldre profil")
            self.assertEqual(database.row("SELECT message FROM events")["message"], "Fiktiv äldre profil")
            self.assertEqual(len(privacy.export_subject("legacy")["legacy_events_for_manual_review"]), 1)
            preview = privacy.erase_subject("legacy")
            self.assertFalse(preview["applied"])
            privacy.erase_subject("legacy", True)
            self.assertNotIn("Fiktiv äldre profil", database.row("SELECT message FROM events ORDER BY event_id")["message"])

    def test_unfinished_request_group_and_pending_subject_block_purge(self):
        privacy.save_policy({"controller": "Test", "contact": "test@example.invalid", "purpose": "Test", "lawful_basis": "Test", "loan_days": "30", "event_days": "10"})
        with database.connect() as db:
            db.executemany("""INSERT INTO loan_requests(user_id,object_id,quantity,lending_date,return_date,status,created_at,updated_at,request_group_id)
                VALUES ('u1','M',1,'2026-01-01','2026-01-02',?,'2026-01-01','2026-01-03',99)""", [("stocked",), ("prepared",)])
            db.execute("UPDATE loans SET status='returned', return_time='2026-01-03', loan_request_id=1 WHERE loan_id=1")
        result = privacy.retention(now=datetime(2026, 10, 15))
        self.assertEqual(result["counts"]["loan_requests"], 0)
        self.assertEqual(result["counts"]["loans"], 0)
        with self.assertRaises(ValueError):
            privacy.erase_subject("u1", True)

    def test_smtp_transport_requires_tls(self):
        settings = {"smtp_enabled": "1", "smtp_host": "smtp.example.invalid", "smtp_port": "587", "smtp_from_address": "test@example.invalid", "smtp_use_tls": "0", "notification_simulation_enabled": "0"}
        with patch.dict("os.environ", {"LOAN_ENABLE_NOTIFICATIONS": "1"}), patch.object(notifications.smtplib, "SMTP") as smtp:
            with self.assertRaises(ValueError):
                notifications.email_msg("Test", "Test", ["test@example.invalid"], settings)
            smtp.assert_not_called()

    def test_server_refuses_network_binding_without_opt_in_before_database_access(self):
        with patch.dict("os.environ", {"LOAN_ALLOW_LAN": "0"}), patch("backend.server.initialize_database") as initialize:
            with self.assertRaises(ValueError):
                run_server("0.0.0.0")
            with self.assertRaises(ValueError):
                run_server("192.168.1.25")
            with self.assertRaises(ValueError):
                run_server("8.8.8.8")
            initialize.assert_not_called()

    def test_fixed_local_test_accounts_work_only_on_loopback_and_are_locked(self):
        env = {
            "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "1",
            "LOAN_LOCAL_ADMIN_PASSWORD": "admin",
            "LOAN_LOCAL_SUPERADMIN_PASSWORD": "superadmin",
        }
        server = Mock()
        server.server_port = 8000
        with patch.dict("os.environ", env), \
                patch("backend.server.ThreadingHTTPServer", return_value=server):
            run_server("127.0.0.1")
        self.assertTrue(server.local_operator)

        accounts = database.rows("SELECT username,role,password_hash FROM access_accounts WHERE username IN (SELECT username FROM local_test_accounts)")
        self.assertEqual({(account["username"], account["role"]) for account in accounts},
                         {("admin", "admin"), ("superadmin", "superadmin")})
        self.assertNotIn("admin", {account["password_hash"] for account in accounts})
        state = AccessState()
        admin_token = state.login("admin", "admin", "127.0.0.1")
        superadmin_token = state.login("superadmin", "superadmin", "127.0.0.1")
        self.assertTrue(admin_token)
        self.assertTrue(superadmin_token)
        with self.assertRaisesRegex(ValueError, "låst"):
            create_account("admin", "another-password-longer-than-15", "admin")

    def test_fixed_local_test_accounts_refuse_lan_binding_before_database_access(self):
        env = {"LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "1", "LOAN_ALLOW_LAN": "1"}
        with patch.dict("os.environ", env), patch("backend.server.initialize_database") as initialize:
            with self.assertRaisesRegex(ValueError, "LAN-läge"):
                run_server("10.222.16.50")
            initialize.assert_not_called()

    def test_server_allows_private_lan_binding_only_with_explicit_opt_in(self):
        server = Mock()
        server.server_port = 8000
        with patch.dict("os.environ", {"LOAN_ALLOW_LAN": "1"}), \
                patch("backend.server.initialize_database"), \
                patch("backend.server.ThreadingHTTPServer", return_value=server) as create_server:
            run_server("192.168.1.25")
        create_server.assert_called_once_with(("192.168.1.25", 8000), AppHandler, bind_and_activate=False)
        self.assertEqual(server.allowed_hosts, {"192.168.1.25:8000"})
        self.assertTrue(server.anonymous_operator)

    def test_anonymous_lan_operator_gets_operator_access_without_login(self):
        self.server.anonymous_operator = True
        headers = {"Host": f"127.0.0.1:{self.server.server_port}"}
        status, identity, _ = self.call("/api/auth/session", headers)
        self.assertEqual(status, 200)
        self.assertEqual(identity["data"]["role"], "operator")
        self.assertTrue(identity["data"]["anonymous"])
        status, payload, _ = self.call("/api/users", headers)
        self.assertEqual(status, 200)
        self.assertEqual({user["user_id"] for user in payload["data"]}, {"u1", "u2"})
        status, payload, _ = self.call("/api/loans", headers)
        self.assertEqual(status, 200)
        self.assertEqual({loan["user_id"] for loan in payload["data"]}, {"u1", "u2"})
        self.assertEqual(self.call("/api/events", headers)[0], 403)
        write_headers = {**headers, "Content-Type": "application/json", "X-Loan-Client": "browser", "X-CSRF-Token": "lan-test-operator",
                         "Origin": f"http://127.0.0.1:{self.server.server_port}"}
        status, payload, _ = self.call("/api/return", write_headers, "POST",
                                       {"user_id": "u2", "loan_ids": [2]})
        self.assertEqual(status, 200, payload)
        self.assertEqual(database.row("SELECT status FROM loans WHERE loan_id=2")["status"], "returned")

    def test_local_operator_view_is_available_without_login(self):
        self.server.local_operator = True
        headers = {"Host": f"127.0.0.1:{self.server.server_port}"}
        status, identity, _ = self.call("/api/auth/session", headers)
        self.assertEqual(status, 200)
        self.assertEqual(identity["data"]["role"], "operator")
        self.assertTrue(identity["data"]["anonymous"])
        self.assertEqual(self.call("/api/users", headers)[0], 200)
        self.assertEqual(self.call("/api/events", headers)[0], 403)
        status, identity, _ = self.call("/api/auth/session", self.admin)
        self.assertEqual(status, 200)
        self.assertEqual(identity["data"]["role"], "admin")
        self.assertFalse(identity["data"].get("anonymous", False))
        self.assertEqual(self.call("/api/auth/logout", self.admin, "POST", {})[0], 200)
        self.assertTrue(self.call("/api/auth/session", self.admin)[1]["data"]["anonymous"])

    def test_authenticated_lan_admin_is_not_replaced_by_anonymous_operator(self):
        self.server.anonymous_operator = True
        self.assertEqual(self.call("/api/auth/session", self.admin)[1]["data"]["role"], "admin")

    def test_runtime_information_is_public_without_database_details(self):
        self.server.simulation = True
        self.server.instance_id = "test-instance"
        status, payload, _ = self.call("/api/runtime")
        self.assertEqual(status, 200)
        self.assertEqual(payload["data"], {"simulation": True, "instance_id": "test-instance"})

    def test_bad_json_and_internal_errors_do_not_leak_details(self):
        request = Request(f"http://127.0.0.1:{self.server.server_port}/api/loan-requests", data=b"[]", headers=self.operator)
        with self.assertRaises(HTTPError) as result:
            urlopen(request)
        self.assertEqual(result.exception.code, 400)
        result.exception.close()
        with patch("backend.server.services.list_objects", side_effect=RuntimeError("private filesystem path and secret")):
            status, payload, _ = self.call("/api/objects", self.operator)
            self.assertEqual(status, 500)
            self.assertNotIn("private", json.dumps(payload))

    def test_external_notifications_blocked_without_opening_network(self):
        with patch.dict("os.environ", {"LOAN_ENABLE_NOTIFICATIONS": "0"}), patch.object(notifications.smtplib, "SMTP") as smtp:
            for send in (notifications.email_msg, notifications.team_msg):
                with self.assertRaises(ValueError):
                    send("Test", "Fiktivt innehåll", ["test@example.invalid"])
            smtp.assert_not_called()

    def test_environment_password_never_written_to_database_or_api(self):
        with database.connect() as db:
            db.execute("INSERT INTO system_settings(key,value) VALUES ('notification_simulation_recipient','test@example.invalid')")
        with patch.dict("os.environ", {"LOAN_SMTP_PASSWORD": "test-environment-secret"}):
            result = notifications.update_system_settings({})
            self.assertNotIn("test-environment-secret", json.dumps(result))
            self.assertIsNone(database.row("SELECT value FROM system_settings WHERE key='smtp_password'"))

    def test_operator_can_only_collect_own_prepared_request(self):
        with database.connect() as db:
            db.executemany("""INSERT INTO loan_requests(user_id,object_id,quantity,lending_date,return_date,status,created_at,updated_at)
                       VALUES (?,'M',1,'2026-10-15','2026-10-16','prepared','2026-10-15','2026-10-15')""", [("u1",), ("u2",)])
        payload = {"request_id": 2, "status": "loaned"}
        self.assertEqual(self.call("/api/loan-requests", self.operator, "PUT", payload)[0], 403)
        payload = {"request_id": 1, "status": "approved"}
        self.assertEqual(self.call("/api/loan-requests", self.operator, "PUT", payload)[0], 403)
        payload = {"request_id": 1, "status": "loaned"}
        self.assertEqual(self.call("/api/loan-requests", self.operator, "PUT", payload)[0], 200)

    def test_operator_can_create_and_read_own_request_without_supplied_identity(self):
        with patch("backend.services.loans.notify_rule_recipients"):
            status, payload, _ = self.call("/api/loan-requests", self.operator, "POST", {
                "items": [{"object_id": "M", "quantity": 1}], "lending_date": "2026-10-15", "due_time": "2026-10-16"})
        self.assertEqual(status, 200)
        self.assertTrue(payload["data"]["request_id"] > 0)
        data = self.call("/api/loan-requests", self.operator)[1]["data"]
        self.assertEqual({r["user_id"] for r in data}, {"u1"})

    def test_security_audit_has_no_body_cookie_or_password_and_erasure_scrubs_identity(self):
        self.call("/api/return", self.operator, "POST", {"loan_ids": [1]})
        audit = database.rows("SELECT * FROM security_audit")
        self.assertTrue(any(r["actor"] == "operator-test" and r["action"] == "POST /api/return" for r in audit))
        self.assertNotIn("fictitious-test-password", json.dumps(audit))
        self.assertNotIn(self.operator["Cookie"], json.dumps(audit))
        privacy.erase_subject("u1", True)
        serialized = json.dumps(database.rows("SELECT * FROM security_audit"))
        self.assertNotIn("operator-test", serialized)
        self.assertNotIn('"u1"', serialized)


if __name__ == "__main__":
    unittest.main()
