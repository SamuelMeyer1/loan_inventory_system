from __future__ import annotations

from contextlib import ExitStack
import json
import os
import mimetypes
import ipaddress
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backend.database import initialize_database, row
from backend import database
from backend.seed_data import seed_database
from backend.simulation_data import seed_simulation
from simulation_store import is_simulation, simulation_guard, validate_simulation
from backend import services
from backend.http_access import AccessMixin
from backend.security import initialize_local_test_accounts


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"


class AppHandler(AccessMixin, BaseHTTPRequestHandler):
    server_version = "LoanInventoryHTTP/1.0"

    def dispatch(self, method):
        started = time.perf_counter()
        self.response_status = "-"
        try:
            super().dispatch(method)
        except ConnectionError:
            self.report_disconnect()
        finally:
            if os.environ.get("LOAN_SERVER_DIAGNOSTICS") == "1":
                elapsed = (time.perf_counter() - started) * 1000
                print(f"[HTTP] {method} {self.response_status} {elapsed:.1f} ms", flush=True)

    def report_disconnect(self) -> None:
        self.close_connection = True
        self.response_status = "DISCONNECTED"
        print("[HTTP] Anslutningen avbröts innan svaret kunde levereras. "
              "Begäran skickas inte om automatiskt.", flush=True)

    def log_request(self, code="-", size="-"):
        # Exclude URLs, headers, IP addresses and payloads from diagnostics.
        self.response_status = code

    def _do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, parse_qs(parsed.query))
            return
        self.serve_static(parsed.path)

    def _do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_error(404)
            return

        try:
            payload = self.read_json()
            if parsed.path == "/api/admin-notifications/read":
                self.send_json({"ok": True, "data": services.mark_admin_notifications_read(payload)})
            elif parsed.path == "/api/checkout":
                self.send_json({"ok": True, "data": services.checkout(payload)})
            elif parsed.path == "/api/issue":
                self.send_json({"ok": True, "data": services.issue_item(payload)})
            elif parsed.path == "/api/return":
                self.send_json({"ok": True, "data": services.return_item(payload)})
            elif parsed.path == "/api/damaged-returns/resolve":
                self.send_json({"ok": True, "data": services.resolve_damaged_return(payload)})
            elif parsed.path == "/api/objects":
                self.send_json({"ok": True, "data": services.add_object(payload)})
            elif parsed.path == "/api/users":
                self.send_json({"ok": True, "data": services.add_user(payload)})
            elif parsed.path == "/api/users/borrow-override":
                self.send_json({"ok": True, "data": services.set_user_borrow_override(payload)})
            elif parsed.path == "/api/users/card":
                self.send_json({"ok": True, "data": services.set_user_card(payload)})
            elif parsed.path == "/api/smartcard/read":
                self.send_json({"ok": True, "data": {"uid": services.read_card_uid()}})
            elif parsed.path == "/api/users/scan-card":
                self.send_json({"ok": True, "data": services.read_user_card()})
            elif parsed.path == "/api/groups":
                self.send_json({"ok": True, "data": services.create_group(payload)})
            elif parsed.path == "/api/loan-requests":
                self.send_json({"ok": True, "data": services.create_loan_request(payload)})
            elif parsed.path == "/api/consumable-reports":
                self.send_json({"ok": True, "data": services.create_consumable_report(payload)})
            elif parsed.path == "/api/reminders/send":
                self.send_json({"ok": True, "data": services.send_loan_reminders()})
            elif parsed.path == "/api/loans/reminder":
                self.send_json({"ok": True, "data": services.send_loan_reminder(int(payload.get("loan_id", 0)))})
            elif parsed.path == "/api/loan-requests/pickup-email":
                self.send_json({"ok": True, "data": services.send_pickup_ready_email(int(payload.get("request_id", 0)))})
            elif parsed.path == "/api/teams/test":
                self.send_json({"ok": True, "data": services.send_teams_test_message()})
            else:
                self.send_error(404)
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)

    def _do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/objects", "/api/users", "/api/groups", "/api/loan-requests"):
            self.send_error(404)
            return

        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/loan-requests":
                request_id = int(query.get("request_id", ["0"])[0])
                self.send_json({"ok": True, "data": services.delete_loan_request(request_id)})
            elif parsed.path == "/api/groups":
                group_id = int(query.get("group_id", ["0"])[0])
                self.send_json({"ok": True, "data": services.delete_group(group_id)})
            elif parsed.path == "/api/users":
                user_id = query.get("user_id", [""])[0]
                self.send_json({"ok": True, "data": services.remove_user(user_id)})
            else:
                object_id = query.get("object_id", [""])[0]
                self.send_json({"ok": True, "data": services.delete_object(object_id)})
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)

    def _do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/loan-requests":
            try:
                payload = self.read_json()
                if payload.get("request_group_id"):
                    data = services.update_loan_request_group_status(payload)
                else:
                    data = services.update_loan_request_status(payload)
                self.send_json({"ok": True, "data": data})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return
        if parsed.path == "/api/loan-requests/details":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_loan_request_details(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return
        if parsed.path == "/api/consumable-reports":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.close_consumable_report(int(payload.get("report_id", 0)))})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return
        if parsed.path == "/api/system-settings":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_system_settings(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return
        if parsed.path == "/api/users":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_user(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return
        if parsed.path == "/api/groups":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_group(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)
            return

        if parsed.path != "/api/objects":
            self.send_error(404)
            return

        try:
            payload = self.read_json()
            self.send_json({"ok": True, "data": services.update_object(payload)})
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, status=500)

    def handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
        if path == "/api/damaged-returns":
            self.send_json({"ok": True, "data": services.list_damaged_returns()})
            return
        if path == "/api/stats":
            self.send_json({"ok": True, "data": services.dashboard_stats()})
        elif path == "/api/statistics":
            self.send_json({"ok": True, "data": services.statistics_data()})
        elif path == "/api/objects":
            self.send_json(
                {
                    "ok": True,
                    "data": services.list_objects(
                        search=query.get("search", [""])[0],
                        category=query.get("category", ["Alla"])[0],
                        status=query.get("status", ["Alla"])[0],
                    ),
                }
            )
        elif path == "/api/search":
            term = query.get("q", [""])[0]
            limit = int(query.get("limit", ["8"])[0])
            self.send_json({"ok": True, "data": services.search_objects(term, limit)})
        elif path == "/api/users":
            include_inactive = query.get("include_inactive", ["0"])[0] in ("1", "true", "yes")
            self.send_json({"ok": True, "data": services.list_users(include_inactive)})
        elif path == "/api/groups":
            self.send_json({"ok": True, "data": services.list_groups()})
        elif path == "/api/loans":
            self.send_json({"ok": True, "data": services.list_active_loans()})
        elif path == "/api/loan-requests":
            self.send_json({"ok": True, "data": services.list_loan_requests()})
        elif path == "/api/consumable-reports":
            self.send_json({"ok": True, "data": services.list_consumable_reports()})
        elif path == "/api/admin-notifications":
            self.send_json({"ok": True, "data": services.list_admin_notifications()})
        elif path == "/api/events":
            limit = int(query.get("limit", ["100"])[0])
            self.send_json({"ok": True, "data": services.recent_events(limit)})
        elif path == "/api/system-settings":
            self.send_json({"ok": True, "data": services.get_public_system_settings()})
        else:
            self.send_error(404)

    def serve_static(self, request_path: str) -> None:
        relative_path = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
        file_path = (FRONTEND_DIR / relative_path).resolve()

        if FRONTEND_DIR.resolve() not in file_path.parents and file_path != FRONTEND_DIR.resolve():
            self.send_error(403)
            return
        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        content = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)

    def read_json(self) -> dict:
        if hasattr(self, "json_payload"):
            return self.json_payload
        if self.headers.get("Transfer-Encoding"):
            raise ValueError("Transfer-Encoding stöds inte.")
        length = int(self.headers.get("Content-Length", "0"))
        if not 0 <= length <= 4 * 1024 * 1024:
            raise ValueError("Begäran är för stor.")
        if length and self.headers.get_content_type() != "application/json":
            raise ValueError("Använd application/json.")
        payload = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        if not isinstance(payload, dict):
            raise ValueError("JSON måste vara ett objekt.")
        self.json_payload = payload
        return payload

    def send_json(self, payload: dict, status: int = 200) -> None:
        payload = self.filter_response(payload)
        self.response_status = status
        self.record_audit(status)
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        try:
            self.end_headers()
            self.wfile.write(body)
        except ConnectionError:
            self.report_disconnect()

    def log_message(self, format: str, *args) -> None:
        pass  # Do not write IP addresses, query strings or submitted identifiers to stdout.


def _validated_bind_host(host: str | None) -> str:
    if host is None:
        host = os.environ.get("LOAN_HOST", "127.0.0.1")
    if host in ("127.0.0.1", "localhost"):
        return host
    if os.environ.get("LOAN_ALLOW_LAN") != "1":
        raise ValueError("LAN-test kräver uttryckligt val: sätt LOAN_ALLOW_LAN=1.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError as error:
        raise ValueError("LOAN_HOST måste vara en privat IPv4-adress för LAN-test.") from error
    lan_networks = (
        ipaddress.ip_network("10.0.0.0/8"),
        ipaddress.ip_network("172.16.0.0/12"),
        ipaddress.ip_network("192.168.0.0/16"),
    )
    if not isinstance(address, ipaddress.IPv4Address) or not any(address in network for network in lan_networks):
        raise ValueError("LAN-test får endast bindas till en privat IPv4-adress, inte 0.0.0.0 eller en publik adress.")
    return host


def run_server(host: str | None = None, port: int = 8000) -> None:
    host = _validated_bind_host(host)
    simulation = os.environ.get("LOAN_SIMULATION") == "1"
    if simulation and host not in ("127.0.0.1", "localhost"):
        raise ValueError("Simulering får endast köras lokalt.")
    if simulation:
        simulation_path = database.DATABASE_PATH.resolve()
        if (not os.environ.get("LOAN_DATABASE_PATH")
                or simulation_path == (ROOT_DIR / "data" / "inventory.db").resolve()):
            raise ValueError("Simulering kräver en separat demodatabas från startfönstret.")
        validate_simulation(simulation_path)
    anonymous_operator = host not in ("127.0.0.1", "localhost")
    fixed_test_credentials = os.environ.get("LOAN_LOCAL_FIXED_TEST_CREDENTIALS") == "1"
    if fixed_test_credentials and anonymous_operator:
        raise ValueError("Fasta lokala testinloggningar får inte användas i LAN-läge.")
    server = ThreadingHTTPServer((host, port), AppHandler, bind_and_activate=False)
    guards = ExitStack()
    try:
        # Reserve the port now, but do not queue clients until startup is complete.
        server.server_bind()
        if simulation:
            guards.enter_context(simulation_guard(database.DATABASE_PATH))
            validate_simulation(database.DATABASE_PATH)
        elif is_simulation(database.DATABASE_PATH):
            raise ValueError("En simuleringsdatabas får bara öppnas i Simulering, inte Lokalt eller Nätverk.")
        initialize_database()
        if anonymous_operator and row("SELECT username FROM local_test_accounts LIMIT 1"):
            raise ValueError("Databasen innehåller låsta lokala testkonton och får inte användas i LAN-läge.")
        if fixed_test_credentials or simulation:
            initialize_local_test_accounts()
        if simulation:
            seed_simulation()
        elif os.environ.get("LOAN_SEED_DEMO") == "1":
            seed_database()
        server.allowed_hosts = {f"{host}:{server.server_port}"}
        if host in ("127.0.0.1", "localhost"):
            server.allowed_hosts |= {f"127.0.0.1:{server.server_port}", f"localhost:{server.server_port}"}
            if server.server_port == 80:
                server.allowed_hosts |= {"localhost", "127.0.0.1"}
        server.anonymous_operator = anonymous_operator
        server.local_operator = host in ("127.0.0.1", "localhost")
        server.simulation = simulation
        server.instance_id = os.environ.get("LOAN_INSTANCE_ID", "")
        server.server_activate()
        print(f"Loan Inventory System running at http://{host}:{server.server_port}", flush=True)
        print("Press Ctrl+C to stop.")
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        try:
            server.server_close()
        finally:
            guards.close()
