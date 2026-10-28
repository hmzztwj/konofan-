#!/usr/bin/env bash
# 构建 素晴管理器（konofanmgr）
# aapt2/d8/zipalign/apksigner 是 Windows 原生程序，参数里不能有中文路径 ⇒ 先在 C:/kwbuild_mgr 构建再拷回。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BT="${BT:-/f/python_work/逆向/tools/buildtools/android-14}"
SDK="${SDK:-/f/android-sdk}"
JAR="$SDK/platforms/android-34/android.jar"
JAVA="$SDK/jdk-17/bin/java"
JAVAC="$SDK/jdk-17/bin/javac"
W=/c/kwbuild_mgr
WA="C:/kwbuild_mgr"

export MSYS2_ARG_CONV_EXCL='*'
export JAVA_TOOL_OPTIONS="-Duser.language=en -Dfile.encoding=UTF-8"

rm -rf "$W"
mkdir -p "$W/res" "$W/src" "$W/assets" "$W/flat" "$W/gen" "$W/classes" "$W/dex"
cp -r "$HERE/res/." "$W/res/"
cp -r "$HERE/src/." "$W/src/"
cp -r "$HERE/assets/." "$W/assets/"
cp "$HERE/AndroidManifest.xml" "$W/AndroidManifest.xml"

echo "[1/6] aapt2 compile"
"$BT/aapt2.exe" compile --dir "$WA/res" -o "$WA/flat"

echo "[2/6] aapt2 link"
"$BT/aapt2.exe" link -o "$WA/base.apk" \
  -I "$(cygpath -w "$JAR")" \
  --manifest "$WA/AndroidManifest.xml" \
  --min-sdk-version 24 --target-sdk-version 29 \
  --java "$WA/gen" \
  --auto-add-overlay \
  -A "$WA/assets" \
  "$WA"/flat/*.flat

echo "[3/6] javac"
find "$W/src" "$W/gen" -name '*.java' | while read -r f; do cygpath -w "$f"; done > "$W/sources.txt"
"$JAVAC" -encoding UTF-8 --release 8 -nowarn -classpath "$(cygpath -w "$JAR")" -d "$WA/classes" "@$(cygpath -w "$W/sources.txt")"

echo "[4/6] d8"
find "$W/classes" -name '*.class' | while read -r f; do cygpath -w "$f"; done > "$W/classes.txt"
"$JAVA" -cp "$(cygpath -w "$BT")/lib/d8.jar" com.android.tools.r8.D8 \
  --min-api 24 --lib "$(cygpath -w "$JAR")" --output "$WA/dex" "@$(cygpath -w "$W/classes.txt")"

echo "[5/6] 打包 classes.dex"
cp "$WA/base.apk" "$WA/unsigned.apk"
python - <<'PY'
import zipfile
with zipfile.ZipFile(r'C:/kwbuild_mgr/unsigned.apk', 'a') as z:
    z.write(r'C:/kwbuild_mgr/dex/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_STORED)
PY

echo "[6/6] 对齐 + 签名"
"$BT/zipalign.exe" -f -p 4 "$WA/unsigned.apk" "$WA/aligned.apk"
"$JAVA" -jar "$(cygpath -w "$BT/lib/apksigner.jar")" sign \
  --ks "$(cygpath -w "$HERE/keystore/debug.keystore")" \
  --ks-pass pass:android --key-pass pass:android --ks-key-alias androiddebugkey \
  --out "$WA/konofanmgr.apk" "$WA/aligned.apk"
"$JAVA" -jar "$(cygpath -w "$BT/lib/apksigner.jar")" verify --print-certs "$WA/konofanmgr.apk" | head -3

cp "$WA/konofanmgr.apk" "$HERE/konofanmgr.apk"
"$BT/aapt2.exe" dump badging "$WA/konofanmgr.apk" | head -1
ls -l "$HERE/konofanmgr.apk"
