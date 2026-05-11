# Loan Inventory System

Lokal prototyp med Python-backend, SQLite och HTML/CSS/JavaScript-frontend.

Backend använder endast Python standardbibliotek:

- `http.server` för lokal HTTP-server
- `sqlite3` för databas
- `json` för API-svar

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

Rollväljaren i toppbaren simulerar framtida login:

- **Operatör** är standard och fokuserar på att låna, lämna tillbaka och checka ut förbrukningsartiklar.
- **Admin** kan skapa, redigera och ta bort objekt samt se admin/logg-vyer.
- **SuperAdmin** har Admins vyer plus System-vyn för Modbus/PLC, SMTP och generella notifikationer.

## Struktur

```text
loan_inventory_system/
  main.py
  backend/
    database.py
    services.py
    server.py
    seed_data.py
  frontend/
    index.html
    styles.css
    app.js
```
