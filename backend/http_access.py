"""HTTP access boundary: every API route is denied unless explicitly allowed."""
import hmac
import threading
from urllib.parse import urlparse, parse_qs

from backend import security
from backend.database import connect, rows
from datetime import datetime
from backend.services import privacy

_initialization_lock = threading.Lock()
READ = {"/api/stats", "/api/objects", "/api/object-categories", "/api/search", "/api/users", "/api/loans", "/api/loan-requests", "/api/system-settings"}
ADMIN_READ = {"/api/statistics", "/api/groups", "/api/consumable-reports", "/api/damaged-returns", "/api/admin-notifications"}
SUPER_READ = {"/api/events", "/api/privacy/export", "/api/privacy/policy", "/api/privacy/retention", "/api/privacy/erase"}
ADMIN_WRITE = {
    ("POST", path) for path in ("/api/checkout", "/api/issue", "/api/objects", "/api/object-categories", "/api/users", "/api/users/borrow-override", "/api/users/card", "/api/smartcard/read", "/api/users/scan-card", "/api/groups", "/api/loans/reminder", "/api/loan-requests/pickup-email")
} | {("PUT", path) for path in ("/api/objects", "/api/users", "/api/groups", "/api/loan-requests/details", "/api/consumable-reports")} | {
    ("DELETE", path) for path in ("/api/objects", "/api/users", "/api/groups", "/api/loan-requests")}
ADMIN_WRITE.add(("POST", "/api/damaged-returns/resolve"))
ADMIN_WRITE.add(("POST", "/api/admin-notifications/read"))
SUPER_WRITE = {("PUT", "/api/system-settings"), ("POST", "/api/reminders/send"), ("POST", "/api/teams/test"),
               ("PUT", "/api/privacy/policy"), ("POST", "/api/privacy/erase"), ("POST", "/api/privacy/retention")}


class AccessMixin:
    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_PUT(self):
        self.dispatch("PUT")

    def do_DELETE(self):
        self.dispatch("DELETE")

    def dispatch(self, method):
        self.identity = None
        self.pending_cookie = None
        parsed = urlparse(self.path)
        self.api_path = parsed.path
        port = self.server.server_port
        allowed_hosts = getattr(self.server, "allowed_hosts", {f"127.0.0.1:{port}", f"localhost:{port}"})
        if port == 80 and not hasattr(self.server, "allowed_hosts"):
            allowed_hosts |= {"localhost", "127.0.0.1"}
        host = self.headers.get("Host", "")
        if host not in allowed_hosts:
            self.send_json({"ok": False, "error": "Ogiltig värd."}, 403)
            return
        if not parsed.path.startswith("/api/"):
            getattr(self, "_do_"+method)()
            return
        with _initialization_lock:
            if not hasattr(self.server, "access"):
                self.server.access = security.AccessState()
        access = self.server.access
        try:
            if self.headers.get("Sec-Fetch-Site") == "cross-site":
                self.send_json({"ok": False, "error": "Begäran från annan webbplats nekas."}, 403)
                return
            if method != "GET":
                origin = self.headers.get("Origin")
                if (origin and origin != f"http://{host}") or self.headers.get("X-Loan-Client") != "browser":
                    self.send_json({"ok": False, "error": "Begäran saknar skydd mot förfalskade anrop."}, 403)
                    return
            if method == "GET" and parsed.path == "/api/privacy/notice":
                self.send_json({"ok": True, "data": privacy.policy()})
                return
            if method == "GET" and parsed.path == "/api/runtime":
                self.send_json({"ok": True, "data": {
                    "simulation": getattr(self.server, "simulation", False),
                    "instance_id": getattr(self.server, "instance_id", ""),
                }})
                return
            if method == "POST" and parsed.path == "/api/auth/login":
                payload = self.read_json()
                token = access.login(payload.get("username", ""), payload.get("password", ""), self.client_address[0])
                access.logout(self.headers.get("Cookie"))
                self.pending_cookie = f"{security.COOKIE}={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age={security.SESSION_SECONDS}"
                identity = access.identify(f"{security.COOKIE}={token}")
                self.identity = identity
                self.send_json({"ok": True, "data": identity})
                return
            self.identity = access.identify(self.headers.get("Cookie"))
            if self.identity is None and (getattr(self.server, "anonymous_operator", False) or getattr(self.server, "local_operator", False)):
                self.identity = {
                    "username": "lan-test-operator",
                    "role": "operator",
                    "user_id": None,
                    "csrf": "lan-test-operator",
                    "expires_in": 0,
                    "anonymous": True,
                }
            if self.identity is None:
                self.send_json({"ok": False, "error": "Logga in för att använda programmet."}, 401)
                return
            if method != "GET" and not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), self.identity["csrf"]):
                self.send_json({"ok": False, "error": "Ogiltigt sessionsskydd. Logga in igen."}, 403)
                return
            if method == "GET" and parsed.path == "/api/auth/session":
                self.send_json({"ok": True, "data": self.identity})
                return
            if method == "POST" and parsed.path == "/api/auth/logout":
                access.logout(self.headers.get("Cookie"))
                self.pending_cookie = f"{security.COOKIE}=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0"
                self.send_json({"ok": True, "data": {}})
                return
            if not self.authorize(method, parsed.path):
                self.send_json({"ok": False, "error": "Du saknar behörighet för åtgärden."}, 403)
                return
            if parsed.path.startswith("/api/privacy/"):
                query = parse_qs(parsed.query)
                subject = query.get("user_id", [""])[0]
                if parsed.path.endswith("/policy"):
                    data = privacy.policy() if method == "GET" else privacy.save_policy(self.read_json())
                elif parsed.path.endswith("/export"):
                    data = privacy.export_subject(subject)
                elif parsed.path.endswith("/erase"):
                    data = privacy.erase_subject(subject) if method == "GET" else privacy.erase_subject(self.confirmed()["user_id"], True)
                else:
                    data = privacy.retention() if method == "GET" else privacy.retention(bool(self.confirmed()))
                self.send_json({"ok": True, "data": data})
                return
            getattr(self, "_do_"+method)()
        except ValueError as error:
            self.send_json({"ok": False, "error": str(error) or "Ogiltiga uppgifter."}, 400)
        except (TypeError, UnicodeError):
            self.send_json({"ok": False, "error": "Ogiltiga uppgifter eller åtgärden kan inte genomföras. Kontrollera underlaget."}, 400)
        except Exception:
            self.send_json({"ok": False, "error": "Ett internt fel inträffade."}, 500)

    def record_audit(self, status):
        method = self.command
        path = self.api_path
        if getattr(self, "audit_written", False) or not hasattr(self.server, "access"):
            return
        if not path.startswith("/api/") or (method == "GET" and not path.startswith("/api/privacy/")) or path == "/api/privacy/notice":
            return
        self.audit_written = True
        identity = self.identity or {}
        # Recheck the account after deletion; do not reintroduce an erased ID.
        with connect() as db:
            account = db.execute("SELECT username,user_id FROM access_accounts WHERE username=?", (identity.get("username"),)).fetchone()
            known_paths = READ | ADMIN_READ | SUPER_READ | {p for _, p in ADMIN_WRITE | SUPER_WRITE} | {
                "/api/auth/login", "/api/auth/logout", "/api/return", "/api/consumable-reports"}
            action = method+" "+(path if path in known_paths else "/api/unknown")
            db.execute("INSERT INTO security_audit(event_time,actor,user_id,action,status) VALUES (?,?,?,?,?)",
                       (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        account["username"] if account else "unauthenticated",
                        account["user_id"] if account else None, action, status))

    def confirmed(self):
        payload = self.read_json()
        if payload.get("confirm") != "DELETE":
            raise ValueError("Uttrycklig bekräftelse krävs.")
        return payload

    def authorize(self, method, path):
        role = self.identity["role"]
        if method == "GET":
            return path in READ or (role in ("admin", "superadmin") and path in ADMIN_READ) or (role == "superadmin" and path in SUPER_READ)
        if (method, path) in SUPER_WRITE:
            return role == "superadmin"
        if (method, path) in ADMIN_WRITE:
            return role in ("admin", "superadmin")
        if (method, path) == ("POST", "/api/consumable-reports"):
            return True
        if (method, path) in (("POST", "/api/loan-requests"), ("POST", "/api/return"), ("PUT", "/api/loan-requests")):
            if role != "operator":
                return True
            if self.identity.get("anonymous"):
                return True
            payload = self.read_json()
            user_id = self.identity["user_id"]
            if path == "/api/loan-requests" and method == "PUT":
                # Self-service collection only; staff approve and prepare loans.
                if payload.get("status") != "loaned":
                    return False
                if payload.get("request_group_id"):
                    matches = rows("SELECT user_id, status FROM loan_requests WHERE COALESCE(request_group_id,request_id)=?", (payload["request_group_id"],))
                else:
                    matches = rows("SELECT user_id, status FROM loan_requests WHERE request_id=?", (payload.get("request_id"),))
                return bool(matches) and all(r["user_id"] == user_id and r["status"] == "prepared" for r in matches)
            if payload.get("user_id") not in (None, "", user_id):
                return False
            if path == "/api/return" and not any(
                isinstance(payload.get(key), list) and payload[key] for key in ("loan_ids", "items")
            ):
                # Legacy identifier-based returns cannot prove ownership.
                return False
            payload["user_id"] = user_id
            return True
        return False

    def filter_response(self, payload):
        if not self.identity or not payload.get("ok"):
            return payload
        role = self.identity["role"]
        data = payload.get("data")
        if self.api_path == "/api/system-settings" and role != "superadmin":
            payload["data"] = {"max_loan_days": data.get("max_loan_days", "90")}
        if role == "operator":
            if self.command == "GET" and self.api_path == "/api/users":
                if not self.identity.get("anonymous"):
                    data = [r for r in data if r.get("user_id") == self.identity["user_id"]]
                payload["data"] = [{
                    key: value for key, value in user.items()
                    if key not in ("rfid_code", "privacy_notice_acknowledged_at", "last_borrowed_at",
                                   "inactive_for_days", "has_pending_activity", "inactivity_warning",
                                   "inactivity_threshold_days")
                } for user in data]
            elif self.command == "GET" and self.api_path in ("/api/loans", "/api/loan-requests"):
                if not self.identity.get("anonymous"):
                    payload["data"] = [r for r in data if r.get("user_id") == self.identity["user_id"]]
                for item in payload["data"]:
                    item.pop("unresolved_damage_description", None)
            elif self.command == "GET" and self.api_path == "/api/stats":
                payload["data"] = {"objects": data.get("objects", 0), "low_stock": data.get("low_stock", 0)}
        return payload

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        if getattr(self, "pending_cookie", None):
            self.send_header("Set-Cookie", self.pending_cookie)
        super().end_headers()
