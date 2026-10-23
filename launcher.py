"""Desktop launcher; server processes always receive an explicit environment."""
from __future__ import annotations

import ipaddress
import codecs
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from queue import Empty, Queue
from threading import Thread
import uuid
import webbrowser
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from app_runtime import default_database, is_frozen, storage_directory
from app_version import RELEASES_URL, VERSION

ROOT = Path(__file__).resolve().parent
MODES = {
    "local": "Lokalt",
    "lan": "Nätverk",
    "simulation": "Simulering",
}


def probe_server(url: str, instance_id: str) -> float:
    started = time.perf_counter()
    with build_opener(ProxyHandler({})).open(url + "api/runtime", timeout=1) as response:
        payload = json.load(response)
    data = payload.get("data") if isinstance(payload, dict) else None
    if not isinstance(data, dict) or data.get("instance_id") != instance_id:
        raise ValueError("En annan server svarar på adressen.")
    return (time.perf_counter() - started) * 1000


def prepare_server(mode: str, database: str, host: str, port: str,
                   storage: Path) -> tuple[list[str], dict[str, str], str, Path]:
    if mode not in ("local", "lan", "simulation"):
        raise ValueError("Välj ett giltigt startläge.")
    try:
        port_number = int(port)
    except ValueError as error:
        raise ValueError("Porten ska vara ett heltal mellan 1 och 65535.") from error
    if not 1 <= port_number <= 65535:
        raise ValueError("Porten ska vara mellan 1 och 65535.")
    bind_host = "127.0.0.1"
    if mode == "lan":
        try:
            address = ipaddress.IPv4Address(host.strip())
        except ipaddress.AddressValueError as error:
            raise ValueError("Ange datorns privata IPv4-adress för LAN-start.") from error
        if not any(address in ipaddress.ip_network(network) for network in
                   ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")):
            raise ValueError("LAN-start kräver en privat IPv4-adress, inte en wildcard-adress.")
        bind_host = str(address)
    if mode == "simulation":
        directory = storage / "simulations"
        directory.mkdir(parents=True, exist_ok=True)
        database_path = directory / f"simulation-{uuid.uuid4().hex}.db"
        # Exclusive creation prevents reuse or replacement of an existing database.
        database_path.touch(exist_ok=False)
    else:
        database_path = Path(database).expanduser().resolve()
        if not database.strip() or not database_path.is_file():
            raise ValueError("Välj en befintlig databas eller skapa en tom databas först.")
    environment = os.environ.copy()
    for key in ("LOAN_LOCAL_ADMIN_PASSWORD", "LOAN_LOCAL_SUPERADMIN_PASSWORD"):
        environment.pop(key, None)
    environment.update({
        "LOAN_HOST": bind_host,
        "LOAN_DATABASE_PATH": str(database_path),
        "LOAN_ALLOW_LAN": "1" if mode == "lan" else "0",
        "LOAN_SEED_DEMO": "1" if mode == "simulation" else "0",
        "LOAN_LOCAL_FIXED_TEST_CREDENTIALS": "1" if mode == "simulation" else "0",
        "LOAN_SIMULATION": "1" if mode == "simulation" else "0",
        "LOAN_ENABLE_NOTIFICATIONS": "0",
        "LOAN_INSTANCE_ID": uuid.uuid4().hex,
        "LOAN_SERVER_DIAGNOSTICS": "1",
        "PYTHONIOENCODING": "utf-8",
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    if mode == "simulation":
        environment.update(LOAN_LOCAL_ADMIN_PASSWORD="admin", LOAN_LOCAL_SUPERADMIN_PASSWORD="superadmin")
    if is_frozen():
        command = [sys.executable, "--server", "--port", str(port_number)]
    else:
        command = [sys.executable, "-B", str(ROOT / "main.py"), "--port", str(port_number)]
    return command, environment, f"http://{bind_host}:{port_number}/", database_path


class Launcher:
    def __init__(self) -> None:
        import tkinter as tk
        from tkinter import ttk
        from tkinter.scrolledtext import ScrolledText

        self.tk = tk
        self.root = tk.Tk()
        self.root.title(f"Starta Loan Inventory · {VERSION}")
        self.root.geometry("660x680")
        self.root.minsize(600, 650)
        self.icon = tk.PhotoImage(width=32, height=32)
        self.icon.put("#2f6f8f", to=(0, 0, 32, 32))
        for top in (6, 14, 22):
            self.icon.put("#ffffff", to=(6, top, 26, top + 4))
        self.root.iconphoto(True, self.icon)
        self.storage = storage_directory()
        self.process: subprocess.Popen | None = None
        self.log_path: Path | None = None
        self.url = ""
        self.instance_id = ""
        self.deadline = 0.0
        self.check_id: str | None = None
        self.next_probe = 0.0
        self.probe_pending = False
        self.health_results: Queue[tuple[str, float | None, str]] = Queue()
        self.log_offset = 0
        self.log_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.last_log_error = ""
        self.last_health_error = ""
        self.mode = tk.StringVar(value="simulation")
        self.database = tk.StringVar(value=str(default_database()))
        self.host = tk.StringVar(value="")
        self.port = tk.StringVar(value="8000")
        self.status = tk.StringVar(value="Stoppad")
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="Loan Inventory", font=("Segoe UI", 20, "bold")).pack(anchor="w")
        self.updates_button = ttk.Button(
            frame, text="Öppna versionssidan i webbläsaren", command=self.open_releases)
        self.updates_button.pack(anchor="w", pady=(6, 0))
        ttk.Label(frame, text="Privat GitHub · inloggning krävs · ingen automatisk kontroll",
                  wraplength=550).pack(anchor="w")
        modes = ttk.Frame(frame)
        modes.pack(fill="x", pady=(12, 8))
        for value, label in MODES.items():
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode,
                            command=self.update_fields).pack(side="left", padx=(0, 24))
        ttk.Label(frame, text="Databas").pack(anchor="w", pady=(4, 3))
        self.database_entry = ttk.Entry(frame, textvariable=self.database)
        self.database_entry.pack(fill="x")
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x", pady=5)
        self.browse_button = ttk.Button(buttons, text="Bläddra...", command=self.browse)
        self.browse_button.pack(side="left")
        self.new_button = ttk.Button(buttons, text="Ny databas...", command=self.new_database)
        self.new_button.pack(side="left", padx=8)
        fields = ttk.Frame(frame)
        fields.pack(fill="x", pady=6)
        ttk.Label(fields, text="LAN-adress").grid(row=0, column=0, sticky="w")
        ttk.Label(fields, text="Port").grid(row=0, column=1, sticky="w", padx=12)
        self.host_entry = ttk.Entry(fields, textvariable=self.host, width=33)
        self.host_entry.grid(row=1, column=0, sticky="ew")
        self.port_entry = ttk.Entry(fields, textvariable=self.port, width=9)
        self.port_entry.grid(row=1, column=1, padx=12)
        self.help_text = ttk.Label(frame, wraplength=570, foreground="#345a70")
        self.help_text.pack(fill="x", pady=8)
        controls = ttk.Frame(frame)
        controls.pack(fill="x", pady=(4, 10))
        self.start_button = ttk.Button(controls, text="Starta", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Stoppa", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(controls, text="Öppna appen", command=self.open_browser, state="disabled")
        self.open_button.pack(side="right")
        ttk.Separator(frame).pack(fill="x", pady=(0, 8))
        ttk.Label(frame, textvariable=self.status, wraplength=570).pack(fill="x", pady=(0, 6))
        ttk.Label(frame, text="Serverlogg · HTTP-status och behandlingstid (ms)").pack(anchor="w", pady=(0, 4))
        self.console = ScrolledText(frame, height=10, wrap="word", font=("Consolas", 10),
                                    background="#15212b", foreground="#d9e7ef",
                                    insertbackground="#d9e7ef", relief="flat", state="disabled")
        self.console.pack(fill="both", expand=True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.load_preferences()
        self.update_fields()

    def report_error(self, error: Exception | str) -> None:
        from tkinter import messagebox
        self.status.set("Fel — se serverloggen")
        self.append_log(f"[FEL] {error}\n")
        messagebox.showerror("Kunde inte utföra åtgärden", str(error), parent=self.root)

    def load_preferences(self) -> None:
        path = self.storage / "preferences.json"
        if not path.exists():
            return
        try:
            values = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(values, dict):
                raise ValueError("Startinställningarna måste vara ett JSON-objekt.")
            if values.get("mode") == "remote":
                self.mode.set("local")
                self.append_log("[INFO] Anslutningsläget har tagits bort. Välj hur servern ska startas.\n")
            for name in ("mode", "database", "host", "port"):
                value = values.get(name)
                if isinstance(value, str) and (name != "mode" or value in MODES):
                    getattr(self, name).set(value)
        except (OSError, ValueError) as error:
            self.report_error(f"Kunde inte läsa startinställningarna: {error}")

    def save_preferences(self) -> None:
        self.storage.mkdir(parents=True, exist_ok=True)
        values = {name: getattr(self, name).get() for name in ("mode", "database", "host", "port")}
        temporary = self.storage / f"preferences-{uuid.uuid4().hex}.tmp"
        try:
            temporary.write_text(json.dumps(values, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.storage / "preferences.json")
        finally:
            temporary.unlink(missing_ok=True)

    def update_fields(self) -> None:
        mode = self.mode.get()
        for widget in (self.database_entry, self.browse_button, self.new_button):
            widget.configure(state="normal" if mode in ("local", "lan") else "disabled")
        self.host_entry.configure(state="normal" if mode == "lan" else "disabled")
        self.help_text.configure(text={
            "simulation": "Ny fejkdatabas · Inga utskick/kortläsare · admin/admin",
            "local": "Endast denna dator · Vald databas · Inga externa utskick",
            "lan": "Delas på nätverket · Endast fejkdata · Inga externa utskick",
        }[mode])

    def append_log(self, text: str) -> None:
        at_bottom = self.console.yview()[1] >= 0.99
        self.console.configure(state="normal")
        self.console.insert("end", text)
        lines = int(self.console.index("end-1c").split(".")[0])
        if lines > 1000:
            self.console.delete("1.0", f"{lines - 1000 + 1}.0")
        # A single very long traceback line must also remain bounded.
        characters = self.console.count("1.0", "end-1c", "chars")
        if characters and characters[0] > 100000:
            self.console.delete("1.0", f"1.0 + {characters[0] - 100000} chars")
        self.console.configure(state="disabled")
        if at_bottom:
            self.console.see("end")

    def read_log(self) -> None:
        if self.log_path is None:
            return
        try:
            with self.log_path.open("rb") as log:
                log.seek(self.log_offset)
                chunk = log.read(16384)
                self.log_offset = log.tell()
            self.last_log_error = ""
            if chunk:
                self.append_log(self.log_decoder.decode(chunk))
        except OSError as error:
            message = f"[FEL] Kunde inte läsa serverloggen: {error}\n"
            if message != self.last_log_error:
                self.append_log(message)
                self.last_log_error = message

    def start_probe(self) -> None:
        self.probe_pending = True
        url, instance_id = self.url, self.instance_id

        def run() -> None:
            try:
                elapsed = probe_server(url, instance_id)
                result = (instance_id, elapsed, "")
            except (OSError, URLError, ValueError) as error:
                result = (instance_id, None, str(error))
            self.health_results.put(result)

        Thread(target=run, daemon=True).start()

    def browse(self) -> None:
        from tkinter import filedialog
        path = filedialog.askopenfilename(parent=self.root, title="Välj SQLite-databas",
                                         filetypes=[("SQLite", "*.db *.sqlite *.sqlite3"), ("Alla filer", "*.*")])
        if path:
            self.database.set(path)

    def new_database(self) -> None:
        from tkinter import filedialog
        initial_directory = self.storage / "data"
        try:
            initial_directory.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            self.report_error(f"Kunde inte öppna datamappen: {error}")
            return
        path = filedialog.asksaveasfilename(parent=self.root, title="Skapa ny tom databas",
                                          initialdir=str(initial_directory),
                                          defaultextension=".db", filetypes=[("SQLite", "*.db")])
        if path:
            try:
                Path(path).touch(exist_ok=False)
                self.database.set(path)
            except OSError as error:
                self.report_error(f"Databasen skapades inte. Befintliga filer ersätts aldrig: {error}")

    def start(self) -> None:
        if self.process is not None:
            self.report_error("Stoppa den server som detta fönster redan har startat först.")
            return
        from tkinter import messagebox
        try:
            if self.mode.get() == "lan" and not messagebox.askokcancel(
                    "LAN-test", "Alla som når servern får operatörsåtkomst till vald databas. "
                    "Använd endast fejkdata och godkänd nätverksåtkomst. Fortsätt?", parent=self.root):
                return
            command, environment, self.url, database = prepare_server(
                self.mode.get(), self.database.get(), self.host.get(), self.port.get(), self.storage)
            self.save_preferences()
            self.log_path = self.storage / f"server-{environment['LOAN_INSTANCE_ID']}.log"
            environment["LOAN_SERVER_LOG"] = str(self.log_path)
            with self.log_path.open("w", encoding="utf-8") as log:
                self.process = subprocess.Popen(command, cwd=ROOT, env=environment, stdout=log,
                                                stderr=subprocess.STDOUT,
                                                creationflags=subprocess.CREATE_NO_WINDOW
                                                if is_frozen() and os.name == "nt" else 0)
            self.instance_id = environment["LOAN_INSTANCE_ID"]
            self.log_offset = 0
            self.log_decoder.reset()
            self.last_health_error = ""
            self.probe_pending = False
            self.next_probe = 0
            self.deadline = time.monotonic() + 30
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.status.set("Startar...")
            self.append_log(f"\n[START] {self.url}\nDatabas: {database}\nLoggfil: {self.log_path}\n")
            self.check_id = self.root.after(200, self.check_process)
        except (OSError, ValueError) as error:
            self.report_error(error)

    def check_process(self) -> None:
        self.check_id = None
        if self.process is None:
            return
        self.read_log()
        code = self.process.poll()
        if code is not None:
            self.process = None
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            self.open_button.configure(state="disabled")
            self.report_error(f"Servern avslutades (kod {code}). Felorsaken finns i:\n{self.log_path}")
            return
        while True:
            try:
                instance_id, elapsed, error = self.health_results.get_nowait()
            except Empty:
                break
            if instance_id != self.instance_id:
                continue
            self.probe_pending = False
            self.next_probe = time.monotonic() + 3
            if elapsed is not None:
                starting = bool(self.deadline)
                self.deadline = 0
                self.status.set(f"Kör · Svarstid {elapsed:.0f} ms · {self.url}")
                if starting or self.last_health_error:
                    self.append_log(f"[STATUS] Servern svarar ({elapsed:.0f} ms).\n")
                self.last_health_error = ""
                self.open_button.configure(state="normal")
                if starting:
                    self.open_browser()
            else:
                self.status.set("Startar..." if self.deadline else "Svarar inte — se serverloggen")
                if error != self.last_health_error:
                    self.append_log(f"[STATUS] Väntar på servern: {error}\n")
                    self.last_health_error = error
        if self.deadline and time.monotonic() >= self.deadline:
            self.stop()
            self.report_error(f"Servern svarade inte inom 30 sekunder. Se loggen:\n{self.log_path}")
            return
        if not self.probe_pending and time.monotonic() >= self.next_probe:
            self.start_probe()
        self.check_id = self.root.after(500, self.check_process)

    def open_browser(self) -> None:
        if not webbrowser.open(self.url):
            self.report_error(f"Kunde inte öppna webbläsaren. Öppna adressen manuellt:\n{self.url}")

    def open_releases(self) -> None:
        try:
            if not webbrowser.open(RELEASES_URL):
                self.report_error(f"Öppna versionssidan manuellt:\n{RELEASES_URL}")
        except OSError as error:
            self.report_error(f"Kunde inte öppna versionssidan: {error}\n{RELEASES_URL}")

    def stop(self) -> None:
        if self.process is not None:
            try:
                if self.process.poll() is None:
                    self.process.terminate()
                self.process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired) as error:
                self.report_error(f"Kunde inte stoppa processen {self.process.pid}: {error}")
                return
            self.process = None
        if self.check_id is not None:
            self.root.after_cancel(self.check_id)
            self.check_id = None
        self.read_log()
        self.deadline = 0
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.open_button.configure(state="disabled")
        self.status.set("Stoppad")
        self.append_log("[STOPP] Servern stoppad. Databasen finns kvar.\n")

    def close(self) -> None:
        from tkinter import messagebox
        if self.process is not None:
            if not messagebox.askokcancel("Stäng", "Stoppa servern som detta fönster startade och stäng?", parent=self.root):
                return
            self.stop()
            if self.process is not None:
                return
        self.root.destroy()


if __name__ == "__main__":
    Launcher().root.mainloop()
