import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from http_client import login

from backend import database
from backend.server import AppHandler
from backend.services import notifications


class SystemSettingsSecurityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path_patch = patch.object(database, "DATABASE_PATH", Path(self.temp.name) / "test.db")
        self.path_patch.start()
        self.addCleanup(self.path_patch.stop)
        database.initialize_database()
        with database.connect() as db:
            db.executemany(
                "INSERT INTO system_settings (key, value, updated_at) VALUES (?, ?, '2026-10-01 00:00:00')",
                [
                    ("smtp_password", "existing-secret"),
                    ("notification_simulation_recipient", "test@example.com"),
                ],
            )

    def test_public_api_never_returns_smtp_password(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), AppHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        headers = login(server)
        with urlopen(Request(f"http://127.0.0.1:{server.server_port}/api/system-settings", headers=headers)) as response:
            payload = json.load(response)
            self.assertEqual(response.headers["Cache-Control"], "no-store")

        settings = payload["data"]
        self.assertNotIn("smtp_password", settings)
        self.assertTrue(settings["smtp_password_configured"])

    def test_empty_password_keeps_existing_secret_and_redacts_response(self):
        response = notifications.update_system_settings({"smtp_password": ""})

        stored = database.row("SELECT value FROM system_settings WHERE key = ?", ("smtp_password",))
        self.assertEqual(stored["value"], "existing-secret")
        self.assertNotIn("smtp_password", response)
        self.assertTrue(response["smtp_password_configured"])

    def test_new_password_is_stored_but_not_returned(self):
        response = notifications.update_system_settings({"smtp_password": "replacement-secret"})

        stored = database.row("SELECT value FROM system_settings WHERE key = ?", ("smtp_password",))
        self.assertEqual(stored["value"], "replacement-secret")
        self.assertNotIn("smtp_password", response)
        self.assertTrue(response["smtp_password_configured"])


if __name__ == "__main__":
    unittest.main()
