"""Local prototype authentication. Corporate SSO must be reviewed with IT."""
from __future__ import annotations

import hashlib
import hmac
import secrets
import threading
import time
from http.cookies import SimpleCookie, CookieError

from backend.database import connect, row

SESSION_SECONDS = 1800
COOKIE = "loan_session"


def create_account(username: str, password: str, role: str, user_id: str | None = None) -> None:
    if role not in ("operator", "admin", "superadmin"):
        raise ValueError("Ogiltig roll.")
    if not username or len(username) > 80 or len(password) < 15 or len(password) > 256:
        raise ValueError("Ange kontonamn och ett lösenord med 15–256 tecken.")
    if role == "operator" and not row("SELECT user_id FROM users WHERE user_id = ? AND active = 1", (user_id,)):
        raise ValueError("Operatörskontot måste kopplas till en aktiv låntagare.")
    salt = secrets.token_hex(16)
    digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    with connect() as db:
        db.execute("""INSERT INTO access_accounts (username, salt, password_hash, role, user_id)
                      VALUES (?, ?, ?, ?, ?)
                      ON CONFLICT(username) DO UPDATE SET salt=excluded.salt,
                      password_hash=excluded.password_hash, role=excluded.role,
                      user_id=excluded.user_id, revision=access_accounts.revision+1""",
                   (username, salt, digest, role, user_id))


class AccessState:
    def __init__(self):
        self.lock = threading.Lock()
        self.sessions = {}
        self.failures = {}

    def login(self, username, password, address):
        if not isinstance(username, str) or not isinstance(password, str) or len(username) > 80 or len(password) > 256:
            raise ValueError("Felaktigt kontonamn eller lösenord.")
        now = time.monotonic()
        # Bound work, including expensive password verification, per source.
        with self.lock:
            self.failures = {key: value for key, value in self.failures.items() if now-value[1] < 60}
            count, start = self.failures.get(address, (0, now))
            if count >= 5:
                raise ValueError("För många inloggningsförsök. Vänta en minut.")
            self.failures[address] = (count+1, start)
        account = row("SELECT * FROM access_accounts WHERE username = ?", (username,))
        salt = account["salt"] if account else "00" * 16
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
        if not account or not hmac.compare_digest(digest, account["password_hash"]):
            raise ValueError("Felaktigt kontonamn eller lösenord.")
        if account["role"] == "operator" and not row("SELECT user_id FROM users WHERE user_id = ? AND active = 1", (account["user_id"],)):
            raise ValueError("Kontot är inte tillgängligt.")
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        with self.lock:
            self.sessions = {k: v for k, v in self.sessions.items() if v["expires"] > now}
            self.sessions[hashlib.sha256(token.encode()).hexdigest()] = {
                "username": username, "revision": account["revision"], "csrf": csrf, "expires": now+SESSION_SECONDS}
        return token

    def token(self, cookie):
        try:
            jar = SimpleCookie()
            jar.load(cookie or "")
            return jar[COOKIE].value if COOKIE in jar else ""
        except CookieError:
            return ""

    def identify(self, cookie):
        key = hashlib.sha256(self.token(cookie).encode()).hexdigest()
        with self.lock:
            session = self.sessions.get(key)
            if not session:
                return None
            if session["expires"] <= time.monotonic():
                self.sessions.pop(key, None)
                return None
            session = session.copy()
        account = row("SELECT username, revision, role, user_id FROM access_accounts WHERE username = ?", (session["username"],))
        if not account or account["revision"] != session["revision"]:
            return None
        if account["role"] == "operator" and not row("SELECT user_id FROM users WHERE user_id = ? AND active = 1", (account["user_id"],)):
            return None
        return {"username": account["username"], "role": account["role"], "user_id": account["user_id"], "csrf": session["csrf"],
                "expires_in": max(0, int(session["expires"]-time.monotonic()))}

    def logout(self, cookie):
        with self.lock:
            self.sessions.pop(hashlib.sha256(self.token(cookie).encode()).hexdigest(), None)
