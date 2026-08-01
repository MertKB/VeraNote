# install.ps1 - Vera Note One-Click Installer & Shortcut Creator for Windows
$ErrorActionPreference = "Stop"

$AppName = "Vera Note"
$ExeName = "VeraNote.exe"
$SourceDir = Join-Path $PSScriptRoot "dist\VeraNote"

if (-not (Test-Path (Join-Path $SourceDir $ExeName))) {
    Write-Host "[!] Error: $SourceDir\$ExeName not found. Please run build.ps1 first." -ForegroundColor Red
    exit 1
}

$InstallDir = "$env:LOCALAPPDATA\Programs\VeraNote"
Write-Host "[*] Installing $AppName to $InstallDir..." -ForegroundColor Cyan

if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Copy-Item -Path "$SourceDir\*" -Destination $InstallDir -Recurse -Force

$TargetExe = Join-Path $InstallDir $ExeName
$IconPath = Join-Path $InstallDir "assets\app_icon.ico"

# Create Desktop Shortcut
$WshShell = New-Object -ComObject WScript.Shell
$DesktopPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Desktop)
$DesktopShortcut = $WshShell.CreateShortcut((Join-Path $DesktopPath "$AppName.lnk"))
$DesktopShortcut.TargetPath = $TargetExe
$DesktopShortcut.WorkingDirectory = $InstallDir
if (Test-Path $IconPath) { $DesktopShortcut.IconLocation = $IconPath }
$DesktopShortcut.Description = "Vera Note - Notlar ve Modeller"
$DesktopShortcut.Save()

# Create Start Menu Shortcut
$StartMenuPath = [System.Environment]::GetFolderPath([System.Environment+SpecialFolder]::Programs)
$StartMenuShortcut = $WshShell.CreateShortcut((Join-Path $StartMenuPath "$AppName.lnk"))
$StartMenuShortcut.TargetPath = $TargetExe
$StartMenuShortcut.WorkingDirectory = $InstallDir
if (Test-Path $IconPath) { $StartMenuShortcut.IconLocation = $IconPath }
$StartMenuShortcut.Description = "Vera Note - Notlar ve Modeller"
$StartMenuShortcut.Save()

Write-Host "[+] Installation Complete!" -ForegroundColor Green
Write-Host "[+] Shortcuts created on Desktop and Start Menu for Vera Note." -ForegroundColor Green
