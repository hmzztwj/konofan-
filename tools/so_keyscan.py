#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
so_keyscan.py -- 从 libil2cpp.so 中暴力搜索 MasterData 的 AES 密钥。

原理（不依赖 metadata 版本匹配）：
  * 已知 .data 是 CBC 类分组密码，最后一块解密后必须满足 PKCS#7 填充（或零填充）；
  * 该条件只需要「密钥」，不需要 IV —— 因为 P_last = D(C_last) ^ C_{prev}；
  * 把 .so 里每一个 8 字节对齐窗口（16/32 字节）当作候选密钥，用两个不同
    文件同时通过填充检查来压掉误报，再做明文可打印性 / JSON 校验。

用法:
  python tools/so_keyscan.py <libil2cpp.so> <file_a.data> <file_b.data> [...]
"""
import sys, os, base64, json, struct, time

from Crypto.Cipher import AES

DATA_DIR = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data\MasterData"


def load_data(path):
    with open(path, "rb") as f:
        raw = f.read()
    raw = raw.strip()
    return base64.b64decode(raw)


def elf_segments(path):
    """返回 [(file_offset, size, flags), ...]，只取 PT_LOAD。"""
    with open(path, "rb") as f:
        hdr = f.read(64)
        if hdr[:4] != b"\x7fELF":
            raise SystemExit("not an ELF")
        ei_class = hdr[4]
        if ei_class != 2:
            raise SystemExit("expect ELF64")
        e_phoff = struct.unpack_from("<Q", hdr, 0x20)[0]
        e_phentsize = struct.unpack_from("<H", hdr, 0x36)[0]
        e_phnum = struct.unpack_from("<H", hdr, 0x38)[0]
        segs = []
        f.seek(e_phoff)
        ph = f.read(e_phentsize * e_phnum)
        for i in range(e_phnum):
            off = i * e_phentsize
            p_type = struct.unpack_from("<I", ph, off)[0]
            if p_type != 1:  # PT_LOAD
                continue
            p_flags = struct.unpack_from("<I", ph, off + 4)[0]
            p_offset = struct.unpack_from("<Q", ph, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", ph, off + 32)[0]
            if p_filesz:
                segs.append((p_offset, p_filesz, p_flags))
        return segs


def pad_ok(block):
    """PKCS#7 或零填充的宽松判定。"""
    b = block[-1]
    if 1 <= b <= 16:
        if block[-b:] == bytes([b]) * b:
            return True
    # 零填充：末尾至少 1 个 0x00
    if block[-1] == 0 and block[-2] == 0:
        return True
    return False


def decrypt_blocks(key, ct, start_block, nblocks):
    """用 ECB 实现 CBC 解密（IV 无关），返回从 start_block 起的明文块。"""
    aes = AES.new(key, AES.MODE_ECB)
    out = bytearray()
    for i in range(start_block, start_block + nblocks):
        if i == 0:
            return None  # 需要 IV，跳过
        d = aes.decrypt(ct[i * 16:(i + 1) * 16])
        prev = ct[(i - 1) * 16:i * 16]
        out += bytes(x ^ y for x, y in zip(d, prev))
    return bytes(out)


def main():
    so_path = sys.argv[1]
    files = sys.argv[2:] or [
        os.path.join(DATA_DIR, "ad_reward.data"),
        os.path.join(DATA_DIR, "assist.data"),
    ]
    blobs = [load_data(p) for p in files]
    for p, b in zip(files, blobs):
        print(f"[in] {os.path.basename(p):34s} {len(b):>9,} B  blocks={len(b)//16}")

    # 预取每份密文的最后两块
    tails = []
    for b in blobs:
        n = len(b) // 16
        tails.append((b[(n - 1) * 16:n * 16], b[(n - 2) * 16:(n - 1) * 16]))

    segs = elf_segments(so_path)
    total = sum(s for _, s, _ in segs)
    print(f"[elf] segments={len(segs)} loadable={total:,} B")

    t0 = time.time()
    hits = []
    scanned = 0
    with open(so_path, "rb") as f:
        for (off, size, flags) in segs:
            f.seek(off)
            buf = f.read(size)
            for klen in (16, 32):
                limit = len(buf) - klen
                for i in range(0, limit, 8):
                    key = buf[i:i + klen]
                    ok = True
                    for (clast, cprev) in tails:
                        aes = AES.new(key, AES.MODE_ECB)
                        p = bytes(x ^ y for x, y in zip(aes.decrypt(clast), cprev))
                        if not pad_ok(p):
                            ok = False
                            break
                    if ok:
                        hits.append((off + i, bytes(key)))
                    scanned += 1
            print(f"  seg off=0x{off:x} size={size:,} scanned={scanned:,} hits={len(hits)} "
                  f"{time.time()-t0:.1f}s", flush=True)

    print(f"[stage1] candidates={len(hits)} in {time.time()-t0:.1f}s")
    if not hits:
        print("NO KEY FOUND (padding oracle)")
        return

    # stage2: 用第一份文件解密前 64 块，看可打印比例
    ct0 = blobs[0]
    n0 = len(ct0) // 16
    good = []
    for (addr, key) in hits:
        try:
            pt = decrypt_blocks(key, ct0, 1, min(64, n0 - 1))
        except Exception:
            continue
        if not pt:
            continue
        printable = sum(1 for c in pt if 32 <= c < 127 or c in (9, 10, 13))
        ratio = printable / len(pt)
        if ratio > 0.80:
            good.append((addr, key, ratio, pt[:120]))
    print(f"[stage2] printable-candidates={len(good)}")
    for (addr, key, ratio, head) in good[:40]:
        print(f"  0x{addr:08x} klen={len(key)} ratio={ratio:.2f} key={key.hex()} head={head!r}")

    # stage3: 完整解密 + 找 IV
    for (addr, key, ratio, head) in good[:40]:
        ivs = [b"\x00" * 16, key[:16], (key * 2)[:16]]
        for ivname, iv in zip(("zero", "key[:16]", "key*2"), ivs):
            aes = AES.new(key, AES.MODE_CBC, iv)
            try:
                pt = aes.decrypt(ct0)
            except Exception:
                continue
            body = pt.rstrip(b"\x00")
            try:
                txt = body.decode("utf-8")
            except UnicodeDecodeError:
                continue
            if txt.lstrip()[:1] in ("{", "["):
                print(f"\n*** KEY HIT addr=0x{addr:x} iv={ivname} key={key.hex()} ***")
                print(txt[:400])
                with open(os.path.join(os.path.dirname(__file__), "out", "key_found.txt"), "w",
                          encoding="utf-8") as fp:
                    fp.write(f"addr=0x{addr:x}\nkey={key.hex()}\niv={ivname}:{iv.hex()}\n\n{txt[:2000]}")
                return
    print("no full-plaintext confirmation yet")


if __name__ == "__main__":
    main()
