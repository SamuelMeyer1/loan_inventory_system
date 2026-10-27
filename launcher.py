"""Desktop launcher; server processes always receive an explicit environment."""
from __future__ import annotations

import ipaddress
import codecs
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from http.client import HTTPException
from queue import Empty, Queue
from threading import Thread
import uuid
import webbrowser
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

from app_runtime import default_database, is_frozen, storage_directory
from app_version import RELEASES_URL, VERSION
from app_icon import icon_ico, icon_png
from app_updates import UpdateCheck, check_for_updates
from simulation_store import prepare_simulation, reset_simulation, simulation_path

ROOT = Path(__file__).resolve().parent
MODES = {
    "local": "Lokalt",
    "lan": "Nätverk",
    "simulation": "Simulering",
}


def probe_server(url: str, instance_id: str) -> float:
    started = time.perf_counter()
    with build_opener(ProxyHandler({})).open(url + "api/runtime", timeout=5) as response:
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
        database_path = prepare_simulation(storage)
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
        "LOAN_SEED_DEMO": "0",
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
        self.root.geometry("500x340")
        self.root.minsize(430, 300)
        self.icon = tk.PhotoImage(data=icon_png(32), format="png")
        self.root.iconphoto(True, self.icon)
        self.icon_file: Path | None = None
        if os.name == "nt":
            self.icon_file = Path(tempfile.gettempdir()) / f"loan-inventory-{os.getpid()}-{uuid.uuid4().hex}.ico"
            self.icon_file.write_bytes(icon_ico())
            self.root.iconbitmap(default=str(self.icon_file))
        self.root.bind("<Destroy>", self.cleanup_icon, add="+")
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
        self.update_results: Queue[tuple[UpdateCheck | None, str]] = Queue()
        self.update_check_id: str | None = None
        self.update_check_running = False
        self.log_offset = 0
        self.log_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self.last_log_error = ""
        self.last_health_error = ""
        self.mode = tk.StringVar(value="simulation")
        self.database = tk.StringVar(value=str(default_database()))
        self.host = tk.StringVar(value="")
        self.port = tk.StringVar(value="8000")
        self.status = tk.StringVar(value="Stoppad")
        self.update_status = tk.StringVar(value="Uppdateringar kontrolleras vid start.")
        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=10)
        self.start_tab = ttk.Frame(self.tabs, padding=16)
        self.settings_tab = ttk.Frame(self.tabs, padding=16)
        self.log_tab = ttk.Frame(self.tabs, padding=10)
        self.tabs.add(self.start_tab, text="Start")
        self.tabs.add(self.settings_tab, text="Inställningar")
        self.tabs.add(self.log_tab, text="Serverlogg")

        ttk.Label(self.start_tab, text="Loan Inventory", font=("Segoe UI", 18, "bold")).pack(anchor="w")
        modes = ttk.Frame(self.start_tab)
        modes.pack(fill="x", pady=(12, 8))
        for value, label in MODES.items():
            ttk.Radiobutton(modes, text=label, value=value, variable=self.mode,
                            command=self.update_fields).pack(side="left", padx=(0, 16))
        self.help_text = ttk.Label(self.start_tab, wraplength=420, foreground="#345a70")
        self.help_text.pack(fill="x", pady=(2, 12))
        controls = ttk.Frame(self.start_tab)
        controls.pack(fill="x", pady=(2, 8))
        self.start_button = ttk.Button(controls, text="Starta", command=self.start)
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(controls, text="Stoppa", command=self.stop, state="disabled")
        self.stop_button.pack(side="left", padx=8)
        self.open_button = ttk.Button(controls, text="Öppna appen", command=self.open_browser, state="disabled")
        self.open_button.pack(side="right")
        ttk.Separator(self.start_tab).pack(fill="x", pady=(0, 8))
        ttk.Label(self.start_tab, textvariable=self.status, wraplength=420).pack(fill="x")

        ttk.Label(self.settings_tab, text="Databas").grid(row=0, column=0, sticky="w", pady=(0, 3))
        self.database_section = ttk.Frame(self.settings_tab)
        self.database_section.grid(row=1, column=0, sticky="ew")
        self.settings_tab.columnconfigure(0, weight=1)
        self.database_entry = ttk.Entry(self.database_section, textvariable=self.database)
        self.database_entry.pack(fill="x")
        buttons = ttk.Frame(self.database_section)
        buttons.pack(fill="x", pady=5)
        self.browse_button = ttk.Button(buttons, text="Bläddra...", command=self.browse)
        self.browse_button.pack(side="left")
        self.new_button = ttk.Button(buttons, text="Ny databas...", command=self.new_database)
        self.new_button.pack(side="left", padx=8)

        self.network_section = ttk.Frame(self.settings_tab)
        self.network_section.grid(row=2, column=0, sticky="ew", pady=(4, 0))
        self.network_section.columnconfigure(0, weight=1)
        ttk.Label(self.network_section, text="LAN-adress").grid(row=0, column=0, sticky="w")
        self.host_entry = ttk.Entry(self.network_section, textvariable=self.host)
        self.host_entry.grid(row=1, column=0, sticky="ew")

        self.port_section = ttk.Frame(self.settings_tab)
        self.port_section.grid(row=3, column=0, sticky="w", pady=(6, 0))
        ttk.Label(self.port_section, text="Port").pack(anchor="w")
        self.port_entry = ttk.Entry(self.port_section, textvariable=self.port, width=9)
        self.port_entry.pack(anchor="w")

        self.simulation_section = ttk.Frame(self.settings_tab)
        self.simulation_section.grid(row=4, column=0, sticky="ew", pady=(8, 0))
        self.simulation_info = ttk.Label(self.simulation_section, wraplength=420)
        self.simulation_info.pack(anchor="w", pady=(0, 4))
        self.reset_simulation_button = ttk.Button(
            self.simulation_section, text="Återställ demodata...", command=self.reset_demo)
        self.reset_simulation_button.pack(anchor="w")

        updates = ttk.Frame(self.settings_tab)
        updates.grid(row=5, column=0, sticky="ew", pady=(12, 0))
        self.check_updates_button = ttk.Button(updates, text="Sök uppdateringar", command=self.check_updates)
        self.check_updates_button.pack(side="left")
        self.updates_button = ttk.Button(updates, text="Versionssida", command=self.open_releases)
        self.updates_button.pack(side="left", padx=8)
        ttk.Label(self.settings_tab, textvariable=self.update_status, wraplength=420).grid(
            row=6, column=0, sticky="ew", pady=(6, 0))
        self.console = ScrolledText(self.log_tab, height=10, wrap="word", font=("Consolas", 10),
                                    background="#15212b", foreground="#d9e7ef",
                                    insertbackground="#d9e7ef", relief="flat", state="disabled")
        self.console.pack(fill="both", expand=True)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.load_preferences()
        self.update_fields()
        if os.environ.get("LOAN_SKIP_UPDATE_CHECK") == "1":
            self.update_status.set("Automatisk uppdateringskontroll avstängd för denna start.")
        else:
            self.update_check_id = self.root.after(200, self.check_updates)

    def cleanup_icon(self, event=None) -> None:
        if event is not None and event.widget is not self.root:
            return
        if self.icon_file is not None:
            self.icon_file.unlink(missing_ok=True)
            self.icon_file = None

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
        if mode in ("local", "lan"):
            self.database_section.grid()
        else:
            self.database_section.grid_remove()
        if mode == "lan":
            self.network_section.grid()
        else:
            self.network_section.grid_remove()
        if mode == "simulation":
            self.simulation_section.grid()
        else:
            self.simulation_section.grid_remove()
        self.reset_simulation_button.configure(
            state="normal" if mode == "simulation" and self.process is None else "disabled")
        self.help_text.configure(text={
            "simulation": "Separat demo med sparade teständringar. Inga utskick eller kortläsare.",
            "local": "Servern körs bara på den här datorn.",
            "lan": "Delas på nätverket. Använd endast fejkdata och godkänd nätverksåtkomst.",
        }[mode])
        self.simulation_info.configure(
            text=f"Sparad demo · admin/admin\n{simulation_path(self.storage)}")

    def reset_demo(self) -> None:
        from tkinter import messagebox
        if self.mode.get() != "simulation" or self.process is not None:
            self.report_error("Stoppa servern och välj Simulering innan du återställer demodata.")
            return
        if not messagebox.askokcancel(
                "Återställ demodata",
                "Återskapa den påhittade demonstrationen vid nästa start? Dina teständringar "
                "läggs i en separat säkerhetskopia. Den riktiga databasen påverkas inte.",
                parent=self.root):
            return
        try:
            backup = reset_simulation(self.storage)
            self.status.set("Demodata återskapas vid nästa start.")
            self.append_log(f"[DEMO] Återställning klar. Tidigare demo: {backup or 'ingen'}\n")
        except (OSError, ValueError) as error:
            self.report_error(error)

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
            self.deadline = time.monotonic() + 60
            self.start_button.configure(state="disabled")
            self.stop_button.configure(state="normal")
            self.reset_simulation_button.configure(state="disabled")
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
            self.update_fields()
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
            self.report_error(f"Servern svarade inte inom 60 sekunder. Se loggen:\n{self.log_path}")
            return
        if not self.probe_pending and time.monotonic() >= self.next_probe:
            self.start_probe()
        self.check_id = self.root.after(500, self.check_process)

    def open_browser(self) -> None:
        if not webbrowser.open(self.url):
            self.report_error(f"Kunde inte öppna webbläsaren. Öppna adressen manuellt:\n{self.url}")

    def check_updates(self) -> None:
        if self.update_check_running:
            return
        if self.update_check_id is not None:
            self.root.after_cancel(self.update_check_id)
            self.update_check_id = None
        self.update_check_running = True
        self.check_updates_button.configure(state="disabled")
        self.update_status.set("Söker efter uppdateringar på GitHub...")

        def run() -> None:
            try:
                self.update_results.put((check_for_updates(), ""))
            except (OSError, ValueError, HTTPException) as error:
                self.update_results.put((None, str(error)))

        Thread(target=run, daemon=True).start()
        self.update_check_id = self.root.after(100, self.receive_update_check)

    def receive_update_check(self) -> None:
        from tkinter import messagebox
        self.update_check_id = None
        try:
            result, error = self.update_results.get_nowait()
        except Empty:
            self.update_check_id = self.root.after(100, self.receive_update_check)
            return
        self.update_check_running = False
        self.check_updates_button.configure(state="normal")
        if error or result is None:
            self.report_update_error(error or "Versionskontrollen saknar resultat.")
            return
        if result.latest_version is None:
            self.update_status.set("Ingen publicerad release kunde hittas. Programmet kan startas som vanligt.")
            return
        release = result.available
        if release is None:
            self.update_status.set(f"Ingen nyare version. Installerad/körd version: {VERSION}. Senaste publicerade: {result.latest_version}.")
            return
        self.update_status.set(f"Version {release.version} finns att ladda ner. Du har {VERSION}.")
        source_note = "" if is_frozen() else "\nBAT-startens källkod uppdateras inte av installationsfilen."
        if messagebox.askyesno(
                "Uppdatering finns",
                f"Version {release.version} finns tillgänglig. Du har {VERSION}.\n\n"
                f"{release.notes or 'Versionsinformation finns på versionssidan.'}\n\n"
                "Vill du ladda ner installationsfilen i din webbläsare?\n"
                "Stoppa servern och stäng startfönstret före installation. "
                "Databas och inställningar behålls. Filen är osignerad."
                f"{source_note}", parent=self.root):
            try:
                if not webbrowser.open(release.download_url):
                    raise OSError("Webbläsaren kunde inte öppnas. Använd knappen Versionssida.")
                self.update_status.set("Nedladdningen har öppnats i webbläsaren. Stoppa servern och stäng detta fönster före installation. Ingen installation startas automatiskt.")
            except OSError as error:
                self.report_update_error(str(error))

    def report_update_error(self, error: str) -> None:
        self.update_status.set("Uppdateringskontrollen misslyckades – se loggen. Programmet kan startas som vanligt.")
        self.append_log(f"[UPPDATERING FEL] {error}\n")

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
        self.update_fields()
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
        if self.update_check_id is not None:
            self.root.after_cancel(self.update_check_id)
            self.update_check_id = None
        self.root.destroy()


if __name__ == "__main__":
    Launcher().root.mainloop()
