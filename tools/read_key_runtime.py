"""从运行中的 Unity/L2CPP 进程里，直接读出 AesEncryption 的静态 Key / Iv 数组。

原理（都来自静态逆向的结论）：
  libil2cpp.so 的 metadata usage 槽 0x6850940 运行时存放 AesEncryption 的 Il2CppClass*
  Il2CppClass->static_fields 在 +0xB8
  static_fields[0x0] = byte[] Key, static_fields[0x8] = byte[] Iv
  Il2CppArray 布局: obj(klass,monitor)=0x00..0x10, bounds=0x10, max_length=0x18, data=0x20

用法: python tools/read_key_runtime.py [VA槽地址] [--key-off 0] [--key-off 8]
"""
import os
import re
import subprocess
import sys

ADB = r"F:\android-sdk\platform-tools\adb.exe"
DEV = "127.0.0.1:16384"
PKG = "jp.co.sumzap.pj0007"
SO = "libil2cpp.so"
CLASS_SLOT = 0x6850940   # AesEncryption_TypeInfo usage slot
STATIC_FIELDS_OFF = 0xB8
ARRAY_LEN_OFF = 0x18
ARRAY_DATA_OFF = 0x20


def sh(cmd, timeout=60):
    p = subprocess.run([ADB, "-s", DEV, "shell", cmd], capture_output=True, timeout=timeout)
    return p.stdout.decode("utf-8", "ignore"), p.stderr.decode("utf-8", "ignore")


def rmem(pid, addr, n):
    cmd = (f"dd if=/proc/{pid}/mem bs={n} iflag=skip_bytes,count_bytes "
           f"skip={addr} count={n} 2>/dev/null | od -An -tx1 | tr -d ' \\n'")
    out, err = sh(cmd)
    hx = "".join(out.split())
    if len(hx) < n * 2:
        return None
    return bytes.fromhex(hx[:n * 2])


def u64(b):
    return int.from_bytes(b, "little")


def main():
    slot = int(sys.argv[1], 16) if len(sys.argv) > 1 and sys.argv[1].startswith("0x") else CLASS_SLOT
    pid = sh(f"pidof {PKG}")[0].strip().split()[0]
    print(f"[+] pid={pid}")

    maps, _ = sh(f"cat /proc/{pid}/maps")
    segs = []
    for line in maps.splitlines():
        m = re.match(r"([0-9a-f]+)-([0-9a-f]+)\s+(\S{4})\s+([0-9a-f]+)\s+\S+\s+\S+\s*(.*)", line)
        if not m:
            continue
        start, end, perm, off, name = (int(m.group(1), 16), int(m.group(2), 16),
                                       m.group(3), int(m.group(4), 16), m.group(5).strip())
        if SO in name:
            segs.append((start, end, perm, off, name))
    if not segs:
        print("[-] 没有找到", SO, "的映射")
        return 1
    base = min(s - o for s, e, p, o, n in segs)
    print(f"[+] {SO} 映射基址 = {base:#x}，段数 {len(segs)}")

    def map_va(va):
        a = base + va
        for s, e, p, o, n in segs:
            if s <= a < e:
                return a
        return None

    addr = map_va(slot)
    print(f"[+] 槽 {slot:#x} -> 运行时 {addr:#x}")
    raw = rmem(pid, addr, 8)
    print(f"    原始 8 字节 = {raw.hex() if raw else None}")
    cls = u64(raw)
    print(f"[+] Il2CppClass* = {cls:#x}")
    if not (0x1000 < cls < 0x7fff_ffff_ffff):
        print("[-] 指针不合理，槽里可能还是未解析的编码值")
        return 1

    sf = u64(rmem(pid, cls + STATIC_FIELDS_OFF, 8))
    print(f"[+] static_fields = {sf:#x}")

    for label, off in (("Key", 0x0), ("Iv", 0x8)):
        arr = u64(rmem(pid, sf + off, 8))
        if not (0x1000 < arr < 0x7fff_ffff_ffff):
            print(f"[-] {label} 数组指针无效: {arr:#x}（可能还没初始化）")
            continue
        ln = u64(rmem(pid, arr + ARRAY_LEN_OFF, 8))
        data = rmem(pid, arr + ARRAY_DATA_OFF, max(1, ln))
        print(f"[+] {label}: len={ln} bytes={data.hex() if data else None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
