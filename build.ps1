# build.ps1 - Automated Build Script for Vera Note
$ErrorActionPreference = "Stop"

Write-Host "[*] Building Vera Note (.exe)..." -ForegroundColor Cyan

# Install dependencies if missing
python -m pip install -q -r requirements.txt

# Run PyInstaller
python -m PyInstaller VeraNote.spec --noconfirm

Write-Host "[+] Vera Note Executable Build Complete!" -ForegroundColor Green
Write-Host "[+] Output location: dist\VeraNote\VeraNote.exe" -ForegroundColor Green

# Create distribution ZIP archive
$zipPath = "dist\VeraNote-v2.0.0.zip"
Write-Host "[*] Packaging $zipPath..." -ForegroundColor Cyan
if (Test-Path $zipPath) {
    Remove-Item $zipPath -Force
}
Compress-Archive -Path "dist\VeraNote" -DestinationPath $zipPath
Write-Host "[+] Release ZIP created: $zipPath" -ForegroundColor Green
