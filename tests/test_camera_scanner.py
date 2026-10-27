import unittest
from contextlib import ExitStack, redirect_stdout
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from hardware.razer_camera.scanner import ScanFilter, decode_frame, main, open_camera, run_scanner, scan_once


class ScanFilterTests(unittest.TestCase):
    def test_stable_read_preserves_id_and_suppresses_duplicates(self):
        scanner = ScanFilter()
        self.assertEqual(scanner.update(['00123'], 0), [])
        self.assertEqual(scanner.update(['00123'], 0.1), ['00123'])
        self.assertEqual(scanner.update(['00123'], 0.2), [])
        self.assertEqual(scanner.update(['00123'], 0.9), [])
        scanner.update([], 1.0)
        self.assertEqual(scanner.update(['00123'], 1.2), [])
        scanner.update([], 2.3)
        self.assertEqual(scanner.update(['00123'], 2.4), [])
        self.assertEqual(scanner.update(['00123'], 2.5), ['00123'])

    def test_new_id_and_flicker(self):
        scanner = ScanFilter()
        scanner.update(['12345'], 0)
        self.assertEqual(scanner.update(['99999'], 0.1), [])
        self.assertEqual(scanner.update(['99999'], 0.2), ['99999'])
        self.assertEqual(scanner.update(['ID-12'], 0.3), [])
        self.assertEqual(scanner.update(['ID-12'], 0.4), ['ID-12'])


class CameraLifecycleTests(unittest.TestCase):
    def test_failed_capture_released_before_backend_fallback(self):
        cv = Mock()
        bad, good = Mock(), Mock()
        bad.isOpened.return_value = True
        bad.read.return_value = (False, None)
        good.isOpened.return_value = True
        frame = object()
        good.read.return_value = (True, frame)
        cv.VideoCapture.side_effect = [bad, good]
        with patch('sys.platform', 'win32'):
            camera, result = open_camera(cv, 1, 'auto')
        self.assertIs(camera, good)
        self.assertIs(result, frame)
        bad.release.assert_called_once()

    def test_camera_released_if_decoder_fails(self):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest('Install camera requirements for lifecycle verification')
        camera = Mock()
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        with patch('hardware.razer_camera.scanner.open_camera', return_value=(camera, frame)), \
             patch.object(cv2, 'namedWindow'), patch.object(cv2, 'resizeWindow'), \
             patch.object(cv2, 'destroyAllWindows') as close, \
             patch('hardware.razer_camera.scanner.decode_frame', side_effect=RuntimeError('test')):
            with self.assertRaises(RuntimeError):
                run_scanner()
        camera.release.assert_called_once()
        close.assert_called_once()


class BarcodeTests(unittest.TestCase):
    def test_actual_code128_including_rotation_and_leading_zeroes(self):
        try:
            import numpy as np
            import zxingcpp
        except ImportError:
            self.skipTest('Install camera requirements for real barcode verification')
        for value in ['12345', '00123', 'ID-12345']:
            with self.subTest(value=value):
                code = zxingcpp.create_barcode(value, zxingcpp.BarcodeFormat.Code128)
                image = np.asarray(code.to_image(scale=4))
                for frame in [image, np.rot90(image).copy()]:
                    self.assertEqual([r.text for r in decode_frame(frame)], [value])
        self.assertEqual(decode_frame(np.full((100, 200), 255, dtype=np.uint8)), [])


class SingleScanTests(unittest.TestCase):
    def simulate_scan(self, frames, key=-1):
        try:
            import cv2
            import numpy as np
        except ImportError:
            self.skipTest('Install camera requirements for lifecycle verification')
        camera = Mock()
        frame = np.zeros((100, 200, 3), dtype=np.uint8)
        camera.read.return_value = (True, frame.copy())
        point = SimpleNamespace(x=5, y=5)
        position = SimpleNamespace(top_left=point, top_right=point,
                                   bottom_right=point, bottom_left=point)
        results = [[SimpleNamespace(text=text, position=position) for text in values]
                   for values in frames]
        with ExitStack() as stack:
            stack.enter_context(patch('hardware.razer_camera.scanner.open_camera',
                                      return_value=(camera, frame)))
            stack.enter_context(patch('hardware.razer_camera.scanner.decode_frame', side_effect=results))
            for name in ('namedWindow', 'resizeWindow', 'imshow'):
                stack.enter_context(patch.object(cv2, name))
            stack.enter_context(patch.object(cv2, 'waitKey', return_value=key))
            stack.enter_context(patch.object(cv2, 'getWindowProperty', return_value=1))
            close = stack.enter_context(patch.object(cv2, 'destroyAllWindows'))
            stdout = stack.enter_context(redirect_stdout(StringIO()))
            result = scan_once(camera_index=1, backend='dshow')
        camera.release.assert_called_once()
        close.assert_called_once()
        self.assertEqual(stdout.getvalue(), '')
        return result

    def test_returns_exact_id_and_releases_camera(self):
        self.assertEqual(self.simulate_scan([['00123'], ['00123']]), '00123')

    def test_cancel_does_not_return_stale_id(self):
        self.assertIsNone(self.simulate_scan([['12345']], key=27))

    def test_multiple_codes_require_single_unambiguous_scan(self):
        self.assertEqual(self.simulate_scan([
            ['12345', '99999'], ['12345', '99999'], ['ID-12'], ['ID-12'],
        ]), 'ID-12')

    def test_cli_prints_once_and_reports_cancel(self):
        try:
            import cv2, zxingcpp
        except ImportError:
            self.skipTest('Install camera requirements for CLI verification')
        for value, status in [('00123', 0), (None, 2)]:
            with self.subTest(value=value), \
                 patch('hardware.razer_camera.scanner.scan_once', return_value=value), \
                 redirect_stdout(StringIO()) as stdout:
                self.assertEqual(main(['--once', '--camera', '1']), status)
                self.assertEqual(stdout.getvalue(), '00123\n' if value else '')


if __name__ == '__main__':
    unittest.main()
