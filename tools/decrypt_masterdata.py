# -*- coding: utf-8 -*-
"""用运行时捕获的 AES key/iv 解密全部 MasterData 与本地存档 .data，导出为明文 JSON。

key/iv 来源: tools/read_key_runtime.py 从模拟器里运行中的 jp.co.sumzap.pj0007 进程
            AesEncryption.static_fields 直接读出的 byte[]（不是猜的）。
格式: 文件内容是 base64 文本 -> AES-256-CBC / PKCS#7 / 固定 IV -> UTF-8 JSON
"""
import base64
import glob
import json
import os
import re

from Crypto.Cipher import AES

KEY = bytes.fromhex("851c20916d7a895bc14ceba139e3dc253486b30b858140c41c8a7e9fe99aec72")
IV = bytes.fromhex("dcaa69cc863200d4eb74b4980bd60383")
ROOT = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
OUT = r"F:\python_work\逆向\out\masterdata"


def decrypt(path):
    raw = open(path, "rb").read().strip()
    ct = base64.b64decode(re.sub(rb"\s+", b"", raw))
    pt = AES.new(KEY, AES.MODE_CBC, IV).decrypt(ct)
    pad = pt[-1]
    if not (1 <= pad <= 16) or pt[-pad:] != bytes([pad]) * pad:
        raise ValueError("bad padding")
    return pt[:-pad], len(ct)


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(os.path.join(ROOT, "*.data")))
    files += sorted(glob.glob(os.path.join(ROOT, "MasterData", "*.data")))
    index, fail = [], []
    total_bytes = 0
    for p in files:
        name = os.path.basename(p)[:-5]
        try:
            pt, ctlen = decrypt(p)
            text = pt.decode("utf-8")
            obj = json.loads(text)
            out = os.path.join(OUT, name + ".json")
            with open(out, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, indent=1)
        except Exception as e:
            fail.append((name, str(e)[:60]))
            continue
        total_bytes += len(pt)
        rows = None
        if isinstance(obj, dict):
            if isinstance(obj.get("master"), list):
                rows = len(obj["master"])
            else:
                rows = len(obj)
        elif isinstance(obj, list):
            rows = len(obj)
        index.append((name, ctlen, len(pt), rows, list(obj)[:4] if isinstance(obj, dict) else "list"))

    index.sort(key=lambda r: -(r[2] or 0))
    with open(os.path.join(OUT, "_index.md"), "w", encoding="utf-8") as f:
        f.write(f"# MasterData 解密索引\n\n共 {len(index)} 个文件解密成功，{len(fail)} 个失败，"
                f"明文合计 {total_bytes/1048576:.1f} MB\n\n")
        f.write("| 表名 | 密文 B | 明文 B | 行数 | 顶层键 |\n|---|---:|---:|---:|---|\n")
        for name, c, pl, rows, keys in index:
            f.write(f"| {name} | {c:,} | {pl:,} | {rows if rows is not None else '-'} | "
                    f"{', '.join(keys) if isinstance(keys, list) else keys} |\n")
        if fail:
            f.write("\n## 失败\n\n")
            for n, e in fail:
                f.write(f"- {n}: {e}\n")

    print(f"[+] 成功 {len(index)} 个，失败 {len(fail)} 个，明文合计 {total_bytes/1048576:.1f} MB")
    print(f"[+] 输出目录 {OUT}")
    for n, c, pl, rows, keys in index[:12]:
        print(f"    {n:32s} {pl:>9,} B  行数={rows}")
    if fail:
        print("[!] 失败:", fail[:5])


if __name__ == "__main__":
    main()
