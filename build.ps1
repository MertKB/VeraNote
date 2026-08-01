# build.ps1 - Automated Build Script for Vera Note
$ErrorActionPreference = "Stop"

Write-Host "[*] Building Vera Note (.exe)..." -ForegroundColor Cyan

# Install dependencies if missing
python -m pip install -q -r requirements.txt

# Run PyInstaller
python -m PyInstaller VeraNote.spec --noconfirm

Write-Host "[+] Vera Note Executable Build Complete!" -ForegroundColor Green
Write-Host "[+] Output location: dist\VeraNote\VeraNote.exe" -ForegroundColor Green
