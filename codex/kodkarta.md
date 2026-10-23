# Kodkarta efter arbetsflöde

Verifierad mot arbetskopian 2026-09-30. Funktionsnamnen är sökankare;
kontrollera aktuell kod när något har flyttats.

| Uppgift | Frontend | Backend / tester |
| --- | --- | --- |
| Startfönster / isolerad simulering | `launcher.py`, `Starta.bat`; `session.js` visar miljömärkning | `main.py --port`, `server.py`, transport-/kortläsarspärrar; `test_launcher.py` |
| Inloggning / åtkomst | `session.js`, `api.js`, `app.js` | `security.py`, `http_access.py`, `manage_access.py`; `test_privacy_access.py` |
| Dataskydd / gallring | `frontend/privacy.html`, `privacy.js` | `services/privacy.py`; användarrutin i `docs/dataskydd.md` |
| Lånekorg och förfrågan | `loan-views.js`: `addLoanArticle`, `renderLoanCart`; `actions.js`: `requestLoan` | `loans.py`: `create_loan_request`; båda filerna i `tests/` |
| Direktutlåning / uttag | `actions.js`: `checkout`, `checkoutPayload` | `loans.py`: `checkout`, `issue_item` |
| Återlämning / skador | `loan-views.js`: `renderReturnLoans`, `renderReturnSummary`, `renderDamagedReturns`; `actions.js`: `returnSelectedLoans`, `resolveDamage` | `loans.py`: `return_item`, `resolve_damaged_return`; `test_partial_returns.py`, `test_loan_cart.cjs`, åtkomsttesterna |
| Jobb / hämtning | `app.js`: `renderJobs`, `renderJobGroup`; `loan-views.js`: `renderPickupItems`; `actions.js`: `updateJobGroupStatus` | `loans.py`: `update_loan_request_group_status`, `ensure_loan_for_request` |
| Objekt / lager / bilder | `app.js`: `renderObjects`, `renderAdminObjectsTable`, `resizeObjectImage`; objektformulär i `bindEvents` | `inventory.py`; schema i `database.py` |
| Förbrukningsrapport | `app.js`: `renderConsumableReports`; `actions.js`: `saveConsumableReport` | `loans.py`: `create_consumable_report`, `close_consumable_report` |
| Användare / grupper | `app.js`: `renderUsersTable`, `renderGroups`; `actions.js`: `saveUser`, `saveGroup` | `users.py` |
| Kortläsning | `actions.js`: `autoScanCheckoutUserCard`, `scanCheckoutUserCard` | `smartcard.py`; `users.py`: `set_user_card` |
| Inställningar / notiser | `app.js`: `renderSystemSettings`; `actions.js`: `saveSystemSettings` | `notifications.py`; notisanrop även i `loans.py` |
| Statistik | `charts.js`; `app.js`: `renderStats`, `refreshAll` | `stats.py`: `dashboard_stats`, `statistics_data` |
| Språk / layout | `translations.js`, `i18n.js`, `index.html`, `styles.css` | Vanligen ingen backendändring |
| Sökning | `search.js`, `api.js`: `searchApi`; lokala filter även i `app.js` | `inventory.py`: `search_objects`, `list_objects` |
| Installation / import | `windows-installation/`; `scripts/README.md` | `scripts/import_articles_excel.py`, `seed_demo_activity.py` |
| Windows Setup / versionssida | `launcher.py`, `app_version.py`; `windows-installation/SETUP.md` | `desktop_entry.py`, `app_runtime.py`, `Build-Setup.ps1`, `.spec`/`.iss`; `test_packaging.py`, `smoke_bundle.py` |

Alla JS-filer ovan ligger i `frontend/js/`; servicefilerna ligger i
`backend/services/`. Läs `backend/server.py` och `backend/services/__init__.py`
när du behöver följa en endpoint. JSON-klienten finns i `frontend/js/api.js`.

Exempel på avgränsad sökning från projektroten:

```powershell
rg -n 'requestLoan|create_loan_request|/api/loan-requests' frontend/js backend tests
rg -n '^function |^async function ' frontend/js/app.js
rg -n '^def ' backend/services/loans.py
```

Frontend använder vanliga script-taggar och delade globala namn, inte ES-moduler.
`app.js` laddas sist och kör `init()`. Vid uppdelning måste scriptordning,
globala beroenden och tester som laddar filer via Node `vm` hanteras tillsammans.
