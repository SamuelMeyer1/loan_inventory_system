# Codex Project Notes

This file is the quick project context for future Codex sessions. Read it first,
then inspect only the files needed for the current task.

## Project

Loan Inventory System is a local prototype for lending, returning, issuing, and
tracking inventory items. It uses a Python standard-library backend, SQLite, and
a static HTML/CSS/JavaScript frontend served by the backend.

## Run

- Start from the repo root with `python main.py`.
- Open `http://127.0.0.1:8000`.
- The app creates and migrates `data/inventory.db` on startup.
- `requirements.txt` only contains `openpyxl`, used by the Excel import script.

## Structure

- `main.py` starts `backend.server.run_server()`.
- `backend/server.py` defines the HTTP server, static file serving, and API
  routing.
- `backend/database.py` owns the SQLite path, connection helper, schema setup,
  and lightweight migrations.
- `backend/services/` contains business logic split by domain:
  `inventory.py`, `loans.py`, `users.py`, `stats.py`, `notifications.py`, and
  shared helpers in `common.py`.
- `backend/services/__init__.py` re-exports service functions used by
  `backend/server.py`.
- `backend/seed_data.py` seeds demo/default data.
- `frontend/index.html` is the static UI shell.
- `frontend/styles.css` is the main stylesheet.
- `frontend/js/` contains browser code. `app.js` owns state and rendering,
  `api.js` owns fetch helpers, `actions.js` owns form/API actions,
  `loan-views.js` owns loan-specific views, `i18n.js` and `translations.js`
  handle Swedish/English UI text, and `charts.js` renders statistics charts.
- `scripts/import_articles_excel.py` imports MaintMaster/Excel exports into the
  SQLite database.
- `uppdates` is the project log. For user-visible updates, bump the version and
  add a short entry at the top.
- `Ides` contains future feature ideas from the user.

## Data And Safety

- Treat `data/inventory.db` as live local app data.
- Do not delete or replace database files or backups unless the user explicitly
  asks.
- Avoid committing or intentionally editing `__pycache__/` files.
- If an API endpoint is added or renamed, update both `backend/server.py` and
  `backend/services/__init__.py`, then update frontend callers.
- When changing schema, prefer adding migration logic in
  `backend/database.py` so existing local databases keep working.

## Current Behaviors

- UI roles are simulated in the top bar: operator, admin, and super admin.
- Main workflows include checkout, return, pickup/jobs, consumable reports,
  object/user admin, statistics, event log, and system/notification settings.
- Images can be stored in SQLite via object `image_data`.
- Notification settings and reminder sending live in
  `backend/services/notifications.py`.

## Verification

- At minimum, run `python -m compileall backend main.py` after backend changes.
- For frontend-only changes, start `python main.py` and smoke-test the affected
  browser workflow at `http://127.0.0.1:8000`.
- There is no dedicated test suite in the repo right now.
