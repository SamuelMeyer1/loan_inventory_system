#ifndef AppVersion
  #error AppVersion must be passed by Build-Setup.ps1
#endif
#ifndef BuildRoot
  #error BuildRoot must be passed by Build-Setup.ps1
#endif
#ifndef OutputRoot
  #error OutputRoot must be passed by Build-Setup.ps1
#endif
#ifndef TestInstall
  #define ProductId "LoanInventory.SamuelMeyer1"
#else
  #define ProductId "LoanInventory.SamuelMeyer1.PackagingTest"
#endif

[Setup]
AppId={#ProductId}
AppName=Loan Inventory
AppVersion={#AppVersion}
AppPublisher=Samuel Meyer
AppPublisherURL=https://github.com/SamuelMeyer1/loan_inventory_system
AppUpdatesURL=https://github.com/SamuelMeyer1/loan_inventory_system/releases
DefaultDirName={localappdata}\Programs\LoanInventory
DefaultGroupName=Loan Inventory
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputRoot}
OutputBaseFilename=LoanInventory-{#AppVersion}-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\build\windows\loan-inventory.ico
UninstallDisplayIcon={app}\LoanInventory.exe
AppMutex=Local\LoanInventorySystem.Running
CloseApplications=no
RestartApplications=no
SetupLogging=yes
DisableProgramGroupPage=yes
#ifdef TestInstall
Uninstallable=yes
CreateUninstallRegKey=no
UsePreviousAppDir=no
UsePreviousTasks=no
#endif

[Tasks]
Name: "desktopicon"; Description: "Skapa en genväg på skrivbordet"; Flags: unchecked

[Files]
Source: "{#BuildRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

#ifndef TestInstall
[Icons]
Name: "{group}\Loan Inventory"; Filename: "{app}\LoanInventory.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\Loan Inventory"; Filename: "{app}\LoanInventory.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\LoanInventory.exe"; Description: "Starta Loan Inventory"; Flags: nowait postinstall skipifsilent
#endif

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if CheckForMutexes('Local\LoanInventorySystem.Running') then
  begin
    if WizardSilent then
      Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if CheckForMutexes('Local\LoanInventorySystem.Running') then
  begin
    if UninstallSilent then
      Result := False;
  end;
end;
