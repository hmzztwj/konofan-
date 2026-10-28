"""在内存 dump 里以 8 字节对齐滑窗暴力定位 MasterData 的 AES key。

原理: CBC 模式下末块明文 P_last = D(C_last) XOR C_prev, 与 IV 无关。
     若 key 正确, P_last 必为合法 PKCS#7 填充(末字节 n, 且末尾 n 字节都等于 n)。
     命中后再用第一块明文 / 可打印性做二次确认。

用法:
    python tools/scan_key_mem.py <mem目录> [--workers N]

会扫描 manifest.json 里列出的所有 .bin, 输出命中候选 (key, 文件)。
"""
import base64
import glob
import json
import os
import sys
from multiprocessing import Pool

from Crypto.Cipher import AES

ROOT = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
# 用于校验的文件：末块 + 头部都得像 JSON
CHECK = [
    os.path.join(ROOT, "MasterData", "ad_reward.data"),
    os.path.join(ROOT, "MasterData", "assist.data"),
    os.path.join(ROOT, "tutorial.data"),
    os.path.join(ROOT, "notification.data"),
]


def load_ct():
    out = []
    for p in CHECK:
        if not os.path.exists(p):
            continue
        raw = base64.b64decode(open(p, "rb").read().strip(), validate=True)
        if len(raw) % 16 or len(raw) < 32:
            continue
        out.append((os.path.basename(p), raw[-16:], raw[-32:-16]))
    return out


def padding_ok(pt, prev):
    """返回 True 表示 P_last 为合法 PKCS#7"""
    x = bytes(a ^ b for a, b in zip(pt, prev))
    n = x[-1]
    if n < 1 or n > 16:
        return False
    return x[-n:] == bytes([n]) * n


def scan_chunk(args):
    path, keysize, cts = args
    found = []
    data = open(path, "rb").read()
    n = len(data)
    step = 8
    for off in range(0, n - keysize + 1, step):
        key = data[off:off + keysize]
        # 快速排除: 全 0 / 全 ff / 全可打印 ASCII 的窗口不是随机密钥
        if key == bytes(keysize):
            continue
        try:
            cipher = AES.new(key, AES.MODE_ECB)
        except Exception:
            continue
        ok_all = True
        for name, clast, cprev in cts:
            pt = cipher.decrypt(clast)
            if not padding_ok(pt, cprev):
                ok_all = False
                break
        if ok_all:
            found.append((os.path.basename(path), off, key.hex()))
            print(f"[HIT] {os.path.basename(path)} off={off:#x} key={key.hex()}", flush=True)
    return found


def main():
    d = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "out", "mem")
    cts = load_ct()
    if len(cts) < 2:
        print("[-] 缺少校验文件，只有", len(cts))
        return 1
    print(f"[+] 校验文件 {len(cts)} 个: {[c[0] for c in cts]}")
    files = sorted(glob.glob(os.path.join(d, "*.bin")))
    if not files:
        print("[-] 目录里没有 .bin:", d)
        return 1
    total = sum(os.path.getsize(f) for f in files)
    print(f"[+] {len(files)} 个 dump, {total/1048576:.1f} MB")

    tasks = [(f, ks, cts) for f in files for ks in (32, 16)]
    hits = []
    with Pool(processes=min(8, os.cpu_count() or 4)) as pool:
        for r in pool.imap_unordered(scan_chunk, tasks):
            hits.extend(r)
    print(f"[=] 命中 {len(hits)} 个候选")
    with open(os.path.join(d, "hits.json"), "w", encoding="utf-8") as f:
        json.dump(hits, f, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
