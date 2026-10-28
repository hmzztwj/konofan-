"""从运行中的进程读出 CodeStage Anti-Cheat Toolkit 的 ObscuredString 明文。

ObscuredString 字段（dump.cs:1097969）：
  +0x00 klass / +0x08 monitor
  +0x10 string currentCryptoKey
  +0x18 byte[] hiddenValue
  +0x20 bool   inited
  +0x28 string fakeValue
  +0x30 bool   fakeValueActive

用法:
  python tools/read_obscured.py Sha            # 读 Wonder.Util.Crypt.ShaEncryption.Salt
  python tools/read_obscured.py TextUtil 0     # 读 TextUtil 的第 0 个 static 字段
"""
import json
import re
import subprocess
import sys

ADB = r"F:\android-sdk\platform-tools\adb.exe"
DEV = "127.0.0.1:16384"
PKG = "jp.co.sumzap.pj0007"
SO = "libil2cpp.so"
DUMP = r"F:\python_work\逆向\tools\il2cppdumper\out570\script.json"

CLASS_SLOT = {
    "Sha": "Wonder.Util.Crypt.ShaEncryption_TypeInfo",
    "Aes": "Wonder.Util.Crypt.AesEncryption_TypeInfo",
    "TextUtil": "Wonder.Util.TextUtil_TypeInfo",
}


def sh(cmd, timeout=60):
    p = subprocess.run([ADB, "-s", DEV, "shell", cmd], capture_output=True, timeout=timeout)
    return p.stdout.decode("utf-8", "ignore")


def rmem(pid, addr, n):
    cmd = (f"dd if=/proc/{pid}/mem bs={n} iflag=skip_bytes,count_bytes "
           f"skip={addr} count={n} 2>/dev/null | od -An -tx1 | tr -d ' \\n'")
    hx = "".join(sh(cmd).split())
    if len(hx) < n * 2:
        return None
    return bytes.fromhex(hx[:n * 2])


def u64(b):
    return int.from_bytes(b, "little")


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "Sha"
    field_idx = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    target = CLASS_SLOT[which]

    d = json.load(open(DUMP, encoding="utf-8"))
    slot = None
    for e in d["ScriptMetadata"]:
        if e["Name"] == target:
            slot = e["Address"]
            break
    if slot is None:
        print("[-] 找不到", target)
        return 1
    print(f"[+] {target} 槽 = {slot:#x}")

    pid = sh(f"pidof {PKG}").strip().split()[0]
    maps = sh(f"cat /proc/{pid}/maps")
    segs = []
    for line in maps.splitlines():
        m = re.match(r"([0-9a-f]+)-([0-9a-f]+)\s+\S{4}\s+([0-9a-f]+)\s+\S+\s+\S+\s*(.*)", line)
        if m and SO in m.group(4):
            segs.append((int(m.group(1), 16), int(m.group(2), 16), int(m.group(3), 16)))
    base = min(s - o for s, e, o in segs)
    va = base + slot
    print(f"[+] {SO} base={base:#x} -> 槽运行时 {va:#x}")

    cls = u64(rmem(pid, va, 8))
    sf = u64(rmem(pid, cls + 0xB8, 8))
    print(f"[+] class={cls:#x} static_fields={sf:#x}")

    obj = u64(rmem(pid, sf + field_idx * 8, 8))
    print(f"[+] 字段[{field_idx}] 对象 = {obj:#x}")
    if not (0x1000 < obj < 0x7fff_ffff_ffff):
        return 1

    def read_string(p):
        ln = int.from_bytes(rmem(pid, p + 0x10, 4), "little")
        if not (0 < ln < 4096):
            return None
        raw = rmem(pid, p + 0x14, ln * 2)
        return raw.decode("utf-16-le", "replace")

    ck = u64(rmem(pid, obj + 0x10, 8))
    hv = u64(rmem(pid, obj + 0x18, 8))
    print(f"[+] currentCryptoKey ptr={ck:#x} hiddenValue ptr={hv:#x}")
    if 0x1000 < ck < 0x7fff_ffff_ffff:
        print(f"    currentCryptoKey = {read_string(ck)!r}")
    if 0x1000 < hv < 0x7fff_ffff_ffff:
        ln = u64(rmem(pid, hv + 0x18, 8))
        data = rmem(pid, hv + 0x20, ln)
        print(f"    hiddenValue len={ln} hex={data.hex()}")
        # 尝试常见解码
        for name, enc in (("utf-16-le", "utf-16-le"), ("utf-8", "utf-8")):
            try:
                print(f"    as {name}: {data.decode(enc)!r}")
            except Exception:
                pass
    fake = u64(rmem(pid, obj + 0x28, 8))
    act = rmem(pid, obj + 0x30, 1)
    if 0x1000 < fake < 0x7fff_ffff_ffff:
        print(f"    fakeValue(明文) = {read_string(fake)!r}  fakeValueActive={act.hex() if act else None}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
