# -*- coding: utf-8 -*-
"""验证 CRI 文件名派生：disk_name = Base64Url(SHA256(UTF8(salt + plain)))

salt 来自运行时读取的 Wonder.Util.Crypt.ShaEncryption.Salt 的 fakeValue = 'p8c3oOXf'
"""
import base64
import glob
import hashlib
import json
import os
import urllib.parse

SALT = "p8c3oOXf"
DATA = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"
CRI = os.path.join(DATA, "bundles", "Cri")
CAT = os.path.join(DATA, "com.unity.addressables", "catalog_stable.json")


def load_blobs():
    blobs = {}
    for sub in ("Cpk", "Usm"):
        for p in glob.glob(os.path.join(CRI, sub) + "/*.*"):
            f = os.path.basename(p)
            s = urllib.parse.unquote(f.rsplit(".", 1)[0])
            blobs[base64.b64decode(s + "=" * (-len(s) % 4))] = f
    return blobs


def main():
    blobs = load_blobs()
    cri = json.load(open(r"F:\python_work\逆向\out\masterdata\cri_cache.json", encoding="utf-8"))["Caches"]
    cat = json.load(open(CAT, encoding="utf-8"))
    ids = [i for i in cat["m_InternalIds"] if i.endswith(".bytes")]
    print(f"cache names={len(cri)} catalog .bytes={len(ids)} blobs={len(blobs)}")

    cands = set()
    for c in cri:
        n = c["name"]
        base, ext = os.path.splitext(n)
        for v in (n, base, n.lower(), base.lower(), "Cpk/" + n, "Cri/" + n, "Cri/Cpk/" + n):
            cands.add(v)
    for i in ids:
        p = i.replace("\\", "/")
        base = os.path.basename(p)
        for v in (p, p[:-6], base, base[:-6]):
            cands.add(v)
    print("candidates", len(cands))

    hits = []
    for v in cands:
        d = hashlib.sha256((SALT + v).encode()).digest()
        if d in blobs:
            hits.append((v, blobs[d]))
    print("hits", len(hits))
    for h in hits[:10]:
        print("  ", h)


if __name__ == "__main__":
    main()
