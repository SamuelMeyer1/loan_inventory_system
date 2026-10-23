import json
import io
import os
from datetime import date, timedelta
from pathlib import Path
import socket
import subprocess
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import Request, ProxyHandler, build_opener

from launcher import prepare_server, probe_server, ROOT, MODES
from backend import database
from backend.server import run_server
from backend.services import notifications, smartcard


class LauncherConfigTest(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        self.database = self.storage / "existing.db"
        self.database.write_bytes(b"Do not replace this file")

    def test_simulation_ignores_selected_database_and_inherited_settings(self):
        original = self.database.read_bytes()
        with patch.dict(os.environ, {
            "LOAN_HOST": "10.1.2.3", "LOAN_ALLOW_LAN": "1",
            "LOAN_DATABASE_PATH": str(self.database), "LOAN_ENABLE_NOTIFICATIONS": "1",
        }):
            first = prepare_server("simulation", str(self.database), "10.1.2.3", "8001", self.storage)
            second = prepare_server("simulation", str(self.database), "", "8001", self.storage)
            self.assertEqual(os.environ["LOAN_HOST"], "10.1.2.3")
        command, env, url, path = first
        self.assertEqual(path.stat().st_size, 0)
        self.assertNotEqual(path, second[3])
        self.assertEqual(path.parent, self.storage / "simulations")
        self.assertEqual(self.database.read_bytes(), original)
        self.assertEqual(env["LOAN_HOST"], "127.0.0.1")
        self.assertEqual(env["LOAN_ALLOW_LAN"], "0")
        self.assertEqual(env["LOAN_ENABLE_NOTIFICATIONS"], "0")
        self.assertEqual(env["LOAN_LOCAL_ADMIN_PASSWORD"], "admin")
        self.assertEqual(env["LOAN_LOCAL_SUPERADMIN_PASSWORD"], "superadmin")
        self.assertEqual(env["LOAN_SIMULATION"], "1")
        self.assertEqual(url, "http://127.0.0.1:8001/")
        self.assertEqual(command[-2:], ["--port", "8001"])

    def test_normal_launch_resets_simulation_and_keeps_selected_database(self):
        with patch.dict(os.environ, {"LOAN_LOCAL_ADMIN_PASSWORD": "inherited",
                                     "LOAN_SIMULATION": "1", "LOAN_SEED_DEMO": "1",
                                     "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "1"}):
            _, env, url, path = prepare_server("local", str(self.database), "10.1.1.1", "8000", self.storage)
        self.assertEqual(path, self.database.resolve())
        self.assertEqual(path.read_bytes(), b"Do not replace this file")
        for flag in ("LOAN_SIMULATION", "LOAN_ALLOW_LAN", "LOAN_SEED_DEMO", "LOAN_LOCAL_FIXED_TEST_CREDENTIALS"):
            self.assertEqual(env[flag], "0")
        self.assertNotIn("LOAN_LOCAL_ADMIN_PASSWORD", env)
        self.assertEqual(url, "http://127.0.0.1:8000/")

    def test_lan_mode_is_explicit_and_private(self):
        _, env, url, _ = prepare_server("lan", str(self.database), "192.168.1.25", "8000", self.storage)
        self.assertEqual(env["LOAN_ALLOW_LAN"], "1")
        self.assertEqual(env["LOAN_LOCAL_FIXED_TEST_CREDENTIALS"], "0")
        self.assertEqual(url, "http://192.168.1.25:8000/")
        for host in ("0.0.0.0", "127.0.0.1", "8.8.8.8", "localhost", "::"):
            with self.subTest(host=host), self.assertRaises(ValueError):
                prepare_server("lan", str(self.database), host, "8000", self.storage)

    def test_invalid_configuration_does_not_create_simulation(self):
        for port in ("", "abc", "0", "-1", "65536"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                prepare_server("simulation", "", "", port, self.storage)
        self.assertFalse((self.storage / "simulations").exists())
        with self.assertRaises(ValueError):
            prepare_server("local", str(self.storage / "missing.db"), "", "8000", self.storage)
        with self.assertRaises(ValueError):
            prepare_server("unknown", "", "", "8000", self.storage)

    def test_only_local_lan_and_simulation_modes_remain(self):
        self.assertEqual(set(MODES), {"local", "lan", "simulation"})
        with self.assertRaises(ValueError):
            prepare_server("remote", "", "", "8000", self.storage)

    def test_health_probe_verifies_instance_and_measures_round_trip(self):
        with patch("launcher.build_opener") as opener, \
                patch("launcher.time.perf_counter", side_effect=[10, 10.012]):
            opener.return_value.open.return_value = io.BytesIO(b'{"data":{"instance_id":"test"}}')
            self.assertAlmostEqual(probe_server("http://127.0.0.1:8000/", "test"), 12)
            opener.return_value.open.assert_called_once_with("http://127.0.0.1:8000/api/runtime", timeout=5)
        for data in ({"data": {"instance_id": "other"}}, {"data": []}, []):
            with self.subTest(data=data), patch("launcher.build_opener") as opener:
                opener.return_value.open.return_value = io.BytesIO(json.dumps(data).encode())
                with self.assertRaisesRegex(ValueError, "annan server"):
                    probe_server("http://127.0.0.1:8000/", "test")

    def test_simulation_refuses_existing_data_before_migration(self):
        with patch.dict(os.environ, {"LOAN_SIMULATION": "1", "LOAN_DATABASE_PATH": str(self.database)}), \
                patch.object(database, "DATABASE_PATH", self.database), \
                patch("backend.server.initialize_database") as initialize:
            with self.assertRaisesRegex(ValueError, "ny tom separat"):
                run_server("127.0.0.1")
            initialize.assert_not_called()
        self.assertEqual(self.database.read_bytes(), b"Do not replace this file")

    def test_simulation_refuses_lan_before_migration(self):
        with patch.dict(os.environ, {"LOAN_SIMULATION": "1", "LOAN_ALLOW_LAN": "1"}), \
                patch("backend.server.initialize_database") as initialize:
            with self.assertRaisesRegex(ValueError, "endast.*lokalt"):
                run_server("10.1.2.3")
            initialize.assert_not_called()

    def test_busy_port_does_not_migrate_database(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            with patch.dict(os.environ, {"LOAN_SIMULATION": "0", "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "0"}), \
                    patch("backend.server.initialize_database") as initialize:
                with self.assertRaises(OSError):
                    run_server("127.0.0.1", occupied.getsockname()[1])
                initialize.assert_not_called()

    def test_simulation_blocks_real_transports_even_when_enabled(self):
        with patch.dict(os.environ, {"LOAN_SIMULATION": "1", "LOAN_ENABLE_NOTIFICATIONS": "1"}), \
                patch("smtplib.SMTP") as smtp:
            for send in (notifications.email_msg, notifications.team_msg):
                with self.assertRaisesRegex(ValueError, "Simuleringsmiljön"):
                    send("test", "test", ["nobody@example.invalid"])
            with self.assertRaisesRegex(ValueError, "Simuleringsmiljön"):
                notifications.raw_smtp_message("localhost", 25, "a", "b", "subject", "body", "localhost")
            with self.assertRaisesRegex(ValueError, "avstängd"):
                smartcard.read_card_uid()
            smtp.assert_not_called()


class SimulationServerTest(unittest.TestCase):
    def test_real_server_login_checkout_return_and_logout(self):
        with tempfile.TemporaryDirectory() as directory:
            storage = Path(directory)
            # Port zero lets the operating system allocate an unused test port.
            command, env, _, database_path = prepare_server("simulation", "", "", "8000", storage)
            command[-1] = "0"
            log_path = storage / "server.log"
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            try:
                deadline = time.monotonic() + 20
                url = ""
                while time.monotonic() < deadline:
                    text = log_path.read_text(encoding="utf-8", errors="replace")
                    if "running at " in text:
                        url = text.split("running at ", 1)[1].splitlines()[0] + "/"
                        break
                    if process.poll() is not None:
                        self.fail(text)
                    time.sleep(0.05)
                self.assertTrue(url, log_path.read_text(encoding="utf-8", errors="replace"))
                opener = build_opener(ProxyHandler({}))

                def call(path, payload=None, cookie="", csrf=""):
                    headers = {"X-Loan-Client": "browser", "Content-Type": "application/json",
                               "Cookie": cookie, "X-CSRF-Token": csrf}
                    request = Request(url + path, data=None if payload is None else json.dumps(payload).encode(),
                                      headers=headers)
                    with opener.open(request, timeout=3) as response:
                        return json.load(response)["data"], response.headers

                runtime, _ = call("api/runtime")
                self.assertEqual(runtime, {"simulation": True, "instance_id": env["LOAN_INSTANCE_ID"]})
                guest, _ = call("api/auth/session")
                self.assertTrue(guest["anonymous"])
                users, _ = call("api/users")
                self.assertEqual(len(users), 4)
                objects, _ = call("api/objects")
                self.assertEqual(len(objects), 8)
                for username in ("admin", "superadmin"):
                    identity, headers = call("api/auth/login", {"username": username, "password": username})
                    cookie = headers["Set-Cookie"].split(";", 1)[0]
                    session, _ = call("api/auth/session", cookie=cookie)
                    self.assertEqual(session["role"], username)
                    if username == "admin":
                        loan, _ = call("api/checkout", {
                            "user_id": "USR-001", "object_id": "OBJ-1001", "quantity": 1,
                            "lending_date": date.today().isoformat(),
                            "due_time": (date.today() + timedelta(days=1)).isoformat(),
                        }, cookie, identity["csrf"])
                        stock, _ = call("api/objects", cookie=cookie)
                        self.assertEqual(next(item for item in stock if item["object_id"] == "OBJ-1001")["available_quantity"], 3)
                        returned, _ = call("api/return", {"user_id": "USR-001", "loan_ids": [loan["loan_id"]]},
                                           cookie, identity["csrf"])
                        self.assertEqual(returned["loan_ids"], [loan["loan_id"]])
                        stock, _ = call("api/objects", cookie=cookie)
                        self.assertEqual(next(item for item in stock if item["object_id"] == "OBJ-1001")["available_quantity"], 4)
                    call("api/auth/logout", {}, cookie, identity["csrf"])
                    guest, _ = call("api/auth/session", cookie=cookie)
                    self.assertTrue(guest["anonymous"])
                self.assertGreater(database_path.stat().st_size, 0)
                self.assertFalse((storage / "inventory.db").exists())
                log_text = log_path.read_text(encoding="utf-8")
                self.assertRegex(log_text, r"\[HTTP\] GET 200 \d+\.\d ms")
                self.assertRegex(log_text, r"\[HTTP\] POST 200 \d+\.\d ms")
                for private_text in ("USR-001", "OBJ-1001", "superadmin", "loan_session", "csrf"):
                    self.assertNotIn(private_text, log_text)
            finally:
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)


if __name__ == "__main__":
    unittest.main()
