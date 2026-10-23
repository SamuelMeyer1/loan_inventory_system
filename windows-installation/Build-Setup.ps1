param(
    [string]$Python = "python",
    [string]$ISCC = "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    [switch]$TestInstall
)
$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
Set-Location $root
$build = Join-Path $root "build\windows"
$venv = Join-Path $build "venv"
$output = Join-Path $root "dist\installer"
New-Item -ItemType Directory -Force $build, $output, "$build\scratch" | Out-Null
$env:TEMP = "$build\scratch"
$env:TMP = "$build\scratch"
$env:PYTHONDONTWRITEBYTECODE = "1"
$env:PYINSTALLER_CONFIG_DIR = "$build\pyinstaller-cache"
$env:PIP_CACHE_DIR = "$build\pip-cache"
if (-not (Test-Path $ISCC)) { throw "Inno Setup 6 saknas. Installera från https://jrsoftware.org/isdl.php och ange -ISCC." }
if (-not (Test-Path "$venv\Scripts\python.exe")) {
    & $Python -m venv $venv
    if ($LASTEXITCODE -ne 0) { throw "Kunde inte skapa byggmiljön." }
}
$pythonExe = "$venv\Scripts\python.exe"
& $pythonExe -m pip install --quiet --only-binary=:all: -r "$PSScriptRoot\requirements-build.txt"
if ($LASTEXITCODE -ne 0) { throw "Kunde inte installera låsta byggberoenden." }
& $pythonExe -B "$PSScriptRoot\prepare_build.py"
if ($LASTEXITCODE -ne 0) { throw "Versions- eller resurskontroll misslyckades." }
$version = (& $pythonExe -B -c "from app_version import VERSION; print(VERSION)").Trim()
if ($LASTEXITCODE -ne 0) { throw "Kunde inte läsa versionen." }
& $pythonExe -B -m PyInstaller --noconfirm --clean --log-level WARN --workpath "$build\pyinstaller" --distpath "$root\dist" "$PSScriptRoot\LoanInventory.spec"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller misslyckades." }
& $pythonExe -B "$PSScriptRoot\verify_bundle.py" "$root\dist\LoanInventory"
if ($LASTEXITCODE -ne 0) { throw "Paketkontroll misslyckades." }
$arguments = @("/Q", "/DAppVersion=$version", "/DBuildRoot=$root\dist\LoanInventory", "/DOutputRoot=$output")
if ($TestInstall) {
    $arguments += "/DTestInstall=1"
    $arguments += "/FLoanInventory-$version-TestSetup"
}
& $ISCC @arguments "$PSScriptRoot\LoanInventory.iss"
if ($LASTEXITCODE -ne 0) { throw "Inno Setup misslyckades." }
Get-ChildItem $output -Filter "*.exe" | ForEach-Object {
    Get-FileHash $_.FullName -Algorithm SHA256
}
