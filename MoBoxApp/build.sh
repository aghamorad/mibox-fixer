#!/bin/bash
# Builds "MoBox.app" (Universal arm64 + x86_64) — swiftc only, no Xcode project.
set -euo pipefail

cd "$(dirname "$0")"
HERE="$PWD"
ROOT="$(cd .. && pwd)"
NAME="MoBox"
APP="$HERE/$NAME.app"

if [ -d "$APP" ]; then
    STAMP=$(date +%Y%m%d-%H%M%S)
    mkdir -p "$HOME/.Trash"
    mv "$APP" "$HOME/.Trash/$NAME $STAMP.app"
fi

python3 "$HERE/make_icon.py"

mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources/engine"

echo "Bundling MoBox Python engine & Phone Web App..."
cp -R "$ROOT/fixer"     "$APP/Contents/Resources/engine/fixer"
cp -R "$ROOT/web"       "$APP/Contents/Resources/engine/web"
cp -R "$ROOT/playlists" "$APP/Contents/Resources/engine/playlists"
cp "$HERE/icon-preview.png" "$APP/Contents/Resources/engine/MoBoxIcon.png"

cp "$HERE/Resources/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"

COMMIT="$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
BUILD_DATE="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>            <string>MoBox</string>
    <key>CFBundleIdentifier</key>            <string>com.morad.mobox</string>
    <key>CFBundleName</key>                  <string>MoBox</string>
    <key>CFBundleDisplayName</key>           <string>MoBox</string>
    <key>CFBundleIconFile</key>              <string>AppIcon.icns</string>
    <key>CFBundlePackageType</key>           <string>APPL</string>
    <key>CFBundleShortVersionString</key>    <string>2.1.0</string>
    <key>CFBundleVersion</key>               <string>21</string>
    <key>MoBoxBuildCommit</key>              <string>${COMMIT}</string>
    <key>MoBoxBuildDate</key>                <string>${BUILD_DATE}</string>
    <key>LSMinimumSystemVersion</key>        <string>13.0</string>
    <key>NSHighResolutionCapable</key>       <true/>
    <key>NSPrincipalClass</key>              <string>NSApplication</string>
    <key>NSLocalNetworkUsageDescription</key>
    <string>MoBox discovers your Mi Box or Android TV on your home Wi-Fi and serves the Phone Web App on your local network.</string>
    <key>NSAppTransportSecurity</key>
    <dict>
        <key>NSAllowsArbitraryLoads</key>    <true/>
    </dict>
</dict>
</plist>
PLIST

echo "Compiling Universal macOS Binary (arm64 + x86_64)..."
mkdir -p "$HERE/.build"
for arch in arm64 x86_64; do
    swiftc -O \
        -swift-version 5 \
        -parse-as-library \
        -target "$arch-apple-macos13.0" \
        -o "$HERE/.build/MoBox-$arch" \
        "$HERE"/Sources/*.swift
done

lipo -create \
    "$HERE/.build/MoBox-arm64" \
    "$HERE/.build/MoBox-x86_64" \
    -output "$APP/Contents/MacOS/MoBox"

codesign --force --deep --sign - "$APP"
lipo -info "$APP/Contents/MacOS/MoBox"
echo "Built: $APP"
