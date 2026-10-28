import threading
import unittest
from unittest.mock import Mock, patch

from backend.services import object_scanner


class ObjectScannerServiceTests(unittest.TestCase):
    def setUp(self):
        object_scanner._scan_lock = threading.Lock()
        object_scanner._process_lock = threading.Lock()
        object_scanner._active_process = None
        object_scanner._active_scan_id = None
        object_scanner._cancel_requested = False
        object_scanner._cancelled_scan_ids.clear()
        object_scanner._finished_scan_ids.clear()

    def test_scans_with_selected_python_camera_and_returns_code(self):
        process = Mock()
        process.communicate.return_value = ("12345\n", "")
        process.returncode = 0
        with patch.object(object_scanner.subprocess, "Popen", return_value=process) as start:
            result = object_scanner.scan_object_code(2, "scan-123")

        self.assertEqual(result, {"code": "12345", "cancelled": False})
        command = start.call_args.args[0]
        self.assertEqual(command[-2:], ["--camera", "2"])
        self.assertIn("--once", command)

    def test_rejects_invalid_camera_index_and_scan_id(self):
        with patch.object(object_scanner.subprocess, "Popen") as start:
            for camera_index, scan_id in ((9, "scan-1"), ("01", "scan-2"), (0, "bad id")):
                with self.subTest(camera_index=camera_index, scan_id=scan_id):
                    with self.assertRaises(ValueError):
                        object_scanner.scan_object_code(camera_index, scan_id)
        start.assert_not_called()

    def test_cancel_before_process_start_prevents_camera_launch(self):
        self.assertEqual(object_scanner.cancel_object_scan("scan-early"), {"cancelled": True})
        with patch.object(object_scanner.subprocess, "Popen") as start:
            result = object_scanner.scan_object_code(1, "scan-early")

        self.assertEqual(result, {"code": "", "cancelled": True})
        start.assert_not_called()

    def test_cancel_during_process_start_terminates_that_process(self):
        process = Mock()
        process.poll.return_value = None
        process.communicate.return_value = ("", "")
        process.returncode = -15
        process_starting = threading.Event()
        allow_process_start = threading.Event()
        scan_results = []

        def start_process(*args, **kwargs):
            process_starting.set()
            allow_process_start.wait(timeout=2)
            return process

        with patch.object(object_scanner.subprocess, "Popen", side_effect=start_process):
            scan_thread = threading.Thread(
                target=lambda: scan_results.append(object_scanner.scan_object_code(1, "scan-race")))
            scan_thread.start()
            self.assertTrue(process_starting.wait(timeout=2))
            cancel_thread = threading.Thread(target=object_scanner.cancel_object_scan, args=("scan-race",))
            cancel_thread.start()
            allow_process_start.set()
            scan_thread.join(timeout=2)
            cancel_thread.join(timeout=2)

        self.assertFalse(scan_thread.is_alive())
        self.assertFalse(cancel_thread.is_alive())
        self.assertEqual(scan_results, [{"code": "", "cancelled": True}])
        process.terminate.assert_called_once()

    def test_late_cancel_for_finished_scan_does_not_cancel_next_scan(self):
        process = Mock()
        process.communicate.return_value = ("12345\n", "")
        process.returncode = 0
        with patch.object(object_scanner.subprocess, "Popen", return_value=process):
            self.assertEqual(object_scanner.scan_object_code(0, "scan-finished")["code"], "12345")
            self.assertEqual(object_scanner.cancel_object_scan("scan-finished"), {"cancelled": False})


if __name__ == "__main__":
    unittest.main()
