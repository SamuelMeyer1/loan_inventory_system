# Paminnelser

## Arbetsflode

- Las `AGENTS.md` forst, sedan den har mappen.
- Anvand befintliga monster i `backend/services/` och `frontend/js/`.
- Var forsiktig med `data/inventory.db`; den innehaller anvandarens lokala data.
- Undvik att roka andra redan andrade filer i arbetsytan.

## Appen

- Roller styrs i topbaren: operator, admin och superadmin.
- Forbrukningsvaror ar vanliga objekt med `is_consumable = 1`.
- Forbrukningsvaror ska inte kunna lanas.
- "Anmal slut pa lager" ska vara enkelt: sok artikel och klicka knapp.
- Nar en forbrukningsvara anmals slut pa lager ska saldot sattas till 0.

## Kanda onskemal / ej gjorda saker

- Anvandaren namnde att "Lagg till objekt" eventuellt ska flyttas fran Admin till sidebaren for admin+, men den turen avbrots innan implementation.
- De inlagda andhylsorna finns i live-databasen. Om databasen skapas om fran noll finns de inte automatiskt om de inte laggs till i seed/import.

## Verifiering

- Backend: `python -m compileall backend main.py`.
- Frontend: starta `python main.py`, oppna `http://127.0.0.1:8000`, testa berort flode.
- Servern kan redan vara igang pa port 8000; kontrollera innan du startar en ny.
