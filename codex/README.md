# Codex Project Memory

Las den har mappen i borjan av en ny Codex-session nar anvandaren ber om det.

## Filer

- `paminnelser.md` - korta regler, arbetsvanor och saker att inte glomma.
- `uppdateringar.md` - sammanfattning av andringar vi har gjort nyligen.

## Snabbstart

- Projektet kors fran repo-roten med `python main.py`.
- Appen oppnas pa `http://127.0.0.1:8000`.
- Live-data ligger i `data/inventory.db`; ta inte bort eller ersatt den utan tydlig begaran.
- Efter backend-andringar: kor `python -m compileall backend main.py`.
- Node.js saknas i miljon, sa `node --check` gar normalt inte att kora.

## Viktigt

`uppdates` ar fortfarande den formella projektloggen. Den har `codex`-mappen ar mer som arbetsminne mellan sessioner.
