"""Run with python -m hardware.razer_camera.scanner (or run this file)."""

import argparse
import sys
import time


WINDOW = "Kiyo - barcode scanner (Q / Esc avslutar)"


class ScanFilter:
    """Require two matching frames and rearm only after a code leaves view."""

    def __init__(self, rearm_seconds=1.0):
        self.rearm_seconds = rearm_seconds
        self.previous = set()
        self.last_seen = {}
        self.reported = set()

    def update(self, values, now):
        current = set(values)
        for value, seen in list(self.last_seen.items()):
            if now - seen >= self.rearm_seconds:
                self.reported.discard(value)
                del self.last_seen[value]
        ready = sorted(current & self.previous - self.reported)
        self.reported.update(ready)
        self.last_seen.update({value: now for value in current})
        self.previous = current
        return ready


def decode_frame(frame):
    """Decode original strings, preserving prefixes and leading zeroes."""
    import zxingcpp

    return zxingcpp.read_barcodes(
        frame, formats=zxingcpp.BarcodeFormat.Code128, try_rotate=True,
    )


def open_camera(cv2, index, backend):
    backends = {
        "auto": [cv2.CAP_DSHOW, cv2.CAP_MSMF] if sys.platform == "win32" else [cv2.CAP_ANY],
        "dshow": [cv2.CAP_DSHOW],
        "msmf": [cv2.CAP_MSMF],
    }
    for api in backends[backend]:
        camera = cv2.VideoCapture(index, api)
        if camera.isOpened():
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            ok, first_frame = camera.read()
            if ok and first_frame is not None:
                return camera, first_frame
        camera.release()
    raise RuntimeError(
        f"Kunde inte läsa kamera {index}. Stäng Teams/andra kameraappar, kontrollera "
        "Windows kamerabehörigheter eller prova --camera 1 (eller 2)."
    )


def _scan_loop(camera_index=0, backend="auto", once=False):
    import cv2

    camera = None
    try:
        camera, frame = open_camera(cv2, camera_index, backend)
        print(
            f"Kamera {camera_index} startad ({frame.shape[1]}x{frame.shape[0]}). "
            "Visa en Code 128-kod. Q / Esc avslutar. ID skrivs i terminalen.",
            file=sys.stderr, flush=True,
        )
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(WINDOW, 960, 540)
        scan_filter = ScanFilter()
        last_value = "Vantar pa streckkod..."
        while True:
            results = decode_frame(frame)
            values = {r.text for r in results if r.text}
            # A single-scan request must not arbitrarily pick between two items.
            if once and len(values) > 1:
                values = set()
                last_value = "Visa endast en streckkod"
            for value in scan_filter.update(values, time.monotonic()):
                if once:
                    return value
                print(value, flush=True)
                last_value = f"Senast: {value}"
            # Decode before drawing so the overlay cannot obscure barcode pixels.
            for result in results:
                p = result.position
                corners = [p.top_left, p.top_right, p.bottom_right, p.bottom_left]
                for start, end in zip(corners, corners[1:] + corners[:1]):
                    cv2.line(frame, (start.x, start.y), (end.x, end.y), (0, 255, 0), 2)
            cv2.putText(frame, last_value[:90], (15, 30), cv2.FONT_HERSHEY_SIMPLEX,
                        0.7, (0, 255, 0), 2)
            cv2.imshow(WINDOW, frame)
            if cv2.waitKey(1) & 0xFF in (27, ord("q"), ord("Q")):
                return None
            if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                return None
            ok, frame = camera.read()
            if not ok or frame is None:
                raise RuntimeError("Kamerabilden avbröts. Kontrollera USB-anslutningen och starta igen.")
    finally:
        if camera is not None:
            camera.release()
        cv2.destroyAllWindows()


def run_scanner(camera_index=0, backend="auto"):
    """Continuous terminal mode; return an exit code when the user closes it."""
    _scan_loop(camera_index, backend)
    return 0


def scan_once(camera_index=0, backend="auto") -> str | None:
    """Open camera on demand and return one confirmed ID, or None on cancel.

    Blocks until a scan or Q/Esc/window close. The camera is released before
    returning. Hardware/decoder errors propagate to the caller. Importing this
    module never opens the camera. Call from a desktop application's main thread.
    """
    if camera_index < 0 or backend not in ("auto", "dshow", "msmf"):
        raise ValueError("Ogiltigt kameraindex eller backend.")
    try:
        return _scan_loop(camera_index, backend, once=True)
    except KeyboardInterrupt:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description="Läs Code 128-ID med Razer Kiyo/USB-kamera.")
    parser.add_argument("--camera", type=int, default=0, help="Kameraindex, standard 0. Prova 1 för extern kamera.")
    parser.add_argument("--backend", choices=["auto", "dshow", "msmf"], default="auto")
    parser.add_argument("--once", action="store_true", help="Läs ett ID och stäng kameran automatiskt.")
    args = parser.parse_args(argv)
    if args.camera < 0:
        parser.error("Kameraindex måste vara 0 eller högre.")
    try:
        import cv2
        import zxingcpp
    except ImportError:
        print("Installera kamerastödet först:\npython -m pip install -r "
              "hardware/razer_camera/requirements.txt", file=sys.stderr)
        return 1
    try:
        if args.once:
            scanned_id = scan_once(args.camera, args.backend)
            if scanned_id is None:
                print("Skanning avbruten utan ID.", file=sys.stderr)
                return 2
            print(scanned_id, flush=True)
            return 0
        return run_scanner(args.camera, args.backend)
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, cv2.error) as error:
        print(f"Kamerafel: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
