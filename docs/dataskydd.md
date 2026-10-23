# Dataskydd i den lokala prototypen

Uppdaterad 2026-10-22. Detta dokument beskriver tekniskt stöd och kvarstående
verksamhetsbeslut. Det är ingen certifiering eller juridisk bedömning av GDPR-efterlevnad.

## Start och behörigheter

Appen fungerar nu som en lokal prototyp på samma dator. På loopback visas
operatörsvyn utan inloggning; Admin och Superadmin kräver fortfarande konto.
Den anonyma lokala operatören kan hantera och se låntagaruppgifter, så använd
endast fiktiva uppgifter och exponera inte servern på nätverket. Kör kommandona
från projektroten. Säkerhetskopiera databasen enligt företagets godkända rutin
innan migrering. Första kontot skapas manuellt, utan standardlösenord:

```powershell
python -B -m backend.manage_access ditt-kontonamn --role superadmin
python -B main.py
```

Lösenord anges dolt i terminalen, minst 15 tecken, och lagras som saltad scrypt-hash.
Ingen användare eller inloggning har skapats i den befintliga databasen under denna
utveckling. Databasmigreringen sker först när verktyget eller appen körs mot den.
Inga befintliga personuppgifter raderas av migreringen.

Skapa först en fiktiv låntagare i Admin. Koppla ett separat operatörskonto till
det returnerade låntagar-ID:t:

```powershell
python -B -m backend.manage_access testoperator --role operator --user-id LANTAGAR-ID
```

Byt lösenord/roll genom att köra samma kontokommando igen. Befintliga sessioner
återkallas då vid nästa anrop. Ta bort en inloggning med `--delete`; det raderar
inte låntagaren eller dennes lån. Använd personliga konton och begränsa antalet
administratörer. Konto-rollen styr servern; det gamla profilfältet `users.role`
ger ingen inloggning eller utökad behörighet.

| Konto | Tillgång |
| --- | --- |
| Operatör | Inventarier, egen profil, egna lån och förfrågningar; begära lån, hämta egna förberedda lån, lämna tillbaka egna valda lån, rapportera slut på förbrukningsvara. |
| Admin | Lager, låntagaradministration och lånehantering. Ingen tillgång till fullständiga systeminställningar, loggar eller registerutdrag/radering. |
| Superadmin | Administration samt systeminställningar, loggar och dataskyddsverktyg. |

Rollväljaren är låst. Att ändra HTML eller skicka en annan roll i ett API-anrop
ger ingen utökad behörighet. Kortläsning kan hjälpa personal att välja låntagare;
den ersätter inte autentisering. Operatörernas kortväljare är dold.

Sessioner har en fast livslängd om 30 minuter, finns bara i serverns minne och
återkallas vid omstart. Cookies är HttpOnly och SameSite=Strict. Ändringsanrop
kräver sessionsbundet CSRF-skydd och ett särskilt klienthuvud. Inloggningsförsök
begränsas till fem per minut och källadress; på en gemensam dator kan detta
tillfälligt hindra även legitima inloggningar.

För isolerad lokal UI-testning finns valfria, fasta konton (`admin` och
`superadmin`) som aktiveras med `LOAN_LOCAL_FIXED_TEST_CREDENTIALS=1` och
lösenordsvariablerna `LOAN_LOCAL_ADMIN_PASSWORD` respektive
`LOAN_LOCAL_SUPERADMIN_PASSWORD`. De lagras som scrypt-hash och låses mot
ändring/borttagning via kontoverktyget. Appen vägrar LAN-start när flaggan är
aktiv eller databasen innehåller dessa markerade konton. Använd bara på
loopback med en lokal testdatabas; svaga testlösenord får inte användas i
LAN-/produktionsmiljö.

## Personuppgifter och rättighetsärenden

### Isolerad testmiljö

Startfönstret (`python -B launcher.py`) har ett separat simuleringsläge. Varje
start skapar en ny databas med fejkdata och lokala testkonton; befintliga filer
kopieras eller ersätts inte. Simuleringen binds bara till loopback och spärrar
externa transporter och fysisk kortläsning även om inställningar ändras i appen.
Det skiljer sig från notifieringssimuleringen, som annars kan skicka till en
testmottagare. Testfilerna sparas lokalt och raderas inte automatiskt.

Startfönstrets vanliga lokala-/LAN-lägen använder vald databas och kan migrera
dess schema. Externa utskick är avstängda vid start via detta fönster. En
tidigare simuleringsfil som öppnas i vanligt lokalt läge är inte längre i
det särskilt spärrade simuleringsläget. Använd aldrig verkliga personuppgifter
i simuleringsfilerna.

Startfönstrets HTTP-diagnostik loggar endast metod, statuskod och behandlingstid,
inte begärans URL, parametrar, cookies eller formulärdata. Start-/felutskrifter
kan även innehålla lokala filsökvägar. Loggarna sparas lokalt per körning i
`LoanInventoryLauncher` under användarens datakatalog och raderas inte automatiskt.

### Information till låntagare

Namn och mejl krävs i nuvarande låntagarformulär. Verksamheten måste bedöma om
mejl och uppdelning i för-/efternamn behövs för dess valda arbetsflöde. Telefon
och företag är nu frivilliga. Fyll inte i frivilliga fält utan ett motiverat behov.
Avdelning/grupp, kortkod, alias, lånetider och projektreferenser kan också vara
personuppgifter. Nya låntagar-ID:n är slumpmässiga; befintliga ID:n ändras inte.

Öppna **Dataskydd / Privacy**. Läsbar behandlingsinformation finns även före
inloggning. Superadmin fyller i personuppgiftsansvarig, kontakt, ändamål, rättslig
grund och beslutade gallringstider. Beskriv även mottagare, integrationer,
eventuella överföringar och hur användarprofiler hanteras i textfälten.
Tom konfiguration är tydligt markerad och innebär att endast testdata ska användas.
Att fylla i fälten ersätter inte företagets rättsliga bedömning.
För frågor om personuppgifter är kontaktpersonen Olof Samuelsson:
[olof.samuelsson@volvo.com](mailto:olof.samuelsson@volvo.com).

Vid ny låntagarprofil ska Admin visa behandlingsinformationen för personen och
registrera att personen bekräftar att den tagit del av den. Tidpunkten sparas på
profilen och ingår i registerunderlaget; äldre profiler får ingen bakdaterad
bekräftelse. Detta är endast en kvittens på lämnad information, inte ett
GDPR-samtycke eller en rättslig grund. Verksamheten ansvarar för att välja och
dokumentera lämplig rättslig grund. Profilredigering kräver inte en ny kvittens.

**Registerunderlag:** Ange låntagar-ID och visa underlaget. Det omfattar profil,
lån, förfrågningar, kopplade kontons metadata, strukturerad säkerhetslogg och
sökbara träffar i äldre loggtext. Lösenordshashar och SMTP-hemligheter ingår inte.
Verifiera identiteten och granska underlaget före utlämnande. Äldre loggträffar
kan innehålla andra personers uppgifter. Detta är underlag för ett registerutdrag,
inte en automatiskt komplett juridisk svarshandling.

**Rättelse:** Ändra aktuella profiluppgifter i Admin efter kontroll av begäran.
Äldre fri text, importer och externa kopior kan behöva rättas separat.

**Radering:** Börja med förhandsgranskning. Aktiva lån eller förfrågningar som
inte lagerförts blockerar radering. En behörig handläggare bedömer rättigheten,
eventuella bevarandekrav och avslutar kvarstående förpliktelser. Skriv därefter
DELETE för att uttryckligen verkställa. Profil, lån, förfrågningar och kopplade
inloggningskonton raderas i en transaktion. Säkerhetsloggens koppling till
personen tas bort. Matchande äldre loggtexter maskeras i sin helhet; det kan
även ta bort text om andra personer. Profilinaktivering i Admin är fortfarande
bara inaktivering, inte radering.

Radering är begränsad till dessa strukturer i den aktuella databasen. Äldre
namn/mejladresser, fritextfält, `old_inventory_import`, objektbeskrivningar,
rapporter, kopior, exporter, mejl och Git-historik kan inte säkert kopplas till
en person automatiskt. Granska dem separat. Funktionen får inte beskrivas som
att den garanterar att alla historiska personuppgifter är borta. SQLite
`secure_delete` används vid radering/gallring, men ersätter inte hantering av
backup, diskavbildningar, filsystem eller eventuell WAL/journal.

## Gallring, loggar och externa tjänster

Ingen gallring körs vid start. Verksamheten bestämmer tidsfristerna; det finns
inga påhittade standardtider. Förhandsgranska och kör därefter gallring manuellt
på dataskyddssidan. Den omfattar gamla återlämnade lån, lagerförda förfrågningar
och gamla händelse-/säkerhetsloggar enligt policyn. Aktiva lån och ofärdiga
förfrågningsgrupper bevaras. Användarprofiler gallras genom den separata
raderingsrutinen. Utse ansvarig och intervall för den manuella gallringen.

Nya vanliga händelseloggar behåller tid och händelsetyp men ersätter fritexten
med en neutral text via databas-trigger. Detta minskar detaljerna vid felsökning.
Säkerhetsloggen registrerar konto, eventuell profilkoppling, fast API-åtgärd och
HTTP-status. Den lagrar inte lösenord, sessionsnycklar, IP-adress, query eller
request-body. Misslyckad inloggning registreras som overifierad identitet.
Gamla loggar skrivs inte om vid migrering. HTTP-anrop skrivs inte ut i terminalen.

Mejl och Teams är spärrade vid transportgränsen om inte driftmiljön uttryckligen
har `LOAN_ENABLE_NOTIFICATIONS=1`. Simuleringsläge är inte en säkerhetsgräns:
det kan sända personuppgifter till en testmottagare när transporten aktiveras.
Kontrollera därför mottagare, nödvändiga meddelandefält och företagets godkännande
innan aktivering. TLS med certifikatkontroll krävs; den gamla råa Teams-relävägen
har ersatts med SMTP STARTTLS och kan behöva annan godkänd konfiguration.
Mejlinnehåll och SMTP-kommandon skrivs inte längre ut i terminalen.

`LOAN_SMTP_PASSWORD` kan tillföras av driftmiljön i stället för att lagras i
SQLite. Ett miljötillfört lösenord skrivs inte tillbaka vid inställningsändringar.
Äldre databaslagrade SMTP-lösenord migreras eller raderas inte automatiskt;
IT behöver flytta/rotera dem och hantera gamla kopior. Nuvarande formulär kan
fortfarande spara ett lokalt SMTP-lösenord i databasen när miljövariabel saknas.
Skydda därför databas och backuper även som hemlighetsbärande filer.

Chart.js 4.5.1 finns lokalt i `frontend/vendor/` med MIT-licens. SHA-256 för
`chart.umd.js`: `ecc3cd1eeb8c34d2178e3f59fd63ec5a3d84358c11730af0b9958dc886d7652a`.
Appen laddar inte längre diagramkod från extern CDN. CSP begränsar skript och
nätanrop till samma ursprung. Detta är versionslåsning, inte en fullständig
sårbarhetsrevision; bibliotek och Python behöver en beslutad uppdateringsrutin.

## Innan riktiga uppgifter eller delad drift

Företaget behöver besluta och dokumentera ändamål, rättslig grund, minsta
datamängd, behandlingsinformation, mottagare, gallring, rättighetsärenden och
incidentrutin. Bedöm behov av konsekvensbedömning utifrån den faktiska risken.
Utse systemägare, behörighetsansvarig och ansvarig för uppdateringar/återställning.

Normal start är begränsad till loopback. Ett uttryckligt LAN-testläge kan bindas
till en enda privat IPv4-adress med `LOAN_ALLOW_LAN=1` och `LOAN_HOST`; servern
avvisar wildcard- och publika adresser och kontrollerar värdhuvudet mot den
konfigurerade adressen. LAN-testläget ger alla besökare en gemensam anonym
operatörsidentitet. Den kan läsa samtliga låntagarprofiler, lån och förfrågningar
som operatörsvyn exponerar samt utföra operatörsåtgärder för valfri låntagare.
Detta är avsiktligt bredare än personliga operatörskonton och medför att vem som
helst på det tillåtna nätverket delar denna åtkomst. Använd läget endast
tillfälligt, på ett godkänt privat nätverk och med en separat databas och
fiktiva uppgifter. Öppna inte porten mot internet eller via router.
Brandväggsregler ska godkännas av IT och begränsas till rätt nätverksprofil.
Admin/Superadmin loggar fortfarande in separat.

LAN-testläget använder okrypterad HTTP och cookies utan `Secure`; uppgifter och
sessionstrafik krypteras alltså inte på nätverket. Det är inte godkänt för
riktiga personuppgifter eller normal delad drift. Innan flera personer använder
systemet med riktiga uppgifter krävs en IT-godkänd HTTPS-lösning,
företagsinloggning, eventuell MFA och driftplattform. Python `http.server` är
inte en färdig produktionsplattform. LAN-testläget ersätter inte dessa krav.

SQLite är inte krypterad av appen. IT behöver bedöma filbehörigheter, diskkryptering,
lokal datoråtkomst, backupkryptering och retention, testad återställning samt hur
raderingar återtillämpas vid återställning av äldre backup. Den som kan läsa eller
ändra databasfilen kan kringgå appens åtkomstskydd.

Repo hade redan spårade databas-/backupfiler vid granskningen. Befintlig Git-index
och historik har inte ändrats. Publicera inte repot innan ansvariga har granskat
detta, tagit bort driftdata ur framtida källkodsversioner med lokala filer bevarade
och bedömt historik, tidigare spridning och eventuella exponerade hemligheter.
`.gitignore` tar inte bort redan spårade filer.

## Verifiering

Automatiska tester använder tillfälliga databaser och fiktiva uppgifter. Inga
live-data eller notifieringsmottagare ska användas i test.

```powershell
python -B -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q backend main.py
node tests/test_loan_cart.cjs
node tests/test_privacy_ui.cjs
node --check frontend/js/session.js
node --check frontend/js/privacy.js
```

För en isolerad manuell provkörning kan `LOAN_DATABASE_PATH` sättas till en ny
testdatabas utanför `data/`. Båda kontoverktyget och appen måste använda samma
värde. Befintlig data kopieras inte. Demodata kräver det uttryckliga valet
`LOAN_SEED_DEMO=1`; ingen automatisk seed körs annars.

UI-kontroll kvarstår: inloggning/felmeddelande, respektive roll, egen utlåning och
återlämning, logga ut, svensk/engelsk text, statistikdiagram och dataskyddssidans
förhandsgranskning/bekräftelse. Browser Use kunde inte nå den isolerade lokala
testservern i denna session; ingen godkänd visuell granskning påstås.

Verifierat 2026-10-15: 40 Python-tester godkända, inklusive riktiga lokala
HTTP-anrop med autentisering, negativ behörighetskontroll, aktiva låns skydd,
radering, gallring, äldre schema och upprepade migreringar. Båda Node-sviterna
för lånekorg/återlämning och dataskyddsbekräftelser godkända. JavaScript-syntax
och Python-kompilering godkända. Node använder simulerad DOM och ersätter inte
webbläsargranskning. Befintlig `data/inventory.db` har inte ändrats av arbetet.

## Källor

- [IMY: Inbyggt dataskydd och dataskydd som standard](https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/inbyggt-dataskydd-och-dataskydd-som-standard/)
- [IMY: De registrerades rättigheter](https://www.imy.se/verksamhet/dataskydd/det-har-galler-enligt-gdpr/de-registrerades-rattigheter/)
- [OWASP: Session Management](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)
- [OWASP: CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
## Återlämningar och skadebeskrivningar

Delreturer sparas med antal, tidpunkt och eventuell skadebeskrivning. Skriv endast
saklig information om artikeln, inte namn eller andra personuppgifter, i skadefältet.
Skadekön är endast tillgänglig för Admin/Systemadmin. Registerutdrag omfattar
retur- och skadeposter. Radering blockeras medan skador är i karantän; gallring
väntar dessutom tills beslutad lånehistoriktid passerat efter skadeåtgärden.
Vid tillåten radering av lånet tas dess retur- och skadebeskrivningar också bort,
utan att redan bokförda lagersaldon ändras.
