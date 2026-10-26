"""Exercise the built runtime without external Python or real application data."""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
from contextlib import closing
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from unittest.mock import patch
from urllib.request import ProxyHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app_version import VERSION
from launcher import prepare_server
from simulation_store import reset_simulation


def wait_for(predicate, seconds=30):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.1)
    raise AssertionError("Timed out waiting for packaged application.")


def stop(process):
    if process.poll() is None:
        process.terminate()
    process.wait(timeout=10)


def find_window(pid):
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    found = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(window, _):
        process_id = wintypes.DWORD()
        user32.GetWindowThreadProcessId(window, ctypes.byref(process_id))
        if process_id.value == pid and user32.IsWindowVisible(window):
            found.append(window)
        return True

    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def run_setup(executable, arguments, environment, success=True):
    result = subprocess.run([str(executable), "/VERYSILENT", "/SUPPRESSMSGBOXES",
                             "/NORESTART", "/SP-", *arguments],
                            env=environment, timeout=90, check=False)
    assert (result.returncode == 0) == success, f"Unexpected setup exit code {result.returncode}"


def shortcut_properties(path, environment, reset_icon=False):
    assert path.is_file(), f"Missing installed shortcut: {path}"
    powershell = Path(os.environ["SystemRoot"]) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe"
    script = """
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut($env:LOAN_TEST_SHORTCUT)
if ($env:LOAN_TEST_RESET_ICON -eq '1') {
    $shortcut.IconLocation = $shortcut.TargetPath + ',0'
    $shortcut.Save()
}
[pscustomobject]@{target=$shortcut.TargetPath; icon=$shortcut.IconLocation} | ConvertTo-Json -Compress
"""
    result = subprocess.run(
        [str(powershell), "-NoProfile", "-NonInteractive", "-Command", script],
        env={**environment, "LOAN_TEST_SHORTCUT": str(path), "LOAN_TEST_RESET_ICON": str(int(reset_icon))},
        capture_output=True, text=True, encoding="utf-8", check=True, timeout=30,
    )
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--installer", type=Path, help="Only the separately compiled *-TestSetup.exe")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    if args.installer and not args.installer.name.endswith("-TestSetup.exe"):
        parser.error("Never run production installer in an automated installation test.")
    work = ROOT / "build" / "windows" / f"smoke-{uuid.uuid4().hex[:8]}"
    work.mkdir(parents=True)
    children = []
    environment = os.environ.copy()
    for name in list(environment):
        if name.startswith("LOAN_"):
            environment.pop(name)
    environment.update(
        PATH=os.pathsep.join([str(Path(os.environ["SystemRoot"]) / "System32"),
                              os.environ["SystemRoot"]]),
        LOCALAPPDATA=str(work / "profile"), TEMP=str(work), TMP=str(work),
        LOAN_ENABLE_NOTIFICATIONS="0",
        LOAN_SKIP_UPDATE_CHECK="1",
    )
    storage = Path(environment["LOCALAPPDATA"]) / "LoanInventoryLauncher"
    storage.mkdir(parents=True)
    opener = build_opener(ProxyHandler({}))
    try:
        info = subprocess.run([str(bundle / "LoanInventoryAdmin.exe"), "--runtime-info"],
                              env=environment, capture_output=True, text=True, check=True, timeout=30)
        runtime = json.loads(info.stdout)
        assert runtime["version"] == VERSION and runtime["frozen"] and runtime["pyscard"]
        assert runtime["openpyxl"] == "3.1.5"
        assert runtime["update_tls"] == {
            "provider": "truststore", "verify_required": True, "check_hostname": True,
        }
        help_result = subprocess.run([str(bundle / "LoanInventoryAdmin.exe"), "--help"],
                                     env=environment, capture_output=True, text=True, check=True, timeout=30)
        assert "--role" in help_result.stdout
        print(f"Bundled dependencies, no external Python PATH: {runtime}")

        gui = subprocess.Popen([str(bundle / "LoanInventory.exe")], env=environment)
        children.append(gui)
        window = wait_for(lambda: find_window(gui.pid))
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
        user32.PostMessageW(window, 0x0010, 0, 0)  # WM_CLOSE, before any server exists.
        assert gui.wait(timeout=10) == 0
        print("Frozen Tk launcher created a real window and closed cleanly.")

        def start_server(mode, database=""):
            with patch.dict(os.environ, environment, clear=True), \
                    patch("launcher.is_frozen", return_value=True), \
                    patch("launcher.sys.executable", str(bundle / "LoanInventory.exe")):
                command, child_env, _, path = prepare_server(mode, str(database), "", "8000", storage)
            command[-1] = "0"
            log = work / f"server-{uuid.uuid4().hex}.log"
            child_env["LOAN_SERVER_LOG"] = str(log)
            process = subprocess.Popen(command, env=child_env)
            children.append(process)

            def address():
                text = log.read_text(encoding="utf-8") if log.exists() else ""
                assert process.poll() is None, text
                return text.split("running at ", 1)[1].splitlines()[0] + "/" if "running at " in text else ""

            return process, wait_for(address), path, child_env["LOAN_INSTANCE_ID"]

        process, url, database, instance = start_server("simulation")

        def call(path, payload=None, cookie=""):
            headers = {"Content-Type": "application/json", "X-Loan-Client": "browser", "Cookie": cookie}
            request = Request(url + path, headers=headers,
                              data=None if payload is None else json.dumps(payload).encode())
            with opener.open(request, timeout=5) as response:
                return json.load(response)["data"], response.headers

        data, _ = call("api/runtime")
        assert data == {"simulation": True, "instance_id": instance}
        for path in ("", "styles.css", "js/app.js", "vendor/chart.umd.js",
                     "sample-images/bit-set.svg", "privacy.html"):
            with opener.open(url + path, timeout=5) as response:
                assert response.status == 200 and response.read()
        for username in ("admin", "superadmin"):
            _, headers = call("api/auth/login", {"username": username, "password": username})
            staff_cookie = headers["Set-Cookie"].split(";", 1)[0]
            session, _ = call("api/auth/session", cookie=staff_cookie)
            assert session["role"] == username
        users, _ = call("api/users")
        objects, _ = call("api/objects")
        assert len(users) == 14 and len(objects) == 8
        stats, _ = call("api/stats", cookie=staff_cookie)
        assert stats["loaned"] == 24 and stats["overdue"] > 0
        jobs, _ = call("api/loan-requests", cookie=staff_cookie)
        damaged_job = next(job for job in jobs if job["request_id"] == 32)
        assert damaged_job["unresolved_damage_quantity"] == 1 and damaged_job["stocking_blocked"]
        assert damaged_job["unresolved_damage_description"]
        operator_jobs, _ = call("api/loan-requests")
        assert all("unresolved_damage_description" not in job for job in operator_jobs)
        stop(process)
        print("Frozen simulation, runtime, authenticated login and six static resources passed.")

        with closing(sqlite3.connect(database)) as connection, connection:
            connection.execute("CREATE TABLE installer_sentinel(value TEXT)")
            connection.execute("INSERT INTO installer_sentinel VALUES ('generated test data')")
        earlier_backups = set((database.parent / "backups").glob("*.db"))
        process, url, reopened_database, _ = start_server("simulation")
        assert reopened_database == database
        data, _ = call("api/runtime")
        assert data["simulation"]
        if args.installer:
            run_setup(args.installer.resolve(), [f"/DIR={work / 'installed'}",
                      f"/LOG={work / 'server-busy.log'}"], environment, success=False)
        stop(process)
        backups = list(set((database.parent / "backups").glob("*.db")) - earlier_backups)
        assert len(backups) == 1
        for path in (database, backups[0]):
            with closing(sqlite3.connect(path)) as connection:
                assert connection.execute("SELECT value FROM installer_sentinel").fetchone()[0] == "generated test data"
                assert connection.execute("SELECT COUNT(*) FROM access_accounts").fetchone()[0] == 2
        print("Persistent demo/database/accounts preserved on restart; pre-migration backup verified.")

        if args.installer:
            target = work / "installed"
            preference = storage / "preferences.json"
            preference.write_text(json.dumps({"database": str(database), "mode": "simulation"}), encoding="utf-8")
            before = {path: path.read_bytes() for path in (database, preference, backups[0])}
            setup = args.installer.resolve()
            setup_args = [f"/DIR={target}", "/TASKS=desktopicon", f"/LOG={work / 'install.log'}"]
            run_setup(setup, setup_args, environment)
            assert (target / "LoanInventory.exe").is_file()
            icon = target / f"LoanInventory-{VERSION}.ico"
            assert icon.read_bytes() == (ROOT / "build" / "windows" / "loan-inventory.ico").read_bytes()
            shortcuts = [target / "test-shortcuts" / folder / "Loan Inventory.lnk"
                         for folder in ("Start Menu", "Desktop")]
            for shortcut in shortcuts:
                properties = shortcut_properties(shortcut, environment)
                assert Path(properties["target"]) == target / "LoanInventory.exe"
                icon_path, index = properties["icon"].rsplit(",", 1)
                assert Path(icon_path) == icon and int(index) == 0
                # Recreate the old EXE-based icon reference before reinstalling.
                shortcut_properties(shortcut, environment, reset_icon=True)
            installed_info = subprocess.run([str(target / "LoanInventoryAdmin.exe"), "--runtime-info"],
                                            env=environment, capture_output=True, text=True, check=True, timeout=30)
            assert json.loads(installed_info.stdout)["version"] == VERSION
            run_setup(setup, setup_args, environment)
            for shortcut in shortcuts:
                properties = shortcut_properties(shortcut, environment)
                icon_path, index = properties["icon"].rsplit(",", 1)
                assert Path(icon_path) == icon and int(index) == 0
            print("Desktop/Start Menu shortcuts reference the versioned box icon after install and reinstall.")
            assert all(path.read_bytes() == value for path, value in before.items())
            gui = subprocess.Popen([str(target / "LoanInventory.exe")], env=environment)
            children.append(gui)
            window = wait_for(lambda: find_window(gui.pid))
            run_setup(setup, setup_args, environment, success=False)
            uninstaller = target / "unins000.exe"
            run_setup(uninstaller, [f"/LOG={work / 'uninstall-busy.log'}"], environment, success=False)
            assert (target / "LoanInventory.exe").is_file()
            user32.PostMessageW(window, 0x0010, 0, 0)
            assert gui.wait(timeout=10) == 0
            run_setup(uninstaller, [f"/LOG={work / 'uninstall.log'}"], environment)
            wait_for(lambda: not (target / "LoanInventory.exe").exists())
            assert not icon.exists() and not any(path.exists() for path in shortcuts)
            assert all(path.read_bytes() == value for path, value in before.items())
            print("Silent install/reinstall, running-app refusal, uninstall and data preservation passed.")
        archived_demo = reset_simulation(storage)
        assert archived_demo is not None
        with closing(sqlite3.connect(archived_demo)) as connection:
            assert connection.execute("SELECT value FROM installer_sentinel").fetchone()[0] == "generated test data"
        process, url, restored_database, _ = start_server("simulation")
        assert restored_database == database
        _, headers = call("api/auth/login", {"username": "admin", "password": "admin"})
        data, _ = call("api/stats", cookie=headers["Set-Cookie"].split(";", 1)[0])
        assert data["loaned"] == 24
        with closing(sqlite3.connect(restored_database)) as connection:
            assert connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 15
            assert connection.execute("SELECT name FROM sqlite_master WHERE name='installer_sentinel'").fetchone() is None
        stop(process)
        print("Demo reset preserved its archive and regenerated the rich simulation successfully.")
    finally:
        for process in children:
            stop(process)

        def cleanup():
            try:
                shutil.rmtree(work)
                return True
            except FileNotFoundError:
                return True
            except PermissionError:
                # Inno's uninstaller helper releases its scratch files after exit.
                return False

        wait_for(cleanup)


if __name__ == "__main__":
    main()
