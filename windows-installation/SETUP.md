# Windows Setup – V1.13.1

## Installera och starta

Kör `LoanInventory-1.13.1-Setup.exe` på Windows 10/11 x64. Python, Tkinter,
SQLite, openpyxl och pyscard följer med. Ingen separat Python-installation
eller administratörsbehörighet behövs. Kortläsare kan fortfarande behöva
tillverkarens drivrutin; hårdvara ingår inte i verifieringen.

Programmet installeras normalt i `%LOCALAPPDATA%\Programs\LoanInventory`.
Startmenyn får en genväg; skrivbordsgenväg är ett val i installationen.
Starta **Loan Inventory**, välj **Simulering** och tryck **Starta** för
fiktiva data och `admin/admin` eller `superadmin/superadmin`.
Ingen riktig databas eller något befintligt konto följer med installeraren.
Installeraren är osignerad: Windows/SmartScreen kan varna. Följ organisationens
regler; kringgå inte blockerad programinstallation.

## Egen databas och konton

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

**Öppna versionssidan i webbläsaren** öppnar enbart
<https://github.com/SamuelMeyer1/LoanSystem/releases>.
Repo är privat: logga in i webbläsaren med ett GitHub-konto som har åtkomst.
Knappen kontrollerar inte om en ny version finns och laddar inte ned eller
installerar något. Ingen GitHub-token finns i appen. Om ingen release har
publicerats finns ännu inget att hämta där.

1. Säkerhetskopiera enligt godkänd rutin. Ladda ned en ny Setup manuellt när
   en behörig projektägare har publicerat den.
2. Klicka **Stoppa** och stäng alla Loan Inventory-fönster och kontoverktyg.
   Setup och avinstallation vägrar fortsätta medan en paketerad process körs.
   De tvångsavslutar inte servern.
3. Kör Setup som samma Windows-användare, till samma programmapp.
4. Starta appen. Inställningar, databaser och loggar ligger kvar.

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
kontrollerar paketet och kompilerar `dist\installer\LoanInventory-1.13.1-Setup.exe`.
Det ändrar inte installerade Python-paket i utvecklingsmiljön.
Första bygget behöver nätåtkomst till PyPI; installeraren behöver inte nätet.
Inno Setup måste installeras separat; byggskriptet hämtar inga okända verktyg.
`app_version.py` är källa för version i EXE och Setup. Bygget avvisar avvikande
frontend-/versionslogg. Bumpa även dessa två synliga versionssträngar.

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
# Testpaket med egen AppId, utan genvägar eller avinstallationsregistrering:
.\windows-installation\Build-Setup.ps1 -Python "C:\sökväg\till\python.exe" -TestInstall
.\build\windows\venv\Scripts\python.exe -B windows-installation\smoke_bundle.py dist\LoanInventory --installer dist\installer\LoanInventory-1.13.1-TestSetup.exe
```

`-TestInstall` bygger separat `*-TestSetup.exe` med annan AppId, utan genvägar,
autostart eller Windows avinstallationsregistrering. Använd endast detta paket
för isolerade install-/uppgradering-/avinstallationstester under `build`.
Produktionspaketet ska däremot delas som `*-Setup.exe`.
Setup är inte kodsignerad; signering/certifikat och releasepublicering är
separata framtida åtgärder.
