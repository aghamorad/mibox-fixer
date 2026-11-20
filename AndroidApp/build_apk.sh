#!/bin/bash
# Compiles MoBox.apk (Android 7.0+ / API 24+, works on 32-bit Mi Box 4 AND 64-bit Android phones)
# using plain javac + d8 + aapt2 + apksigner (zero Gradle).
set -euo pipefail

cd "$(dirname "$0")"
HERE="$PWD"
ROOT="$(cd .. && pwd)"

SDK_CACHE="$HOME/.cache/android-sdk"
AAPT2="$SDK_CACHE/android-14/aapt2"
D8="$SDK_CACHE/android-14/d8"
ZIPALIGN="$SDK_CACHE/android-14/zipalign"
APKSIGNER="$SDK_CACHE/android-14/apksigner"
ANDROID_JAR="$SDK_CACHE/android-34/android.jar"

BUILD="$HERE/.build"
rm -rf "$BUILD"
mkdir -p "$BUILD/gen" "$BUILD/classes" "$BUILD/dex" "$HERE/res/drawable" "$ROOT/docs/downloads"

# 1. Copy our Paul Rand + Liquid Glass icon and generate the 320x180 Android TV Leanback banner
cp "$ROOT/MoBoxApp/Resources/AppIcon.iconset/icon_128x128@2x.png" "$HERE/res/drawable/ic_launcher.png"
python3 -c '
import struct, zlib
W, H = 320, 180
rows = []
for y in range(H):
    row = []
    for x in range(W):
        # Paul Rand deep charcoal background with vermilion & gold accent badge
        c = (20, 25, 38)
        if 20 <= x <= 140 and 30 <= y <= 150:
            c = (234, 74, 40)
            if 36 <= x <= 124 and 46 <= y <= 134:
                c = (18, 36, 64)
        elif 165 <= x <= 285 and 76 <= y <= 104:
            c = (244, 184, 12)
        row.append(c)
    rows.append(row)
raw = b"".join(b"\x00" + bytes(v for px in r for v in px) for r in rows)
def chunk(t, d):
    b = t + d
    return struct.pack(">I", len(d)) + b + struct.pack(">I", zlib.crc32(b) & 0xffffffff)
ihdr = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
with open("res/drawable/tv_banner.png", "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))
'

# 2. Compile resources with aapt2
"$AAPT2" compile --dir "$HERE/res" -o "$BUILD/res.zip"
"$AAPT2" link \
    -I "$ANDROID_JAR" \
    --manifest "$HERE/AndroidManifest.xml" \
    -A "$HERE/assets" \
    -o "$BUILD/unaligned.apk" \
    --java "$BUILD/gen" \
    "$BUILD/res.zip"

# 3. Compile Java sources (Java 11 bytecode for d8 desugaring to min-api 24)
javac --release 11 \
    -cp "$ANDROID_JAR" \
    -d "$BUILD/classes" \
    "$HERE/src/com/morad/mobox/MainActivity.java" \
    "$HERE/src/com/morad/mobox/PointerService.java" \
    "$HERE/src/com/morad/mobox/CursorView.java" \
    "$BUILD/gen/com/morad/mobox/R.java"

# 4. Package classes.jar and convert to classes.dex with d8
jar cf "$BUILD/classes.jar" -C "$BUILD/classes" .
"$D8" --lib "$ANDROID_JAR" --min-api 24 --output "$BUILD/dex" "$BUILD/classes.jar"

# 5. Add classes.dex into the APK
(cd "$BUILD/dex" && zip -q "$BUILD/unaligned.apk" classes.dex)

# 6. Align and sign the APK
"$ZIPALIGN" -f 4 "$BUILD/unaligned.apk" "$BUILD/aligned.apk"

KEYSTORE="$SDK_CACHE/mobox-release.jks"
if [ ! -f "$KEYSTORE" ]; then
    keytool -genkeypair \
        -keystore "$KEYSTORE" \
        -storepass mobox123 \
        -keypass mobox123 \
        -alias mobox \
        -keyalg RSA \
        -keysize 2048 \
        -validity 10000 \
        -dname "CN=Morad, O=MoBox, C=US" >/dev/null 2>&1
fi

OUT_APK="$ROOT/docs/downloads/MoBox.apk"
"$APKSIGNER" sign \
    --ks "$KEYSTORE" \
    --ks-pass pass:mobox123 \
    --key-pass pass:mobox123 \
    --out "$OUT_APK" \
    "$BUILD/aligned.apk"

ls -lh "$OUT_APK"
