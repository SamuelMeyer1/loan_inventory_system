"""Exercise real login in HTTP tests; never disable the access boundary."""
import json
from urllib.request import Request, urlopen

from backend.security import create_account


def login(server, username="test-admin", password="fictitious-test-password", role="superadmin", user_id=None):
    create_account(username, password, role, user_id)
    base = f"http://127.0.0.1:{server.server_port}"
    request = Request(base+"/api/auth/login", data=json.dumps({"username": username, "password": password}).encode(),
                      headers={"Content-Type": "application/json", "X-Loan-Client": "browser"})
    with urlopen(request) as response:
        cookie = response.headers["Set-Cookie"].split(";", 1)[0]
        session = json.load(response)["data"]
    return {"Content-Type": "application/json", "X-Loan-Client": "browser", "Cookie": cookie, "X-CSRF-Token": session["csrf"]}
