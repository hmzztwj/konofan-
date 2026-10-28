"""穷举：Pass = 任意两个字面量拼接，Salt = 任意一个字面量（含空串），
   PBKDF2-HMAC-SHA1 1000 次派生 48 字节 -> key(32)/iv(16)，AES-256-CBC 校验。

覆盖「TextUtil 76 个字段的赋值顺序被我们搞错」这种可能：
只要真 Pass/Salt 都在这 76 个字面量里，无论顺序如何都能命中。

用法: python tools/tu_concat_sweep.py
"""
import base64
import hashlib
import itertools
import json
import os
from multiprocessing import Pool

from Crypto.Cipher import AES

TOKENS = r"F:\python_work\逆向\tools\out\textutil_vals.json"
ROOT = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
FILES = ["MasterData/ad_reward.data", "MasterData/assist.data",
         "tutorial.data", "notification.data"]


def load():
    vals = json.load(open(TOKENS, encoding="utf-8"))
    if isinstance(vals, dict):
        vals = list(vals.values())
    vals = sorted({v for v in vals if isinstance(v, str) and v})
    cts = []
    for f in FILES:
        p = os.path.join(ROOT, f.replace("/", os.sep))
        if not os.path.exists(p):
            continue
        raw = base64.b64decode(open(p, "rb").read().strip())
        if len(raw) < 32 or len(raw) % 16:
            continue
        cts.append((f, raw[-16:], raw[-32:-16]))
    return vals, cts


def check_one(args):
    """args = (pass_str, salt_str, cts)"""
    p, s, cts = args
    blob = hashlib.pbkdf2_hmac("sha1", p.encode(), s.encode(), 1000, 48)
    key, iv = blob[:32], blob[32:48]
    cipher = AES.new(key, AES.MODE_ECB)
    for name, clast, cprev in cts:
        x = bytes(a ^ b for a, b in zip(cipher.decrypt(clast), cprev))
        n = x[-1]
        if n < 1 or n > 16 or x[-n:] != bytes([n]) * n:
            return None
    # 全部通过末块校验 -> 全解一次做二次确认
    out = []
    for name, clast, cprev in cts:
        d = AES.new(key, AES.MODE_CBC, iv)
        raw = base64.b64decode(open(os.path.join(ROOT, name.replace("/", os.sep)), "rb").read().strip())
        pt = d.decrypt(raw)
        out.append((name, pt))
    ok = sum(1 for _, pt in out if pt[:1] in (b"{", b"["))
    if ok >= max(1, len(out) - 1):
        return (p, s, key.hex(), iv.hex(), [(n, pt[:80]) for n, pt in out])
    return None


def main():
    vals, cts = load()
    print(f"[+] tokens={len(vals)} files={len(cts)}", flush=True)
    jobs = []
    for a, b in itertools.permutations(vals, 2):
        jobs.append((a + b, "", cts))
    for a, b in itertools.permutations(vals, 2):
        for s in vals:
            jobs.append((a + b, s, cts))
    print(f"[+] jobs={len(jobs)}", flush=True)
    hits = 0
    with Pool(processes=min(12, os.cpu_count() or 4)) as pool:
        for i, r in enumerate(pool.imap_unordered(check_one, jobs, chunksize=64)):
            if r:
                hits += 1
                print("[HIT]", r, flush=True)
                with open(r"F:\python_work\逆向\tools\out\tu_hits.txt", "a", encoding="utf-8") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
            if i % 50000 == 0:
                print(f"  ...{i}/{len(jobs)} hits={hits}", flush=True)
    print(f"[=] done hits={hits}", flush=True)


if __name__ == "__main__":
    main()
