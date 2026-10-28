"""从模拟器（root + adb）dump 指定包名的进程内存。

用法:
    python tools/dump_mem.py <package> [outdir]

流程:
  1. adb shell pidof <package> 找 pid（可多进程，取主进程）
  2. 读 /proc/<pid>/maps，挑选 rw-p 匿名/堆 区域（跳过 so/dex/字体/视频等文件映射）
  3. 对每个区域用 dd if=/proc/<pid>/mem skip=<addr> count=<size> 导出
  4. 全部保存到 outdir/<name>_<addr>.bin，并写 manifest.json
依赖: F:\\android-sdk\\platform-tools\\adb.exe，设备已 adb root
"""
import json
import os
import re
import subprocess
import sys

ADB = r"F:\android-sdk\platform-tools\adb.exe"


def sh(cmd, timeout=120):
    p = subprocess.run([ADB, "shell", cmd], capture_output=True, timeout=timeout)
    return p.returncode, p.stdout.decode("utf-8", "ignore"), p.stderr.decode("utf-8", "ignore")


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else "jp.co.sumzap.pj0007"
    outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), "out", "mem")
    os.makedirs(outdir, exist_ok=True)

    rc, out, err = sh(f"pidof {pkg}")
    pids = out.split()
    if not pids:
        print("[-] 进程不存在，先启动游戏:", pkg, err)
        return 1
    pid = pids[0]
    print(f"[+] pid={pid} (all={pids})")

    rc, maps, err = sh(f"cat /proc/{pid}/maps")
    if not maps.strip():
        print("[-] 读不到 maps，adbd 可能不是 root:", err)
        return 1

    regions = []
    for line in maps.splitlines():
        m = re.match(r"([0-9a-f]+)-([0-9a-f]+)\s+(\S{4})\s+\S+\s+\S+\s+\S+\s*(.*)$", line)
        if not m:
            continue
        start, end, perm, name = int(m.group(1), 16), int(m.group(2), 16), m.group(3), m.group(4).strip()
        if "r" not in perm or "w" not in perm:
            continue
        # 只保留匿名映射 + [heap] + [anon:*] + /dev/ashmem，跳过 so/dex/apk/字体
        if name and not (name.startswith("[") or "ashmem" in name or "dalvik" in name or "app_" in name):
            continue
        size = end - start
        if size < 4096 or size > 512 * 1024 * 1024:
            continue
        regions.append((start, size, perm, name))

    regions.sort()
    print(f"[+] 候选 rw 区域 {len(regions)} 个，合计 {sum(r[1] for r in regions)/1048576:.1f} MB")

    manifest = []
    for start, size, perm, name in regions:
        safe = re.sub(r"[^A-Za-z0-9]+", "_", name)[:24] or "anon"
        fn = f"{safe}_{start:012x}.bin"
        rc, out, err = sh(
            f"dd if=/proc/{pid}/mem of=/sdcard/{fn} bs=1048576 "
            f"iflag=skip_bytes,count_bytes skip={start} count={size} 2>&1 | tail -1",
            timeout=300,
        )
        if "error" in out.lower() or "denied" in out.lower():
            print(f"    ! {start:#x} {size} {name}: {out.strip()}")
            continue
        subprocess.run([ADB, "pull", f"/sdcard/{fn}", os.path.join(outdir, fn)],
                       capture_output=True, timeout=600)
        sh(f"rm -f /sdcard/{fn}")
        local = os.path.join(outdir, fn)
        real = os.path.getsize(local) if os.path.exists(local) else 0
        manifest.append({"start": start, "size": size, "perm": perm, "name": name,
                         "file": fn, "bytes": real})
        print(f"    + {start:#x} {size/1048576:.2f}MB {name or '[anon]'} -> {real/1048576:.2f}MB")

    with open(os.path.join(outdir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"package": pkg, "pid": pid, "regions": manifest}, f, ensure_ascii=False, indent=1)
    total = sum(r["bytes"] for r in manifest)
    print(f"[+] 完成: {len(manifest)} 个区域, {total/1048576:.1f} MB -> {outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
