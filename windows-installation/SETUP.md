# Windows Setup – V1.18.3

## Installera och starta

Kör `LoanInventory-1.18.3-Setup.exe` på Windows 10/11 x64. Python, Tkinter,
SQLite, openpyxl och pyscard följer med. Ingen separat Python-installation
eller administratörsbehörighet behövs. Kortläsare kan fortfarande behöva
tillverkarens drivrutin; hårdvara ingår inte i verifieringen.

Programmet installeras normalt i `%LOCALAPPDATA%\Programs\LoanInventory`.
Startmenyn får en genväg; skrivbordsgenväg är ett val i installationen.
Starta **Loan Inventory**, välj **Simulering** och tryck **Starta** för
fiktiva data och `admin/admin` eller `superadmin/superadmin`.
Simuleringen sparas i `%LOCALAPPDATA%\LoanInventoryLauncher\simulations\demo.db`.
Den innehåller 5 grupper, 15 låntagare, 20 pågående jobb och varierad historik.
Teständringar finns kvar vid omstart. Stoppa servern och välj
**Återställ demodata...** för en ny demo vid nästa start; den gamla arkiveras.
Vald riktig databas berörs inte, och gamla tillfälliga simuleringar importeras inte.
Ingen riktig databas eller något befintligt konto följer med installeraren.
Installeraren är osignerad: Windows/SmartScreen kan varna. Följ organisationens
regler; kringgå inte blockerad programinstallation.

Programmet har en egen blå lagerikon med enbart boxen i startfönstret,
programmet och Setup. Från V1.13.3 använder genvägarna en separat versionsmärkt
ICO-fil, så de inte återanvänder den gamla EXE-ikonreferensen i Windows.
Välj **Skapa en genväg på skrivbordet** när du uppdaterar till samma programmapp.
Installationen uppdaterar sin genväg, men inte manuellt skapade kopior.
Serverporten reserveras före databasstart men börjar lyssna först när starten
är klar. Startfönstret väntar upp till 60 sekunder och varje hälsokontroll får
5 sekunder. En avbruten svarsskrivning loggas kort utan nytt 500-svar.
En låneändring kan redan ha sparats när anslutningen bryts; kontrollera listan
innan du försöker samma åtgärd igen.

## Egen databas och konton

### Regler utan kodändring

Logga in som **Systemadmin** och öppna **System → Allmänt**. Där sparas
inaktivitetsvarning (på/av), antal dagar (1–36500, standard 365) och
Admin-klockans notistyper (ny förfrågan som standard, faktisk utlåning som tillval).
Inställningarna sparas i vald databas och bevaras vid uppdatering.
Den här sidan behöver inte SMTP-/Teams-inställningar eller testmottagare.

Inaktivitet märks vid namnet i användarlistan. Det är en manuell granskningssignal,
inte en automatisk spärr eller radering. Utgångspunkten är senaste utlåning,
annars registreringsdatum. Saknas datum görs ingen automatisk bedömning.
Kvarvarande lån, öppna jobb och olösta skador undantas. Senaste utlåningsdatum
bevaras i låntagarprofilen även när avslutad lånehistorik gallras.

Admin och Systemadmin ser klockan bredvid inloggningsstatus. Den visar de senaste
20 händelserna av valda typer, utan personuppgifter, och kontrollerar nya händelser
var 15:e sekund när sidan är synlig. En utlämning kan ge en notis per artikelrad.
Läsmarkering sparas separat per konto och notistyp. Knappen markerar visade och
äldre händelser av aktiverade typer; senare inkomna händelser förblir olästa.
Loggarnas vanliga gallringsregler gäller även denna historik.
Notiserna skickar aldrig e-post, Teams eller SMS.

### Databas och inloggning

**Ny databas...** föreslår `%LOCALAPPDATA%\LoanInventoryLauncher\data`.
Välj **Lokalt** och den filen. Databaser som väljs via **Bläddra...** används
på sin befintliga plats; de flyttas eller kopieras inte automatiskt.
Lägg aldrig data inne i programmappen. Använd inte en delad nätverksfil.
För egna administratörskonton, kör den medföljande konsolen från PowerShell:

```powershell
$env:LOAN_DATABASE_PATH = "$env:LOCALAPPDATA\LoanInventoryLauncher\data\inventory.db"
& "$env:LOCALAPPDATA\Programs\LoanInventory\LoanInventoryAdmin.exe" ditt-kontonamn --role superadmin
```

Lösenordet efterfrågas dolt (minst 15 tecken). Sätt rätt `LOAN_DATABASE_PATH`
om databasen har annat namn. Verktygets `--help` beskriver fler kontoåtgärder.
Startfönstret stänger av externa utskick. Simuleringen spärrar även fysisk
kortläsning. Programmet är fortfarande en lokal prototyp, inte en godkänd
företags-/GDPR-lösning; se `dataskydd.md` bredvid detta dokument i installerad app.

## Uppdatera och avinstallera

Startfönstret kontrollerar en gång vid varje start senaste stabila GitHub-release
i <https://github.com/SamuelMeyer1/loan-inventory-releases/releases>.
Kontrollen är asynkron, använder 10 sekunders nätverkstimeout och kräver ingen
GitHub-inloggning/token. Windows/systemets proxyinställningar används.
Från 1.18.2 verifieras HTTPS med Windows certifikatfunktioner via `truststore`
för just uppdateringsanropet. Det stöder systemets betrodda certifikat och
hämtning av saknade mellanliggande certifikat utan att stänga av verifiering.
Värdnamn och certifikatkedja kontrolleras fortfarande; appen installerar inga
rotcertifikat och ändrar inte SMTP eller andra anslutningar.
Om certifikatfel kvarstår: kontrollera datorns datum och godkända certifikat
med IT. Gå inte förbi säkerhetsvarningar. 1.18.0/1.18.1 med certifikatfel
behöver uppdateras manuellt via webbläsaren till 1.18.2 för att få denna rättning.
Ingen publicerad release, nätverksfel och API-begränsning visas i startfönstret;
servern kan startas ändå. **Sök uppdateringar** provar igen.

Versionsnummer jämförs numeriskt, inte alfabetiskt. Bara en uppladdad
`LoanInventory-<version>-Setup.exe` från rätt release erbjuds; aldrig TestSetup,
källkodsarkiv, utkast eller förhandsversioner. Efter godkännande öppnar
standardwebbläsaren filens nedladdningsadress. Appen kontrollerar metadata,
filnamn och adress, men verifierar inte den nedladdade filens hash eller signatur.
Ingen installationsfil körs automatiskt. **Versionssida** öppnar release-listan.
BAT-startens källkod ersätts inte av Setup; den installerade EXE-appen uppdateras.

1. Säkerhetskopiera enligt godkänd rutin. Ladda ned en ny Setup manuellt när
   en behörig projektägare har publicerat den.
2. Klicka **Stoppa** och stäng alla Loan Inventory-fönster och kontoverktyg.
   Setup och avinstallation vägrar fortsätta medan en paketerad process körs.
   De tvångsavslutar inte servern.
3. Kör Setup som samma Windows-användare, till samma programmapp.
4. Starta appen. Inställningar, databaser och loggar ligger kvar.

### Publicera en ny version

1. Bygg och testa produktionspaketet. Skapa en release i
   <https://github.com/SamuelMeyer1/loan-inventory-releases/releases/new>.
2. Använd taggen `v1.18.3` och titeln `Loan Inventory 1.18.3` för denna version.
   Tagg, versionsnummer i appen och filnamn måste stämma överens.
3. Beskriv ändringarna och bifoga endast `LoanInventory-1.18.3-Setup.exe`
   från `dist\installer`. Lägg inte med TestSetup, databaser, backuper,
   inställningar eller projektmappen. Granska paketets innehåll före publicering.
4. Publicera som stabil release och markera den som senaste release.
   Senare versioner följer samma mönster med nya versionsnummer.

Äldre installationer utan automatisk kontroll behöver först uppdateras manuellt.
Ett bygge publicerar aldrig något på GitHub. Vid automatiserade tester används
`LOAN_SKIP_UPDATE_CHECK=1` för att undvika nätverksanrop och uppdateringsdialoger;
det stänger inte av den manuella knappen.

Före varje paketerad start som migrerar en befintlig, icke-tom databas skapas
en konsekvent SQLite-backup i `backups` bredvid vald databas, med versionsnummer,
UTC-tid och unikt suffix. Detta gäller även kontoverktyget. Misslyckad backup
stoppar migrationen. En ny tom databas behöver ingen backup.
Backuper raderas inte automatiskt: övervaka diskutrymme och gallra enligt
godkänd rutin. Backuper innehåller samma personuppgifter/kontohashar som originalet.
Återställning görs manuellt till en separat fil med alla servrar stoppade;
välj filen i startfönstret. Äldre programversioner stöds inte på nyare schema.

Inställningar (`preferences.json`), loggar och simuleringar sparas under
`%LOCALAPPDATA%\LoanInventoryLauncher`, separat från programfilerna.
Avinstallation tar endast bort programfiler och genvägar; användardata och
backuper lämnas kvar, även efter ominstallation.
Den gamla källkodsbaserade offlineinstallationen migreras inte automatiskt.
Stoppa dess server och välj vid behov databasen från dess gamla plats.

## Bygg från källkod

Kräver Windows x64, Python 3.13 med Tk och Inno Setup 6 (officiell nedladdning:
<https://jrsoftware.org/isdl.php>). Kör från repo-roten:

```powershell
.\windows-installation\Build-Setup.ps1 -Python "C:\sökväg\till\python.exe"
# Vid annan Inno-installation: lägg till -ISCC "C:\sökväg\till\ISCC.exe"
```

Skriptet bygger en isolerad `build\windows\venv` från
`requirements-build.txt`, en PyInstaller **onedir** i `dist\LoanInventory`,
kontrollerar paketet och kompilerar `dist\installer\LoanInventory-1.18.3-Setup.exe`.
Det ändrar inte installerade Python-paket i utvecklingsmiljön.
Första bygget behöver nätåtkomst till PyPI; installeraren behöver inte nätet.
Inno Setup måste installeras separat; byggskriptet hämtar inga okända verktyg.
`app_version.py` är källa för version i EXE och Setup. Bygget avvisar avvikande
frontend-/versionslogg. Bumpa även dessa två synliga versionssträngar.
`app_icon.py` är gemensam källa för Tk-ikonen och den flerstorleks-ICO som
`prepare_build.py` genererar under `build\windows` för EXE och Setup.

`LoanInventory.spec` har en uttrycklig resurslista. Varken `data`, lokala
preferenser, konton, loggar, hela repo-roten eller `frontend/sample-images/real`
samlas in. Endast importerad appkod, listade statiska filer, dokument och
runtime-beroenden paketeras. Kontrollera alltid distributionen före delning.
Inget byggsteg publicerar, laddar upp eller ändrar GitHub.

Verifiering (endast genererade testdata under repo-roten):

```powershell
$env:TEMP = "$PWD\build\windows\scratch"
$env:TMP = $env:TEMP
.\build\windows\venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_*.py"
.\build\windows\venv\Scripts\python.exe -B windows-installation\smoke_bundle.py dist\LoanInventory
# Testpaket med egen AppId, isolerade genvägar och ingen avinstallationsregistrering:
.\windows-installation\Build-Setup.ps1 -Python "C:\sökväg\till\python.exe" -TestInstall
.\build\windows\venv\Scripts\python.exe -B windows-installation\smoke_bundle.py dist\LoanInventory --installer dist\installer\LoanInventory-1.18.3-TestSetup.exe
```

`-TestInstall` bygger separat `*-TestSetup.exe` med annan AppId, utan
autostart eller Windows avinstallationsregistrering. Testgenvägar skapas endast
under `test-shortcuts` i testets installationsmapp, aldrig på användarens skrivbord
eller i Startmenyn. Testet verifierar ikonreferenser vid installation och
ominstallation samt borttagning vid avinstallation. Använd endast detta paket
för isolerade install-/uppgradering-/avinstallationstester under `build`.
Produktionspaketet ska däremot delas som `*-Setup.exe`.
Setup är inte kodsignerad; signering/certifikat och releasepublicering är
separata framtida åtgärder.
