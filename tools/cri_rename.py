# -*- coding: utf-8 -*-
"""把 CRI 媒体文件按明文名归类。

算法（逆向自 Wonder.Util.Crypt.ShaEncryption.EncryptStreamingAssetsNameString，
RVA 0x2E816D0，反汇编确认调用链 SHA256.Create → Encoding.UTF8 →
String.Format("{0}{1}", Salt, name) → ComputeHash → Convert.ToBase64String）：

    磁盘名 = UrlEncode(Base64(SHA256(UTF8(SALT + 不含扩展名的原名))) + 原扩展名)

其中 SALT = Wonder.Util.Crypt.ShaEncryption.Salt 的明文 = 'p8c3oOXf'
（运行时从 ObscuredString.fakeValue 读出，tools/read_obscured.py）。

产物:
  out/cri_manifest.csv         磁盘文件名 -> 明文名 + catalog 路径/分类
  out/cri_sorted/<分类>/<明文名>  硬链接树（同一分区，不占额外空间）
"""
import base64
import csv
import glob
import hashlib
import json
import os
import urllib.parse

SALT = "p8c3oOXf"
DATA = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"
CRI = os.path.join(DATA, "bundles", "Cri")
CAT = os.path.join(DATA, "com.unity.addressables", "catalog_stable.json")
OUT = r"F:\python_work\逆向\out"
SORTED = os.path.join(OUT, "cri_sorted")


def digest(plain_noext):
    return hashlib.sha256((SALT + plain_noext).encode("utf-8")).digest()


def main():
    cat = json.load(open(CAT, encoding="utf-8"))
    # digest -> (明文名含扩展名, catalog 路径)
    table = {}
    for i in cat["m_InternalIds"]:
        if not i.endswith(".bytes"):
            continue
        p = i.replace("\\", "/")
        leaf = os.path.basename(p)[:-6]          # 去掉 .bytes
        if not (leaf.endswith(".cpk") or leaf.endswith(".usm")):
            continue
        noext, ext = os.path.splitext(leaf)
        table[digest(noext)] = (leaf, p)
    print(f"[+] catalog CRI 条目 {len(table)}")

    files = []
    for sub in ("Cpk", "Usm"):
        files += glob.glob(os.path.join(CRI, sub) + "/*.*")
    print(f"[+] 磁盘文件 {len(files)}")

    rows, miss, linked = [], 0, 0
    for p in sorted(files):
        disk = os.path.basename(p)
        s = urllib.parse.unquote(disk.rsplit(".", 1)[0])
        try:
            d = base64.b64decode(s + "=" * (-len(s) % 4))
        except Exception:
            miss += 1
            continue
        hit = table.get(d)
        if not hit:
            miss += 1
            rows.append({"disk": disk, "plain": "", "category": "zz_unknown", "catalog_path": ""})
            continue
        leaf, catpath = hit
        # 分类: Cri/Cpk/BGM/Battle/xxx.cpk.bytes -> Cpk/BGM/Battle
        parts = catpath.split("/")
        try:
            k = parts.index("Cri")
            cat_parts = parts[k + 1:-1]
            category = "/".join(cat_parts[:3]) if cat_parts else "zz_unknown"
        except ValueError:
            category = "zz_unknown"
        rows.append({"disk": disk, "plain": leaf, "category": category, "catalog_path": catpath})

        dst_dir = os.path.join(SORTED, category)
        os.makedirs(dst_dir, exist_ok=True)
        dst = os.path.join(dst_dir, leaf)
        if not os.path.exists(dst):
            try:
                os.link(p, dst)
                linked += 1
            except OSError:
                pass

    with open(os.path.join(OUT, "cri_manifest.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["disk", "plain", "category", "catalog_path"])
        w.writeheader()
        w.writerows(rows)

    cats = {}
    for r in rows:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    print(f"[+] 匹配 {len(rows) - miss}/{len(rows)}，未匹配 {miss}，硬链接 {linked}")
    print(f"[+] 分类 {len(cats)} 个:")
    for k, v in sorted(cats.items(), key=lambda x: -x[1])[:25]:
        print(f"    {v:>5}  {k}")


if __name__ == "__main__":
    main()
