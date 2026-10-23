LOAN INVENTORY SYSTEM - WINDOWS 10
==================================

NYTT SETUP.EXE (V1.13.0)
Se SETUP.md for den nya per-user-installeraren med paketerad Python.
Bygg med Build-Setup.ps1. Den inkluderar aldrig befintliga databaser.
Instruktionerna nedan galler ENDAST det aldre offline-kallkodspaketet.

PA DEN GAMLA DATORN
1. Hogerklicka pa Skapa-installationspaket.ps1 och valj "Kor med PowerShell".
2. Svara J om den aktuella databasen och alla uppgifter ska folja med.
3. Kopiera hela mappen LoanInventorySystem-Windows10 till USB-minne eller natverksdisk.

PA DEN NYA DATORN
1. Kopiera hela mappen till datorn.
2. Dubbelklicka pa Installera.bat.
3. Efter installationen finns en genvag pa skrivbordet.
4. Genvagen oppnar startfonstret: valj Lokalt, Natverk
   eller Simulering med fejkdata. Serverlogg och svarstid visas i fonstret.
   Stang fonstret for att stoppa
   servern som det startade. Se app\README.md for detaljer.

Ingen internetanslutning behovs. Paketet innehaller Python 3.12 och alla
bibliotek. De installeras i en egen isolerad miljo. Appen installeras under din
anvandarmapp i AppData\Local\LoanInventorySystem.

VIKTIGT
- Administratorer behover konto. Simuleringen har separata lokala testkonton.
  Se app\README.md och app\docs\dataskydd.md.
- Efter installation: oppna PowerShell i installationsmappen och kor
  .\.venv\Scripts\python.exe -B -m backend.manage_access ditt-kontonamn --role superadmin
- Databaspaket innehaller aven kontohashar och kan innehalla personuppgifter/hemligheter.
  Flytta dem endast enligt foretagets godkanda rutin. Endast simuleringen
  skapar testkonton automatiskt i en ny separat databas.
- Radera inte den gamla datorns data innan du har kontrollerat den nya.
- Vid ominstallation bevaras databasen som redan finns pa den nya datorn.
- Smartcard-lasaren kan ocksa krava sin vanliga Windows-drivrutin.
- Paketet ar gjort for 64-bitars Windows 10.
