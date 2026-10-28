# -*- coding: utf-8 -*-
"""把原版 mod APK 重打包成「去 mod」版本。

- classes4.dex 用打过补丁的版本（PMLauncher.init -> return-void）
- AndroidManifest.xml 用打过补丁的版本（去掉 application name / platinmods 组件）
- 移除 lib/arm64-v8a/libplatinmods.so 与 assets/platinmodsRB.png
"""
import os
import sys
import zipfile

SRC = r"apk\konofan_v570_20241008.apk"
OUT = r"apk\build\clean2-unsigned.apk"
MANIFEST = r"tools\out\AndroidManifest.patched.xml"
PATCHED_DEX = r"tools\out\dex\classes4.patched.dex"
DROP = {
    "lib/arm64-v8a/libplatinmods.so",
    "assets/platinmodsRB.png",
}
STORE_EXT = (".so", "resources.arsc")

src = zipfile.ZipFile(SRC)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
n_skip = 0
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as dst:
    for info in src.infolist():
        name = info.filename
        if name in DROP:
            n_skip += 1
            continue
        data = src.read(name)
        if name == "AndroidManifest.xml":
            data = open(MANIFEST, "rb").read()
            print("[*] manifest ->", len(data))
        elif name == "classes4.dex":
            data = open(PATCHED_DEX, "rb").read()
            print("[*] classes4.dex ->", len(data))
        comp = zipfile.ZIP_STORED if name.endswith(STORE_EXT) else zipfile.ZIP_DEFLATED
        zi = zipfile.ZipInfo(name, date_time=info.date_time)
        zi.compress_type = comp
        zi.external_attr = info.external_attr
        dst.writestr(zi, data)
print(f"[+] {OUT} {os.path.getsize(OUT):,} B, 跳过 {n_skip} 个条目")
