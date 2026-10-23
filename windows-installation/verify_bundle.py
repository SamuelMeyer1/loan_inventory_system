"""Check the distribution allowlist before it can become an installer."""
from pathlib import Path
import sys

root = Path(sys.argv[1]).resolve()
required = (
    "LoanInventory.exe", "LoanInventoryAdmin.exe", "_internal\\frontend\\index.html",
    "_internal\\frontend\\js\\app.js", "_internal\\_tkinter.pyd",
)
for name in required:
    if not (root / name).is_file():
        raise SystemExit(f"Missing bundled runtime file: {name}")
for path in root.rglob("*"):
    if not path.is_file():
        continue
    relative = path.relative_to(root)
    if path.suffix.lower() in (".db", ".sqlite", ".sqlite3", ".log", ".bak", ".ps1", ".bat"):
        raise SystemExit(f"Forbidden packaged file: {relative}")
    if any(part.lower() in ("data", "backups", ".git", ".env", ".work", "tests") for part in relative.parts):
        raise SystemExit(f"Forbidden packaged directory: {relative}")
    if path.name.lower() in ("preferences.json", "accounts.json"):
        raise SystemExit(f"Forbidden user state: {relative}")
print("Bundle allowlist/privacy checks passed.")
