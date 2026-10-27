import gc
import json
from pathlib import Path
import socket
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

from launcher import Launcher
from app_version import RELEASES_URL


class LauncherWindowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import tkinter
            root = tkinter.Tk()
        except (ImportError, RuntimeError) as error:
            raise unittest.SkipTest(f"Tkinter unavailable: {error}")
        except tkinter.TclError as error:
            raise unittest.SkipTest(f"Tk display unavailable: {error}")
        root.destroy()

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.storage = Path(temporary.name)
        storage_patch = patch("launcher.storage_directory", return_value=self.storage)
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        errors = patch("tkinter.messagebox.showerror")
        self.errors = errors.start()
        self.addCleanup(errors.stop)
        browser = patch("launcher.webbrowser.open", return_value=True)
        self.browser = browser.start()
        self.addCleanup(browser.stop)
        self.app = Launcher()
        self.app.root.withdraw()
        self.addCleanup(self.cleanup_window)

    def cleanup_window(self):
        self.app.stop()
        self.app.root.destroy()
        self.app = None
        self.errors.reset_mock()
        self.browser.reset_mock()
        # Tcl objects must be finalized on this thread, not a later HTTP worker.
        gc.collect()

    def test_compact_modes_custom_icon_and_read_only_bounded_console(self):
        self.assertFalse(hasattr(self.app, "remote_entry"))
        self.assertEqual(self.app.icon.width(), 32)
        self.assertEqual(self.app.console.cget("state"), "disabled")
        self.app.append_log("rad\n" * 1500)
        self.assertLessEqual(int(self.app.console.index("end-1c").split(".")[0]), 1000)
        self.app.append_log("x" * 150000)
        self.assertLessEqual(len(self.app.console.get("1.0", "end-1c")), 100000)
        self.assertEqual(self.app.console.cget("state"), "disabled")

    def test_release_button_opens_only_browser_and_fits_minimum_window(self):
        self.app.root.deiconify()
        self.app.root.geometry("600x650")
        self.app.tabs.select(self.app.settings_tab)
        self.app.root.update()
        self.assertTrue(self.app.updates_button.winfo_ismapped())
        self.assertEqual(self.app.updates_button.winfo_width(), self.app.updates_button.winfo_reqwidth())
        self.assertGreater(self.app.updates_button.winfo_height(), 15)
        self.app.tabs.select(self.app.log_tab)
        self.app.root.update()
        self.assertLess(self.app.console.winfo_rooty() + self.app.console.winfo_height(),
                        self.app.root.winfo_rooty() + self.app.root.winfo_height())
        self.app.updates_button.invoke()
        self.browser.assert_called_once_with(RELEASES_URL)
        self.assertIsNone(self.app.process)
        self.errors.assert_not_called()

    def test_compact_start_tab_and_mode_specific_settings(self):
        self.app.root.deiconify()
        self.app.root.update()
        self.assertEqual(self.app.tabs.select(), str(self.app.start_tab))
        self.assertLess(self.app.root.winfo_height(), 400)
        self.app.tabs.select(self.app.settings_tab)
        for mode, database, network, simulation in (
                ("local", True, False, False),
                ("lan", True, True, False),
                ("simulation", False, False, True)):
            with self.subTest(mode=mode):
                self.app.mode.set(mode)
                self.app.update_fields()
                self.app.root.update()
                self.assertEqual(bool(self.app.database_section.winfo_ismapped()), database)
                self.assertEqual(bool(self.app.network_section.winfo_ismapped()), network)
                self.assertEqual(bool(self.app.simulation_section.winfo_ismapped()), simulation)

    def test_release_browser_failure_reports_manual_url(self):
        self.browser.return_value = False
        self.app.updates_button.invoke()
        self.errors.assert_called_once()
        self.assertIn(RELEASES_URL, str(self.errors.call_args))

    def test_old_remote_preferences_migrate_to_local(self):
        (self.storage / "preferences.json").write_text(
            json.dumps({"mode": "remote", "remote": "http://old-server", "port": "8001"}), encoding="utf-8")
        self.app.load_preferences()
        self.assertEqual(self.app.mode.get(), "local")
        self.assertEqual(self.app.port.get(), "8001")
        self.assertIn("tagits bort", self.app.console.get("1.0", "end"))
        self.app.save_preferences()
        self.assertNotIn("remote", json.loads((self.storage / "preferences.json").read_text(encoding="utf-8")))

    def test_log_tailing_reads_new_bytes_only_and_handles_split_utf8(self):
        self.app.log_path = self.storage / "server.log"
        self.app.log_path.write_bytes(b"Start\n\xc3")
        self.app.read_log()
        self.app.read_log()
        with self.app.log_path.open("ab") as log:
            log.write(b"\xa5ter\n")
        self.app.read_log()
        text = self.app.console.get("1.0", "end")
        self.assertEqual(text.count("Start"), 1)
        self.assertIn("åter", text)
        self.assertNotIn("\ufffd", text)

    def test_unresponsive_health_and_recovery_are_visible(self):
        self.app.process = Mock()
        self.app.process.poll.return_value = None
        self.app.instance_id = "current"
        self.app.probe_pending = True
        self.app.health_results.put(("old-instance", 1.0, ""))
        self.app.health_results.put(("current", None, "timed out"))
        self.app.check_process()
        self.assertIn("Svarar inte", self.app.status.get())
        self.assertIn("timed out", self.app.console.get("1.0", "end"))
        self.app.root.after_cancel(self.app.check_id)
        self.app.health_results.put(("current", 12.3, ""))
        self.app.check_process()
        self.assertIn("Svarstid 12 ms", self.app.status.get())
        self.assertIn("Servern svarar", self.app.console.get("1.0", "end"))
        self.browser.assert_not_called()

    def test_server_exit_reports_error_and_keeps_log(self):
        self.app.process = Mock()
        self.app.process.poll.return_value = 1
        self.app.log_path = self.storage / "server.log"
        self.app.log_path.write_text("Startup error\n", encoding="utf-8")
        self.app.check_process()
        self.assertIsNone(self.app.process)
        self.errors.assert_called_once()
        self.assertIn("Startup error", self.app.console.get("1.0", "end"))
        self.assertEqual(str(self.app.start_button.cget("state")), "normal")

    def test_actual_simulation_has_live_logs_latency_and_stops(self):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        self.app.port.set(str(port))
        self.app.start()
        process = self.app.process
        self.assertIsNotNone(process)
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            self.app.root.update()
            if self.app.deadline == 0 and "Svarstid" in self.app.status.get():
                break
            time.sleep(0.05)
        self.assertIn("Svarstid", self.app.status.get())
        # Let the next log-tail tick collect the completed health request.
        self.app.read_log()
        self.assertIn("[HTTP] GET 200", self.app.console.get("1.0", "end"))
        self.browser.assert_called_once()
        self.errors.assert_not_called()
        self.app.stop()
        self.assertIsNotNone(process.poll())
        self.assertEqual(self.app.status.get(), "Stoppad")
        self.assertIsNone(self.app.check_id)


if __name__ == "__main__":
    unittest.main()
