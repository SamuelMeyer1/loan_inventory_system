import io
import json
import ssl
import truststore
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from app_updates import MAX_METADATA_BYTES, Release, UpdateCheck, check_for_updates, version_numbers
from app_version import RELEASES_URL
from launcher import Launcher


def release_data(version="1.19.0"):
    filename = f"LoanInventory-{version}-Setup.exe"
    return {
        "tag_name": f"v{version}", "draft": False, "prerelease": False,
        "published_at": "2026-10-26T08:00:00Z", "body": "Test release",
        "assets": [{"name": filename, "state": "uploaded", "size": 15000000,
                    "browser_download_url": f"{RELEASES_URL}/download/v{version}/{filename}"}],
    }


class UpdateMetadataTest(unittest.TestCase):
    def test_native_certificate_verification_and_hostname_checks_are_required(self):
        with patch("app_updates.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(release_data()).encode())
            check_for_updates("1.18.0")
            handler = opener.call_args.args[0]
            context = handler._context
            self.assertIsInstance(context, truststore.SSLContext)
            self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
            self.assertTrue(context.check_hostname)

    def test_certificate_failure_is_not_retried_without_verification(self):
        with patch("app_updates.build_opener") as opener:
            opener.return_value.open.side_effect = URLError(
                ssl.SSLCertVerificationError(1, "unable to get local issuer certificate"))
            with self.assertRaisesRegex(ValueError, "Certifikatkontrollen är fortfarande påslagen"):
                check_for_updates()
            opener.return_value.open.assert_called_once()

    def fetch(self, data, current="1.18.0"):
        with patch("app_updates.build_opener") as opener:
            opener.return_value.open.return_value = io.BytesIO(json.dumps(data).encode())
            result = check_for_updates(current)
            request = opener.return_value.open.call_args.args[0]
            self.assertNotIn("Authorization", request.headers)
            self.assertEqual(opener.return_value.open.call_args.kwargs["timeout"], 10)
            return result

    def test_numeric_versions_and_newer_release(self):
        result = self.fetch(release_data("1.19.0"), current="1.9.9")
        assert result.available is not None
        self.assertEqual(result.available.version, "1.19.0")
        self.assertEqual(result.available.notes, "Test release")
        self.assertTrue(result.available.download_url.endswith("/LoanInventory-1.19.0-Setup.exe"))
        for version in ("1.18.0", "1.17.9"):
            self.assertIsNone(self.fetch(release_data(version)).available)
        for value in ("1.18", "1.18.0-beta", "../1.18.0", "1.18.0\n", "v1.18.0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                version_numbers(value)

    def test_patch_release_is_offered_only_to_older_installation(self):
        for old, new in (("1.18.0", "1.18.1"), ("1.18.2", "1.18.3")):
            with self.subTest(old=old, new=new):
                result = self.fetch(release_data(new), current=old)
                assert result.available is not None
                self.assertEqual(result.available.version, new)
                self.assertEqual(result.available.download_url,
                                 f"{RELEASES_URL}/download/v{new}/LoanInventory-{new}-Setup.exe")
                self.assertIsNone(self.fetch(release_data(new), current=new).available)

    def test_first_release_missing_and_network_errors(self):
        with patch("app_updates.build_opener") as opener:
            opener.return_value.open.side_effect = HTTPError("https://api.github.com", 404, "Not found", {}, None)
            self.assertEqual(check_for_updates(), UpdateCheck(None))
            for code in (403, 429, 500):
                opener.return_value.open.side_effect = HTTPError("https://api.github.com", code, "Error", {}, None)
                with self.subTest(code=code), self.assertRaisesRegex(ValueError, str(code)):
                    check_for_updates()
            opener.return_value.open.side_effect = URLError("offline")
            with self.assertRaises(URLError):
                check_for_updates()

    def test_invalid_metadata_and_unpublished_releases(self):
        for key, value in (("draft", True), ("prerelease", True), ("published_at", None),
                           ("tag_name", "v1.19.0-beta"), ("assets", None), ("body", False)):
            data = release_data()
            data[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.fetch(data)
        with self.assertRaises(ValueError):
            self.fetch([])
        for content in (b"not json", b"x" * (MAX_METADATA_BYTES + 1)):
            with patch("app_updates.build_opener") as opener, self.assertRaises(ValueError):
                opener.return_value.open.return_value = io.BytesIO(content)
                check_for_updates()

    def test_only_exact_published_production_installer_is_offered(self):
        for key, value in (
            ("name", "LoanInventory-1.19.0-TestSetup.exe"), ("name", "../Setup.exe"),
            ("browser_download_url", "https://example.invalid/Setup.exe"),
            ("browser_download_url", f"{RELEASES_URL}/download/v1.18.0/LoanInventory-1.19.0-Setup.exe"),
            ("state", "new"), ("size", 0), ("size", True), ("size", 513 * 1024 * 1024),
        ):
            data = release_data()
            data["assets"][0][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                self.fetch(data)
        data = release_data()
        data["assets"] *= 2
        with self.assertRaises(ValueError):
            self.fetch(data)


class UpdateLauncherTest(unittest.TestCase):
    def setUp(self):
        from queue import Queue
        self.app = Launcher.__new__(Launcher)
        self.app.root = Mock()
        self.app.update_results = Queue()
        self.app.update_status = Mock()
        self.app.status = Mock()
        self.app.check_updates_button = Mock()
        self.app.append_log = Mock()
        self.app.update_check_id = None
        self.app.update_check_running = False

    def receive(self, result, error=""):
        self.app.update_results.put((result, error))
        self.app.receive_update_check()

    def test_check_runs_in_worker_without_blocking_server_controls(self):
        with patch("launcher.Thread") as thread:
            self.app.check_updates()
            self.app.check_updates()
            self.assertEqual(thread.call_count, 1)
            self.app.status.set.assert_not_called()
            with patch("launcher.check_for_updates", return_value=UpdateCheck(None)):
                thread.call_args.kwargs["target"]()
        self.app.receive_update_check()
        self.assertFalse(self.app.update_check_running)
        self.app.check_updates_button.configure.assert_called_with(state="normal")

    def test_no_release_current_version_and_errors_do_not_prompt_or_change_server(self):
        with patch("tkinter.messagebox.askyesno") as ask, patch("launcher.webbrowser.open") as browser:
            self.receive(UpdateCheck(None))
            self.assertIn("Ingen publicerad", self.app.update_status.set.call_args.args[0])
            self.receive(UpdateCheck("1.18.0"))
            self.assertIn("Ingen nyare", self.app.update_status.set.call_args.args[0])
            self.receive(None, "offline")
            self.app.append_log.assert_called_with("[UPPDATERING FEL] offline\n")
            ask.assert_not_called()
            browser.assert_not_called()
            self.app.status.set.assert_not_called()

    def test_download_needs_consent_and_uses_only_verified_asset_link(self):
        release = Release("1.19.0", f"{RELEASES_URL}/download/v1.19.0/LoanInventory-1.19.0-Setup.exe", "Test notes")
        with patch("tkinter.messagebox.askyesno", return_value=False) as ask, \
                patch("launcher.webbrowser.open", return_value=True) as browser:
            self.receive(UpdateCheck(release.version, release))
            browser.assert_not_called()
            self.assertIn("BAT-startens", ask.call_args.args[1])
            ask.return_value = True
            self.receive(UpdateCheck(release.version, release))
            browser.assert_called_once_with(release.download_url)
            self.assertIn("Ingen installation", self.app.update_status.set.call_args.args[0])
            browser.return_value = False
            with patch("launcher.is_frozen", return_value=True):
                self.receive(UpdateCheck(release.version, release))
            self.assertNotIn("BAT-startens", ask.call_args.args[1])
            self.assertIn("Webbläsaren", self.app.append_log.call_args.args[0])

    def test_worker_error_is_displayed_and_pending_check_is_cancelled_on_close(self):
        with patch("launcher.Thread") as thread:
            self.app.check_updates()
            with patch("launcher.check_for_updates", side_effect=TimeoutError("timeout")):
                thread.call_args.kwargs["target"]()
        self.app.receive_update_check()
        self.assertIn("timeout", self.app.append_log.call_args.args[0])
        self.app.process = None
        self.app.update_check_id = "pending"
        self.app.close()
        self.app.root.after_cancel.assert_called_with("pending")
        self.app.root.destroy.assert_called_once()


if __name__ == "__main__":
    unittest.main()
