# Loan Inventory System

Lokal prototyp med Python-backend, SQLite och HTML/CSS/JavaScript-frontend.

Hårdvaruadaptrar och verktyg ligger i `hardware/` (RFID och Brother); externa
protokolltransporter ligger i `software/communications/` (SMTP och Teams).
Notifieringsregler, databaskoppling och användarbehörighet ligger kvar i backend.

Backend använder endast Python standardbibliotek:

- `http.server` för lokal HTTP-server
- `sqlite3` för databas
- `json` för API-svar

## Jobbkort och låntagarprofiler (V1.15.0)

Sök, språk och inloggning är samlade till höger. Objektets extra information
under Låna kan fällas ut med Visa mer; namn, kvarvarande antal och status visas direkt.
Låntagarprofiler skapas utan rollval och är inte inloggningskonton.
Vid redigering betyder **Tillåt utlåning till personen** manuell tillåtelse,
inte nylig aktivitet. Inaktivitetsvarningen styrs separat under System → Allmänt.

Jobbkort godkänns, förbereds och lämnas ut gemensamt. Ta bort oönskade artiklar
före utlämning. Äldre kort med blandade statusar kan stegvis komma ikapp utan att
redan avancerade artiklar flyttas tillbaka. Individuell framflyttning av en
artikel i ett flerartikeljobb avvisas även av API:t; äldre enartikelformat stöds.

**Återlämna – välj antal** öppnar ett formulär med antal och eventuell skada per
artikel. 0 betyder ingen retur av den artikeln. Även en enskild artikel kan
öppnas för delretur. Antal hämtas på nytt och dubbla/inaktuella returer avvisas.
Efter exempelvis 4 av 15 visar kortet 4 återlämnade och 11 kvar hos låntagaren.
Mobilikonen bredvid hämtningsmejlet är inaktiverad: SMS är en framtida funktion.

## Lånekorg och returförtydliganden (V1.15.1)

Skicka låneförfrågan använder korgradens antal för en redan tillagd artikel,
även om artikeln fortfarande är vald i sökfältet. Använd Lägg till artikel
eller ändra korgraden för att öka antalet. När alla tillgängliga exemplar
ligger i korgen visar det inaktiverade antalvalet Inga fler att lägga till.
Aktuellt lagersaldo kontrolleras fortfarande före sändning.

Skadebeskrivning visas och krävs bara när Varav skadade är större än 0,
både på återlämningssidan och i jobbkortets returformulär. Sätts antalet
skadade tillbaka till 0 rensas beskrivningen. Bekräftelsen visar antal
återlämnade och skadade utan ordet karantän; hanteringen av skadat lager
är oförändrad.

## Adminnotiser och avvikelser på jobb

Admin och Superadmin delar notisernas läsmarkering. Klockan blir orange och
pulserar lugnt vid olästa händelser (utan animation vid minskad rörelse).
När panelen öppnas hämtas senaste händelserna och läsmarkeras för båda rollerna.
Senaste 20 visas; läsmarkering raderar inte historiken eller ändrar jobbstatus.
Nya händelser efter den hämtade ögonblicksbilden förblir olästa. Andra öppna
klienter uppdateras vid nästa kontroll, normalt inom 15 sekunder.
Panelen stängs vid klick utanför, Escape och navigation. Gå till jobblistan
öppnar den vanliga jobbvyn med dess befintliga filter.

Varningstriangeln vid artikelantalet visar delreturer och ej åtgärdade skador.
Visa artiklar och Detaljer visar antal, skadebeskrivning och var skadan åtgärdas.
Lagerför allt är inaktiverad när kvarvarande lån eller olösta skador blockerar;
serverns spärr gäller även vid dragning eller samtidiga ändringar.
Grunddemons jobb #32 har avsiktligt en sådan skada. Att läsa en notis löser
inte skadan; använd Admin → Skador / karantän för reparation eller kassering.

## Windows-installationsprogram (V1.18.3)

`LoanInventory-1.18.3-Setup.exe` innehåller Python, Tk och nödvändiga bibliotek.
Installeras per användare, utan separat Python. Data och inställningar ligger
utanför programmappen och lämnas kvar vid uppgradering/avinstallation.
Paketerad app säkerhetskopierar befintlig databas före migration.
Startfönstret kontrollerar vid varje BAT-/EXE-start om en ny stabil version finns
i det publika [release-repot](https://github.com/SamuelMeyer1/loan-inventory-releases/releases).
Kontrollen körs i bakgrunden utan inloggning/token och hindrar inte serverstart
vid nätverksfel eller om ingen release publicerats ännu. På Windows använder
uppdateringskontrollen Windows certifikatverifiering via `truststore`, inklusive
kontroll av certifikatkedja och värdnamn. Inga certifikat installeras av appen.
Sök uppdateringar provar igen.
En ny version erbjuds först när rätt publicerade produktions-Setup finns.
Efter godkännande öppnas nedladdningen i standardwebbläsaren; inget installeras
automatiskt. Stoppa servern och stäng startfönstret före installation.
BAT-startens källkod uppdateras inte av Setup. Äldre versioner utan kontrollen
behöver uppdateras manuellt första gången.
Se [installation, data, konton och bygge](windows-installation/SETUP.md).
Det äldre offline-källkodspaketet är en separat installationsmetod.

## Återlämning och skador (V1.12.0)

Välj låntagare under **Lämna tillbaka**, markera artiklar och ange antal som
återlämnas. **Varav skadade** ingår i returantalet och kräver en beskrivning
(undvik personuppgifter). Sammanfattningen visar vad som återlämnats och vad
låntagaren har kvar. Delvis återlämnade lån fortsätter vara aktiva.

Skadade exemplar hålls i karantän och räknas inte som tillgängliga.
Under **Admin → Skador / karantän** bekräftar Admin antingen reparation
(återför till tillgängligt lager) eller kassering (minskar totalt antal).
Åtgärden gäller hela skadeposten och kan bara utföras en gång.
Ett jobb kan inte lagerföras innan alla exemplar återlämnats och skador åtgärdats.
Kategorisering av skador ingår inte.

API: `POST /api/return` tar `user_id` och `items` med `loan_id`, `quantity`,
`damaged_quantity`, `damage_description` och `expected_returned_quantity`
(senast lästa kumulativa returantal). Det sista fältet avvisar dubbla/stale
delreturer; hämta om lånen före en ny retur. Äldre `loan_ids`/`identifier`
stöds och återlämnar återstående antal. Admin använder
`GET /api/damaged-returns` och `POST /api/damaged-returns/resolve`
med `return_id`, `resolution` (`repaired`/`discarded`) och `confirmed: true`.
Migrationen bevarar befintliga lån och saldon, och skapar returhistorik för
avslutade lån. Ta backup före uppgradering.

## Startfönster och simulering

Dubbelklicka på `Starta.bat` eller kör `python -B launcher.py`.
Startfönstret behöver Tkinter (ingår i normal Python-installation för Windows).
På Linux kan operativsystemets Tkinter-paket behöva installeras.

- **Lokalt:** välj en befintlig SQLite-fil eller skapa en ny tom databas.
  Det befintliga schemat migreras som vid vanlig serverstart; ta backup först.
- **Nätverk:** välj databas, datorns privata IPv4-adress och port.
  Samma LAN-begränsningar och krav på tillåten nätverksåtkomst gäller som tidigare.
  På en annan dator öppnar man serverns adress direkt i webbläsaren.
  Dela inte en SQLite-fil direkt via en nätverksmapp.
- **Simulering:** första starten bygger en separat, sparad demonstrationsdatabas.
  Därefter finns dina teständringar kvar mellan starter. Endast loopback används. `admin/admin` och
  `superadmin/superadmin` finns i denna testdatabas.

Simuleringens databas sparas under
`%LOCALAPPDATA%\LoanInventoryLauncher\simulations\demo.db` på Windows.
Den valda riktiga databasen används inte. Äldre `simulation-*.db` importeras
eller raderas inte automatiskt. Den nya demodatabasen är märkt och kan bara
startas i Simulering, inte i Lokalt/Nätverk.
Externa utskick är avstängda vid all serverstart via startfönstret;
i simuleringen är även fysisk kortläsning och aktivering av utskick spärrade.
Det gamla alternativet för notifieringssimulering i System är inte samma sak:
det kan annars skicka till en testmottagare.

Demonstrationen innehåller 5 grupper, 15 påhittade interna/externa låntagare och
de befintliga 8 demoartiklarna. Det finns 20 pågående jobb (24 lånerader),
7 återlämnade jobb, 5 förfrågningar, 3 godkända, 3 redo att hämta och
31 äldre lagerförda jobb. Historiken fyller statistik över flera månader.
Loctite är förbrukningsvara med en öppen rapport om slut i lager.

Exempel att prova: Demo Erik Holm är spärrad av sena lån, Demo Emil Strand har
manuell tillåtelse trots sena lån, Demo Ida Hed är manuellt avstängd och
Demo Axel Vik/Demo Ella Fors har inaktivitetsvarningar. Admin kan se och
redigera avstängda låntagare; dessa visas inte i förslagen vid nya lån.
Delreturer, öppna skador, reparation och kassering finns med, med konsekventa
lagerantal. E-postadresser slutar på `example.invalid`, telefonnummer är tomma.

För en ny demonstration: stoppa servern, välj Simulering och klicka
**Återställ demodata...**. Efter bekräftelse sparas gamla teständringar i
`demo.before-reset-*.db`; nästa Starta skapar demon på nytt med datum relativt
dagens datum. Vanlig omstart flyttar inte datum och fyller inte tillbaka
borttagna poster. Återställning/ytterligare start av samma demo blockeras
medan den används. Arkiv och uppgraderingsbackuper raderas inte automatiskt.

Startfönstret visar aktiv databas, URL och loggfil i den skrivskyddade loggpanelen
längst ner. Det öppnar webbläsaren först när den egna servern svarar.
**Stoppa** och stängning av startfönstret
stoppar endast den process som fönstret självt startade.
Senaste inställningarna sparas lokalt, utan lösenord.

Statusraden mäter svarstid för `/api/runtime` ungefär var tredje sekund även
efter start, och visar om servern slutar svara. Detta är HTTP-tur och retur från
startfönstret, inte CPU-belastning eller ett prestandatest av hela databasen.
Serverloggen visar HTTP-metod, statuskod och behandlingstid i millisekunder;
frågeparametrar, anropsadresser, IP-adresser, cookies och formulärdata ingår inte
i dessa HTTP-loggrader. Startfönstret aktiverar detta via
`LOAN_SERVER_DIAGNOSTICS=1`; vanlig `python main.py` är fortsatt tyst utan flaggan.
Panelen visar högst 1 000 rader/100 000 tecken, medan loggfilen behåller hela
körningens logg. Man kan markera/kopiera loggtext, men inte köra kommandon.

`python main.py` fungerar fortfarande som tidigare, med miljövariabler;
`python main.py --port 8001` väljer en annan port. Startfönstrets val gäller endast
dess barnprocess och ändrar inte variabler i andra PowerShell-fönster.

## Dataskydd och inloggning

Prototypen har nu lokala inloggningskonton och serverkontrollerade behörigheter.
Den är avsedd för lokal utveckling med fiktiva uppgifter; tekniskt stöd är inte
en garanti om GDPR-efterlevnad eller ett godkännande för företagsdrift. Ett
uttryckligt LAN-testläge finns för tillfälliga tester med fiktiva uppgifter; det
är inte en godkänd lösning för delad företagsdrift.

Första gången: säkerhetskopiera enligt godkänd rutin och skapa ett konto från
projektroten. Lösenordet anges dolt i terminalen, minst 15 tecken:

```powershell
python -B -m backend.manage_access ditt-kontonamn --role superadmin
```

För en lokal, tillfällig testkörning kan två låsta testkonton aktiveras separat.
Lösenorden anges i PowerShell-miljön och lagras endast som hash:

```powershell
$env:LOAN_LOCAL_FIXED_TEST_CREDENTIALS = "1"
$env:LOAN_LOCAL_ADMIN_PASSWORD = "admin"
$env:LOAN_LOCAL_SUPERADMIN_PASSWORD = "superadmin"
python main.py
```

Användarnamnen är `admin` respektive `superadmin`. Kontona kan inte ändras eller
raderas med kontoverktyget. Funktionen är endast för loopback: servern vägrar
starta i LAN-läge med flaggan aktiv eller om databasen innehåller markerade
testkonton. Ta bort flaggan och använd en separat testdatabas för LAN-test.
Lösenorden är avsiktligt svaga och får aldrig användas på en delad eller
produktionsserver.

Läs [dataskydd och drift](docs/dataskydd.md) för operatörskonton, registerunderlag,
gallring, radering och kvarstående beslut. **Dataskydd / Privacy** i appen visar
behandlingsinformation och ger superadmin förhandsgranskning av åtgärder.
Inga konton eller gallringstider läggs in automatiskt. Externa notiser är spärrade
som standard.

När Admin skapar en ny låntagarprofil ska personen först få se informationen om
hur uppgifterna används och bekräfta att den tagit del av den. Appen sparar
tidpunkten för bekräftelsen. Det är en kvittens på lämnad information, inte ett
juridiskt GDPR-samtycke eller en bedömning av rättslig grund.

## Starta

```powershell
cd "c:\Users\a524708\Desktop\Programmerings projekt\WORKSPACE\loan_inventory_system"
python main.py
```

Öppna sedan:

```text
http://127.0.0.1:8000
```

### Tillfälligt LAN-test med kollegor

Använd bara fiktiva testuppgifter och en separat testdatabas. På värddatorn kör
`ipconfig` och välj IPv4-adressen för företagets Ethernet/Wi-Fi. I PowerShell,
från projektroten, sätt miljövariablerna till den egna testdatabasen och IP:n:

```powershell
$env:LOAN_DATABASE_PATH = "$env:TEMP\loan-inventory-lan-test.db"
$env:LOAN_ALLOW_LAN = "1"
$env:LOAN_HOST = "192.168.1.25"
python main.py
```

Byt `192.168.1.25` mot din privata IPv4-adress. Kollegor på samma godkända
företagsnät öppnar `http://192.168.1.25:8000` direkt. LAN-besökare får en gemensam
operatörsvy utan inloggning, inklusive operatörernas låntagaruppgifter och
operatörsåtgärder. Admin eller Superadmin loggar in via knappen **Admin logga in**;
skapa först kontot i testdatabasen med `python -B -m backend.manage_access testadmin --role superadmin`.
Om Windows-brandväggen blockerar
anslutningen, be IT godkänna inkommande TCP-port 8000 för rätt privat
nätverksprofil; stäng inte av brandväggen och exponera inte porten via routern.
Variablerna gäller bara det PowerShell-fönstret. Utan `LOAN_ALLOW_LAN=1` startar
servern fortfarande endast lokalt, och LAN-läge vägrar wildcard-/publika adresser.

Operatörsvyn visar låntagaruppgifter utan individuell inloggning och tillåter
operatörsåtgärder åt alla låntagare. Alla på nätverket delar den åtkomsten.
Testläget använder okrypterad HTTP. Begränsa det till en kort, godkänd testperiod
med fiktiva uppgifter. Använd inte produktionsdatabasen eller riktiga personuppgifter.

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

I LAN-testläget används en delad, anonym operatörsidentitet som kan se alla
låntagaruppgifter och utföra operatörsåtgärder för alla. Detta är endast för
fiktiva testdata. Se `python -B -m backend.manage_access --help` och
[dataskyddsrutinen](docs/dataskydd.md).

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
