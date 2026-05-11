from __future__ import annotations

import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from backend.database import initialize_database
from backend.seed_data import seed_database
from backend import services


ROOT_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = ROOT_DIR / "frontend"


class AppHandler(BaseHTTPRequestHandler):
    server_version = "LoanInventoryHTTP/1.0"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/"):
            self.handle_api_get(parsed.path, parse_qs(parsed.query))
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            self.send_error(404)
            return

        try:
            payload = self.read_json()
            if parsed.path == "/api/checkout":
                self.send_json({"ok": True, "data": services.checkout(payload)})
            elif parsed.path == "/api/issue":
                self.send_json({"ok": True, "data": services.issue_item(payload)})
            elif parsed.path == "/api/return":
                self.send_json({"ok": True, "data": services.return_item(payload)})
            elif parsed.path == "/api/objects":
                self.send_json({"ok": True, "data": services.add_object(payload)})
            elif parsed.path == "/api/users":
                self.send_json({"ok": True, "data": services.add_user(payload)})
            elif parsed.path == "/api/loan-requests":
                self.send_json({"ok": True, "data": services.create_loan_request(payload)})
            elif parsed.path == "/api/consumable-reports":
                self.send_json({"ok": True, "data": services.create_consumable_report(payload)})
            elif parsed.path == "/api/reminders/send":
                self.send_json({"ok": True, "data": services.send_loan_reminders()})
            else:
                self.send_error(404)
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)

    def do_DELETE(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in ("/api/objects", "/api/users", "/api/loan-requests"):
            self.send_error(404)
            return

        try:
            query = parse_qs(parsed.query)
            if parsed.path == "/api/loan-requests":
                request_id = int(query.get("request_id", ["0"])[0])
                self.send_json({"ok": True, "data": services.delete_loan_request(request_id)})
            elif parsed.path == "/api/users":
                user_id = query.get("user_id", [""])[0]
                self.send_json({"ok": True, "data": services.remove_user(user_id)})
            else:
                object_id = query.get("object_id", [""])[0]
                self.send_json({"ok": True, "data": services.delete_object(object_id)})
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error)}, status=400)
        except Exception as error:
            self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)

    def do_PUT(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/loan-requests":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_loan_request_status(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)
            return
        if parsed.path == "/api/consumable-reports":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.close_consumable_report(int(payload.get("report_id", 0)))})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)
            return
        if parsed.path == "/api/system-settings":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_system_settings(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)
            return
        if parsed.path == "/api/users":
            try:
                payload = self.read_json()
                self.send_json({"ok": True, "data": services.update_user(payload)})
            except ValueError as error:
                self.send_json({"ok": False, "error": str(error)}, status=400)
            except Exception as error:
                self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)
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
            self.send_json({"ok": False, "error": f"Serverfel: {error}"}, status=500)

    def handle_api_get(self, path: str, query: dict[str, list[str]]) -> None:
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
        elif path == "/api/loans":
            self.send_json({"ok": True, "data": services.list_active_loans()})
        elif path == "/api/loan-requests":
            self.send_json({"ok": True, "data": services.list_loan_requests()})
        elif path == "/api/consumable-reports":
            self.send_json({"ok": True, "data": services.list_consumable_reports()})
        elif path == "/api/events":
            limit = int(query.get("limit", ["100"])[0])
            self.send_json({"ok": True, "data": services.recent_events(limit)})
        elif path == "/api/system-settings":
            self.send_json({"ok": True, "data": services.get_system_settings()})
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
        length = int(self.headers.get("Content-Length", "0"))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        print(f"{self.address_string()} - {format % args}")


def run_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    initialize_database()
    seed_database()
    server = ThreadingHTTPServer((host, port), AppHandler)
    print(f"Loan Inventory System running at http://{host}:{port}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
    finally:
        server.server_close()
