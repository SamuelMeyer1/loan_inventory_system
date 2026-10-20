LOAN INVENTORY SYSTEM - WINDOWS 10
==================================

PA DEN GAMLA DATORN
1. Hogerklicka pa Skapa-installationspaket.ps1 och valj "Kor med PowerShell".
2. Svara J om den aktuella databasen och alla uppgifter ska folja med.
3. Kopiera hela mappen LoanInventorySystem-Windows10 till USB-minne eller natverksdisk.

PA DEN NYA DATORN
1. Kopiera hela mappen till datorn.
2. Dubbelklicka pa Installera.bat.
3. Efter installationen finns en genvag pa skrivbordet.

Ingen internetanslutning behovs. Paketet innehaller Python 3.12 och alla
bibliotek. De installeras i en egen isolerad miljo. Appen installeras under din
anvandarmapp i AppData\Local\LoanInventorySystem.

VIKTIGT
- V1.6.0 kraver ett lokalt inloggningskonto. Se app\README.md och app\docs\dataskydd.md.
- Efter installation: oppna PowerShell i installationsmappen och kor
  .\.venv\Scripts\python.exe -B -m backend.manage_access ditt-kontonamn --role superadmin
- Databaspaket innehaller aven kontohashar och kan innehalla personuppgifter/hemligheter.
  Flytta dem endast enligt foretagets godkanda rutin. Inga konton skapas automatiskt.
- Radera inte den gamla datorns data innan du har kontrollerat den nya.
- Vid ominstallation bevaras databasen som redan finns pa den nya datorn.
- Smartcard-lasaren kan ocksa krava sin vanliga Windows-drivrutin.
- Paketet ar gjort for 64-bitars Windows 10.
