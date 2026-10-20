$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir
$OutputDir = Join-Path $ProjectDir "LoanInventorySystem-Windows10"
$AppDir = Join-Path $OutputDir "app"

if (Test-Path -LiteralPath $OutputDir) {
    Remove-Item -LiteralPath $OutputDir -Recurse -Force
}
New-Item -ItemType Directory -Path $AppDir -Force | Out-Null

$items = @("backend", "frontend", "scripts", "docs", "main.py", "requirements.txt", "README.md")
foreach ($item in $items) {
    Copy-Item -LiteralPath (Join-Path $ProjectDir $item) -Destination $AppDir -Recurse -Force
}

Get-ChildItem -LiteralPath $AppDir -Directory -Filter "__pycache__" -Recurse |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $AppDir -File -Recurse |
    Where-Object { $_.Extension -in @(".pyc", ".pyo") } |
    Remove-Item -Force

$DataDir = Join-Path $ProjectDir "data"
$TargetDataDir = Join-Path $AppDir "data"
New-Item -ItemType Directory -Path $TargetDataDir -Force | Out-Null

$answer = Read-Host "Ska den aktuella databasen med alla uppgifter folja med? (J/N)"
if ($answer -match "^[JjYy]") {
    $database = Join-Path $DataDir "inventory.db"
    if (Test-Path -LiteralPath $database) {
        Copy-Item -LiteralPath $database -Destination $TargetDataDir
        Write-Host "Databasen inkluderades." -ForegroundColor Yellow
    } else {
        Write-Warning "Ingen data\inventory.db hittades. En ny databas skapas vid forsta start."
    }
}

Copy-Item -LiteralPath (Join-Path $ScriptDir "Installera.bat") -Destination $OutputDir
Copy-Item -LiteralPath (Join-Path $ScriptDir "Installera.ps1") -Destination $OutputDir
Copy-Item -LiteralPath (Join-Path $ScriptDir "README.txt") -Destination $OutputDir
Copy-Item -LiteralPath (Join-Path $ScriptDir "offline") -Destination $OutputDir -Recurse -Force

Write-Host "Paketet ar klart:" -ForegroundColor Green
Write-Host $OutputDir
Write-Host "Kopiera hela mappen till den nya datorn och dubbelklicka pa Installera.bat."
