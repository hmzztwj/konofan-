"""在已去 mod 的 APK 基础上替换 global-metadata.dat（用于改 API 地址等），重新打包。

用法：python tools/build_probe_apk.py
读 apk/konofan_v570_demod.apk + tools/out/meta/global-metadata.patched.dat
写 apk/build/probe-unsigned.apk
"""
import os
import zipfile

SRC = r"apk\konofan_v570_demod.apk"
META = r"tools\out\meta\global-metadata.patched.dat"
OUT = r"apk\build\probe-unsigned.apk"
ENTRY = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
STORE = (".so", ".arsc")


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    meta = open(META, "rb").read()
    zin = zipfile.ZipFile(SRC)
    n = 0
    replaced = 0
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == ENTRY:
                data = meta
                replaced += 1
            comp = zipfile.ZIP_STORED if item.filename.endswith(STORE) else zipfile.ZIP_DEFLATED
            zi = zipfile.ZipInfo(item.filename, date_time=(2024, 10, 8, 0, 0, 0))
            zi.compress_type = comp
            zi.external_attr = item.external_attr
            zout.writestr(zi, data)
            n += 1
    print("[+] %s  %d entries, metadata replaced=%d, %d B" % (OUT, n, replaced, os.path.getsize(OUT)))


if __name__ == "__main__":
    main()
