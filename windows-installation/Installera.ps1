$ErrorActionPreference = "Stop"

$AppName = "Loan Inventory System"
$PythonVersion = "3.12.10"
$PackageDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$SourceDir = Join-Path $PackageDir "app"
$OfflineDir = Join-Path $PackageDir "offline"
$PythonInstaller = Join-Path $OfflineDir "python-$PythonVersion-amd64.exe"
$WheelDir = Join-Path $OfflineDir "wheels"
$InstallDir = Join-Path $env:LOCALAPPDATA "LoanInventorySystem"
$VenvPython = Join-Path $InstallDir ".venv\Scripts\python.exe"

function Find-Python312 {
    $launcher = Get-Command py.exe -ErrorAction SilentlyContinue
    if ($launcher) {
        & $launcher.Source -3.12 -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0) {
            return (& $launcher.Source -3.12 -c "import sys; print(sys.executable)").Trim()
        }
    }

    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Python\Python312\python.exe"
    if (Test-Path -LiteralPath $candidate) { return $candidate }
    return $null
}

if (-not (Test-Path -LiteralPath (Join-Path $SourceDir "main.py"))) {
    throw "Paketet saknar app\main.py. Kor Skapa-installationspaket.ps1 igen."
}

Write-Host "Installerar $AppName..." -ForegroundColor Cyan
$PythonExe = Find-Python312
if (-not $PythonExe) {
    if (-not (Test-Path -LiteralPath $PythonInstaller)) {
        throw "Offlinepaketet saknar $PythonInstaller. Bygg paketet igen pa den gamla datorn."
    }
    Write-Host "Python 3.12 saknas. Installerar Python $PythonVersion fran offlinepaketet..."
    $process = Start-Process -FilePath $PythonInstaller -ArgumentList "/quiet InstallAllUsers=0 PrependPath=0 Include_launcher=1 Include_test=0" -Wait -PassThru
    if ($process.ExitCode -ne 0) { throw "Python-installationen gav felkod $($process.ExitCode)." }
    $PythonExe = Find-Python312
}
if (-not $PythonExe) { throw "Python 3.12 kunde inte hittas efter installationen." }

$SavedDatabase = $null
if (Test-Path -LiteralPath (Join-Path $InstallDir "data\inventory.db")) {
    $SavedDatabase = Join-Path $env:TEMP "loan-inventory-existing-$([guid]::NewGuid()).db"
    Copy-Item -LiteralPath (Join-Path $InstallDir "data\inventory.db") -Destination $SavedDatabase
    Write-Host "Befintlig databas bevaras."
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
Get-ChildItem -LiteralPath $SourceDir -Force | Copy-Item -Destination $InstallDir -Recurse -Force
if ($SavedDatabase) {
    New-Item -ItemType Directory -Path (Join-Path $InstallDir "data") -Force | Out-Null
    Copy-Item -LiteralPath $SavedDatabase -Destination (Join-Path $InstallDir "data\inventory.db") -Force
    Remove-Item -LiteralPath $SavedDatabase -Force
}

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Host "Skapar en isolerad Python-miljo..."
    & $PythonExe -m venv (Join-Path $InstallDir ".venv")
    if ($LASTEXITCODE -ne 0) { throw "Kunde inte skapa Python-miljon." }
}

Write-Host "Installerar bibliotek..."
if (-not (Test-Path -LiteralPath $WheelDir)) { throw "Offlinepaketet saknar biblioteksmappen." }
& $VenvPython -m pip install --disable-pip-version-check --no-index --find-links $WheelDir -r (Join-Path $InstallDir "requirements.txt")
if ($LASTEXITCODE -ne 0) { throw "Kunde inte installera biblioteken." }

$StartScript = Join-Path $InstallDir "Starta Loan Inventory System.bat"
$startContents = @"
@echo off
cd /d "$InstallDir"
start "" "http://127.0.0.1:8000"
"$VenvPython" main.py
if errorlevel 1 pause
"@
Set-Content -LiteralPath $StartScript -Value $startContents -Encoding ASCII

$Desktop = [Environment]::GetFolderPath("Desktop")
$ShortcutPath = Join-Path $Desktop "$AppName.lnk"
$Shell = New-Object -ComObject WScript.Shell
$Shortcut = $Shell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = $StartScript
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description = "Starta $AppName"
$Shortcut.Save()

Write-Host "Klart! Programmet ar installerat i: $InstallDir" -ForegroundColor Green
Write-Host "En genvag har skapats pa skrivbordet."
Start-Process -FilePath $StartScript
