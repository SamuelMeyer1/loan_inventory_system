# Codex Project Notes

Local loan/inventory prototype: Python HTTP server, SQLite and static HTML/CSS/JS.
Start from the repo root: `python main.py`; open `http://127.0.0.1:8000`.
`requirements.txt` contains `openpyxl` (Excel import) and `pyscard` (card reader).

## Read only what the task needs

- Use `codex/README.md` as the documentation index when orientation is needed.
- Find files by workflow in `codex/kodkarta.md`; read relevant functions and callers.
- Use `codex/arbetsflode.md` for task examples and verification commands.
- Read `codex/paminnelser.md` for loan, stock, notification or migration changes.
- Read `codex/forbattringar.md` for architecture/review tasks, not routine edits.
- `codex/uppdateringar.md` is historical context, not current application truth.
- Search with `rg -n` in relevant folders. Avoid reading whole large files,
  database contents, logs, installers or full history without a task reason.

## Code boundaries

- `main.py` → `backend/server.py` → `backend/services/` → `backend/database.py`.
- Services own business rules; `services/__init__.py` exports server entry points.
- Physical device protocols belong in `hardware/<device>/`; keep user lookup,
  database writes and authorization in backend service adapters.
- External software transports belong in `software/<integration>/`; keep
  notification policy, simulation safeguards and secrets in backend services.
- Frontend uses shared globals and ordered scripts in `frontend/index.html`.
  `app.js` owns state/rendering; `actions.js` handles actions; `api.js` handles fetch.
- Schema changes need migration logic in `backend/database.py` for existing data.
- API changes must keep server routes, service exports and frontend callers aligned.
- UI text changes may require both languages in `frontend/js/translations.js`.

## Data and existing work

- Check `git status --short`; preserve unrelated work, including untracked files.
- `data/inventory.db` and backups are live local data. Never delete or replace
  them without an explicit request. Use temporary databases for automated tests.
- Startup migrates data; demo seed is explicit. Import/demo scripts can change live data.
- Mock email/Teams/card readers in tests; notification simulation can still send.
- Avoid committing or intentionally editing `__pycache__/` files.
- API access is enforced by `backend/http_access.py`; local hashed-password accounts
  are managed by `python -B -m backend.manage_access`. Do not bypass this in tests.
- `docs/dataskydd.md` describes privacy scope and deployment limitations. Tests
  must use temporary `DATABASE_PATH`; `LOAN_DATABASE_PATH` selects an isolated UI DB.
- Normal startup no longer seeds data. Demo seed requires `LOAN_SEED_DEMO=1`.
- External notifications are blocked unless `LOAN_ENABLE_NOTIFICATIONS=1`;
  simulation still needs mocks. Never enable transports for automated tests.
- Existing Git-tracked data/backups need a separate review before publication.

## Verification and documentation

- Backend changes: `python -m compileall backend main.py` and affected tests.
- Loan/API regression suite: `python -B -m unittest discover -s tests -p 'test_*.py'`.
- Loan frontend actions: `node tests/test_loan_cart.cjs` plus browser smoke test.
- Frontend changes: start/reuse the local server and smoke-test the affected flow.
  Node syntax/unit checks do not replace browser verification.
- Documentation-only edits: check links, commands and diff; no app startup needed.
- User-visible updates: bump the version and prepend a short entry in `uppdates`.
  `Ides` holds user ideas. Keep Codex notes compact and update only affected facts.
