from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import threading
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
_scan_lock = threading.Lock()
_process_lock = threading.Lock()
_active_process: subprocess.Popen[str] | None = None
_active_scan_id: str | None = None
_cancel_requested = False
_cancelled_scan_ids: list[str] = []
_finished_scan_ids: list[str] = []
_scan_finished = threading.Event()
_scan_finished.set()


def _validated_scan_id(value: Any) -> str:
    scan_id = str(value or "")
    if not re.fullmatch(r"[A-Za-z0-9._-]{1,80}", scan_id):
        raise ValueError("Ogiltigt skannings-ID.")
    return scan_id


def scan_object_code(camera_index: Any, raw_scan_id: Any) -> dict[str, Any]:
    scan_id = _validated_scan_id(raw_scan_id)
    try:
        index = int(camera_index)
    except (TypeError, ValueError) as error:
        raise ValueError("Kameranumret måste vara ett heltal.") from error
    if str(index) != str(camera_index) or not 0 <= index <= 8:
        raise ValueError("Kameranumret måste vara mellan 0 och 8.")
    if not _scan_lock.acquire(blocking=False):
        raise ValueError("En kamerasökning pågår redan.")

    global _active_process, _active_scan_id, _cancel_requested
    process = None
    with _process_lock:
        if scan_id in _cancelled_scan_ids:
            _cancelled_scan_ids.remove(scan_id)
            _scan_lock.release()
            return {"code": "", "cancelled": True}
        _scan_finished.clear()
        _active_scan_id = scan_id
        _active_process = None
        _cancel_requested = False
        _scan_finished.clear()
    try:
        command = [
            sys.executable, "-B", "-m", "hardware.razer_camera.scanner",
            "--once", "--camera", str(index),
        ]
        process = subprocess.Popen(
            command,
            cwd=ROOT_DIR,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        with _process_lock:
            _active_process = process
            cancel_requested = _cancel_requested and _active_scan_id == scan_id
        if cancel_requested and process.poll() is None:
            process.terminate()
        try:
            stdout, stderr = process.communicate(timeout=180)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise ValueError("Skanningen tog för lång tid och avbröts.") from error

        with _process_lock:
            cancel_requested = _cancel_requested and _active_scan_id == scan_id
        if process.returncode == 2 or cancel_requested:
            return {"code": "", "cancelled": True}
        if process.returncode != 0:
            detail = stderr.strip() or "Python-skannern kunde inte läsa kameran."
            raise ValueError(detail[-1000:])

        code = stdout.strip()
        if not code or len(code) > 256 or "\n" in code or "\r" in code:
            raise ValueError("Python-skannern returnerade ingen giltig streckkod.")
        return {"code": code, "cancelled": False}
    finally:
        with _process_lock:
            if _active_scan_id == scan_id:
                _active_process = None
                _active_scan_id = None
                _cancel_requested = False
                _finished_scan_ids.append(scan_id)
                del _finished_scan_ids[:-32]
        _scan_lock.release()
        _scan_finished.set()


def cancel_object_scan(raw_scan_id: Any) -> dict[str, bool]:
    scan_id = _validated_scan_id(raw_scan_id)
    global _cancel_requested
    with _process_lock:
        if _active_scan_id != scan_id:
            if scan_id in _finished_scan_ids:
                return {"cancelled": False}
            if scan_id not in _cancelled_scan_ids:
                _cancelled_scan_ids.append(scan_id)
                del _cancelled_scan_ids[:-32]
            return {"cancelled": True}
        _cancel_requested = True
        process = _active_process
    if process is not None and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)
            _scan_finished.wait(timeout=5)
    return {"cancelled": True}