#!/usr/bin/env bash
# 构建 konofanweb（网页版壳 App）
# 注意：aapt2/d8/zipalign 是 Windows 原生程序，参数里不能出现中文路径（会报"找不到文件"），
#      所以先在纯 ASCII 目录（默认 C:/kwbuild）里构建，最后把 apk 拷回来。
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
BT="${BT:-/f/python_work/逆向/tools/buildtools/android-14}"
SDK="${SDK:-/f/android-sdk}"
JAR="$SDK/platforms/android-34/android.jar"
JAVA="$SDK/jdk-17/bin/java"
JAVAC="$SDK/jdk-17/bin/javac"
KEYTOOL="$SDK/jdk-17/bin/keytool"
W=/c/kwbuild          # shell 用
WA="C:/kwbuild"        # 传给 Windows 原生 exe 用（必须是 C:/ 形式）

export MSYS2_ARG_CONV_EXCL='*'
export JAVA_TOOL_OPTIONS="-Duser.language=en -Dfile.encoding=UTF-8"

rm -rf "$W"
mkdir -p "$W/res" "$W/src" "$W/flat" "$W/gen" "$W/classes" "$W/dex"
cp -r "$HERE/res/." "$W/res/"
cp -r "$HERE/src/." "$W/src/"
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
  "$WA"/flat/*.flat

echo "[3/6] javac"
find "$W/src" "$W/gen" -name '*.java' | while read -r f; do cygpath -w "$f"; done > "$W/sources.txt"
"$JAVAC" -encoding UTF-8 --release 8 -nowarn -classpath "$(cygpath -w "$JAR")" -d "$WA/classes" "@$(cygpath -w "$W/sources.txt")"

echo "[4/6] d8"
find "$W/classes" -name '*.class' | while read -r f; do cygpath -w "$f"; done > "$W/classes.txt"
"$JAVA" -cp "$(cygpath -w "$BT")/lib/d8.jar" com.android.tools.r8.D8 \
  --release --lib "$(cygpath -w "$JAR")" --min-api 24 --output "$WA/dex" "@$(cygpath -w "$W/classes.txt")"

echo "[5/6] 打包 classes.dex"
cp "$W/base.apk" "$W/unsigned.apk"
python - <<'PY'
import shutil, zipfile
shutil.copyfile(r'C:/kwbuild/base.apk', r'C:/kwbuild/unsigned.apk')
with zipfile.ZipFile(r'C:/kwbuild/unsigned.apk', 'a') as z:
    z.write(r'C:/kwbuild/dex/classes.dex', 'classes.dex', compress_type=zipfile.ZIP_STORED)
PY
"$BT/zipalign.exe" -f -p 4 "$WA/unsigned.apk" "$WA/aligned.apk"

echo "[6/6] 签名"
KS="$HERE/keystore/debug.keystore"
mkdir -p "$HERE/keystore"
if [ ! -f "$KS" ]; then
  "$KEYTOOL.exe" -genkeypair -keystore "$(cygpath -w "$KS")" -storepass android -keypass android \
    -alias androiddebugkey -keyalg RSA -keysize 2048 -validity 10000 \
    -dname "CN=Android Debug,O=Android,C=US" >/dev/null 2>&1
fi
"$JAVA" -jar "$(cygpath -w "$BT")/lib/apksigner.jar" sign \
  --ks "$(cygpath -w "$KS")" --ks-pass pass:android --key-pass pass:android \
  --v1-signing-enabled true --v2-signing-enabled true --v3-signing-enabled true \
  --out "$WA/konofanweb.apk" "$WA/aligned.apk"

"$JAVA" -jar "$(cygpath -w "$BT")/lib/apksigner.jar" verify --print-certs "$WA/konofanweb.apk" | head -3
cp "$W/konofanweb.apk" "$HERE/konofanweb.apk"
ls -l "$HERE/konofanweb.apk"
