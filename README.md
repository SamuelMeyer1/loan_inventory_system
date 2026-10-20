# Loan Inventory System

Lokal prototyp med Python-backend, SQLite och HTML/CSS/JavaScript-frontend.

Backend använder endast Python standardbibliotek:

- `http.server` för lokal HTTP-server
- `sqlite3` för databas
- `json` för API-svar

## Dataskydd och inloggning (V1.6.0)

Prototypen har nu lokala inloggningskonton och serverkontrollerade behörigheter.
Den är avsedd för lokal utveckling med fiktiva uppgifter; tekniskt stöd är inte
en garanti om GDPR-efterlevnad eller ett godkännande för företagsdrift.

Första gången: säkerhetskopiera enligt godkänd rutin och skapa ett konto från
projektroten. Lösenordet anges dolt i terminalen, minst 15 tecken:

```powershell
python -B -m backend.manage_access ditt-kontonamn --role superadmin
```

Läs [dataskydd och drift](docs/dataskydd.md) för operatörskonton, registerunderlag,
gallring, radering och kvarstående beslut. **Dataskydd / Privacy** i appen visar
behandlingsinformation och ger superadmin förhandsgranskning av åtgärder.
Inga konton eller gallringstider läggs in automatiskt. Externa notiser är spärrade
som standard. Nätverksbindning stöds inte av denna lokala prototyp.

## Starta

```powershell
cd "c:\Users\a524708\Desktop\Programmerings projekt\WORKSPACE\loan_inventory_system"
python main.py
```

Öppna sedan:

```text
http://127.0.0.1:8000
```

Databasen skapas automatiskt som:

```text
data/inventory.db
```

## Bilder

Rekommenderad bildstorlek:

- 600 x 600 px för kvadratiska objektbilder
- 800 x 600 px för liggande objektbilder
- JPG, PNG, WebP eller SVG
- under 700 KB per bild i den här prototypen

Bilder sparas lokalt i SQLite. För större produktion är det bättre att spara bildfiler på disk och bara lagra filvägen i databasen.

Det finns 10 neutrala exempelbilder i:

```text
frontend/sample-images/
```

Det finns även 10 riktiga produktbilder för prototyp/test i:

```text
frontend/sample-images/real/
```

Du kan lägga in dem via **Admin** genom att redigera eller skapa ett objekt och välja en bildfil.

## API

- `GET /api/stats`
- `GET /api/objects`
- `GET /api/users`
- `GET /api/loans`
- `GET /api/events`
- `POST /api/checkout`
- `POST /api/issue`
- `POST /api/return`
- `POST /api/objects`
- `PUT /api/objects`
- `DELETE /api/objects?object_id=...`

## Import från MaintMaster/Excel

Excel-exporten kan importeras med:

```powershell
python scripts/import_articles_excel.py "c:\Users\a524708\Downloads\Alla artiklar och reservdelar.xlsx" --apply
```

Kör utan `--apply` för en torrkörning som bara visar antal rader och exempel:

```powershell
python scripts/import_articles_excel.py "c:\Users\a524708\Downloads\Alla artiklar och reservdelar.xlsx"
```

Importen skapar backup i `data/`, sparar alla originalkolumner i `old_inventory_import` och fyller `objects` med MaintMaster-fälten som appen använder.

## Roller i prototypen

Rollväljaren visar det inloggade kontots roll och kan inte ändras. Servern
kontrollerar varje API-anrop. Profilens rollfält skapar inte ett inloggningskonto.

- **Operatör:** egna uppgifter/lån, låneförfrågningar, hämtning av egna förberedda
  lån, återlämning av egna valda lån och rapportering av slut på förbrukningsvara.
- **Admin:** lager, användare och lånehantering.
- **Superadmin:** dessutom fullständiga systeminställningar, loggar och dataskydd.

Se `python -B -m backend.manage_access --help` och [dataskyddsrutinen](docs/dataskydd.md).

## Struktur

```text
loan_inventory_system/
  main.py
  backend/
    database.py
    server.py
    seed_data.py
    services/
      __init__.py
      common.py
      inventory.py
      loans.py
      notifications.py
      stats.py
      users.py
  frontend/
    index.html
    styles.css
    js/
      app.js
      actions.js
      api.js
      charts.js
      i18n.js
      loan-views.js
      search.js
      translations.js
      ui-utils.js
    sample-images/
  scripts/
  hardware/
  data/
```
