import os
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import app_runtime
from app_version import VERSION
from launcher import prepare_server


class PackagedRuntimeTest(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.storage = Path(directory.name)
        self.database = self.storage / "test.db"

    def test_frozen_server_is_explicit_not_recursive_python_invocation(self):
        with patch("launcher.is_frozen", return_value=True), \
                patch("launcher.sys.executable", "C:\\App\\LoanInventory.exe"):
            command, _, _, _ = prepare_server("simulation", "", "", "8123", self.storage)
        self.assertEqual(command, ["C:\\App\\LoanInventory.exe", "--server", "--port", "8123"])

    def test_development_server_still_uses_main(self):
        with patch("launcher.is_frozen", return_value=False):
            command, _, _, _ = prepare_server("simulation", "", "", "8123", self.storage)
        self.assertEqual(command[1], "-B")
        self.assertEqual(Path(command[2]).name, "main.py")

    def test_frozen_default_database_is_outside_program_files(self):
        with patch("app_runtime.is_frozen", return_value=True), \
                patch.dict(os.environ, {"LOCALAPPDATA": str(self.storage)}):
            self.assertEqual(app_runtime.default_database(),
                             self.storage / "LoanInventoryLauncher" / "data" / "inventory.db")
        with patch("app_runtime.is_frozen", return_value=False):
            self.assertEqual(app_runtime.default_database(),
                             Path(app_runtime.__file__).parent / "data" / "inventory.db")

    def test_backup_is_consistent_unique_and_keeps_original(self):
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute("CREATE TABLE sentinel(value TEXT)")
            connection.execute("INSERT INTO sentinel VALUES ('synthetic data')")
        original = self.database.read_bytes()
        with patch("app_runtime.is_frozen", return_value=True):
            first = app_runtime.backup_before_migration(self.database)
            second = app_runtime.backup_before_migration(self.database)
        self.assertNotEqual(first, second)
        self.assertIn(VERSION, first.name)
        self.assertEqual(first.parent, self.storage / "backups")
        self.assertEqual(self.database.read_bytes(), original)
        with closing(sqlite3.connect(first)) as connection:
            self.assertEqual(connection.execute("SELECT value FROM sentinel").fetchone()[0], "synthetic data")
            self.assertEqual(connection.execute("PRAGMA quick_check").fetchone()[0], "ok")

    def test_empty_or_development_database_is_not_backed_up(self):
        self.database.touch()
        with patch("app_runtime.is_frozen", return_value=True):
            self.assertIsNone(app_runtime.backup_before_migration(self.database))
        self.database.write_bytes(b"not a database")
        with patch("app_runtime.is_frozen", return_value=False):
            self.assertIsNone(app_runtime.backup_before_migration(self.database))
        self.assertFalse((self.storage / "backups").exists())

    def test_invalid_database_backup_fails_without_replacing_original(self):
        self.database.write_bytes(b"not a database")
        with patch("app_runtime.is_frozen", return_value=True):
            with self.assertRaises(sqlite3.DatabaseError):
                app_runtime.backup_before_migration(self.database)
        self.assertEqual(self.database.read_bytes(), b"not a database")
        self.assertEqual(list((self.storage / "backups").iterdir()), [])

    def test_failed_backup_prevents_schema_migration(self):
        from backend import database
        with patch.object(database, "DATABASE_PATH", self.database), \
                patch.object(database, "backup_before_migration", side_effect=PermissionError("backup denied")), \
                patch.object(database, "connect") as connect:
            with self.assertRaises(PermissionError):
                database.initialize_database()
            connect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
