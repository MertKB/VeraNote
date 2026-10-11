#!/bin/bash
set -e

echo "[*] Building VeraNote Linux AppImage..."

# 1. Install dependencies
python3 -m pip install -q -r requirements.txt pyinstaller

# 2. PyInstaller build
python3 -m PyInstaller VeraNote.spec --noconfirm

# 3. Setup AppDir
APPDIR="build/AppDir"
rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"

# Copy PyInstaller distribution
cp -r dist/VeraNote/* "$APPDIR/usr/bin/"

# Copy desktop integration files and icons
cp veranote.desktop "$APPDIR/"
cp assets/app_icon.png "$APPDIR/veranote.png"
cp assets/app_icon.png "$APPDIR/.DirIcon"
cp assets/app_icon.png "$APPDIR/usr/share/icons/hicolor/256x256/apps/veranote.png"

# Create standard AppRun launcher
cat << 'EOF' > "$APPDIR/AppRun"
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/bin/_internal:${LD_LIBRARY_PATH}"
exec "${HERE}/usr/bin/VeraNote" "$@"
EOF
chmod +x "$APPDIR/AppRun"

# 4. Download appimagetool if not present
if [ ! -f "appimagetool" ]; then
    echo "[*] Downloading appimagetool..."
    wget -q -O appimagetool https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
    chmod +x appimagetool
fi

# 5. Build AppImage
mkdir -p dist
ARCH=x86_64 ./appimagetool "$APPDIR" "dist/VeraNote-x86_64.AppImage"

echo "[+] VeraNote AppImage built successfully: dist/VeraNote-x86_64.AppImage"
