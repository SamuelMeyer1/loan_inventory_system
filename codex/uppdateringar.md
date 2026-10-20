# Uppdateringar Vi Gjort

Senast uppdaterad: 2026-09-30

## 2026-09-30 — Projektminne och kodgranskning

- Kortade och rättade `AGENTS.md`; stödtexter läses efter uppgift.
- Lade till `kodkarta.md`, `arbetsflode.md` och `forbattringar.md`.
- Rättade uppgifterna om tester, Node och Python-beroenden.
- Baslinje: 14 Python-tester samt Node-test för lånekorg/återlämning godkända.
- Nästa föreslagna arbete: transaktioner vid direktuttag och publika inställningssvar.
- Ingen appkod ändrad. Äldre anteckningar nedan är historik, inte aktuell datastatus.

## Historik från 2026-05-27

## UI och arbetsfloden

- Lade till Scanna anvandare-knapp i Lana-vyn med scanner-dialog for framtida RFID-lasare.
- Lade till Scanna objekt-knapp i Lana-vyn med scanner-dialog for framtida RFID-/streckkodslasare.
- Tydliggjorde Tips & tricks-kortet for Mina utlaningar.
- Tog bort texten "Lokal HTML-prototyp" fran sidomenyn.
- Tog bort statusfiltret "Alla statusar" fran Jobb-vyn.
- Justerade Jobb-vyns filterrad till sokfalt, datum-sortering och "Dolj jobb".
- Forenklade "Anmal slut pa lager" till endast sok forbrukningsvara och knapp.
- Tog bort antal, rapporterad av och kommentar fran forbrukningsrapporten.

## Backend och data

- Forbrukningsrapport satter nu artikelns `available_quantity` till `0`.
- Fixade att `is_consumable` skickas nar objekt sparas fran adminformular.
- Fixade att forbrukningsflaggan visas korrekt nar objekt redigeras.
- Gjorde "Failed to fetch" tydligare i frontend: visar instruktion om att starta backend med `python main.py`.

## Live-data som lades in

Foljande forbrukningsvaror lades in direkt i `data/inventory.db`:

- `ANDHYLSA-05MM2` - Andhylsa 0,5 mm2
- `ANDHYLSA-075MM2` - Andhylsa 0,75 mm2
- `ANDHYLSA-10MM2` - Andhylsa 1,0 mm2
- `ANDHYLSA-15MM2` - Andhylsa 1,5 mm2
- `ANDHYLSA-25MM2` - Andhylsa 2,5 mm2
- `ANDHYLSA-40MM2` - Andhylsa 4 mm2
- `ANDHYLSA-60MM2` - Andhylsa 6 mm2
- `ANDHYLSA-100MM2` - Andhylsa 10 mm2

Alla har:

- kategori: Andhylsor
- saldo: 100 av 100
- min-niva: 20
- `is_consumable = 1`
- plats: Elforrad / Andhylsor

## Versioner i `uppdates`

- V1.1.4 - tog bort sidomenytexten.
- V1.1.3 - tog bort statusfiltret i Jobb-vyn.
- V1.1.2 - forenklade forbrukningsrapportering.
- V1.1.1 - fixade forbrukningsflagga och tydligare fetch-fel.
- V1.1.0 - lade till sparr for for manga sena lan.
