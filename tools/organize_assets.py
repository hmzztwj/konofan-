# -*- coding: utf-8 -*-
"""把 out/assets 里导出的 21,790 张图，按原始容器路径归类到 out/assets_sorted/ 下。

文件名形如 <h1>_<h2>_<Type>_<Name>.png，其中 h1/h2 就是 UnityCache\Shared\<h1>\<h2> 两个目录 hash，
用 (h1,h2) 反查 tools/out/bundles.csv 的 CONTAINER 行，取 Unity 工程里的真实路径做分类目录。
用硬链接（同盘）而不是复制，省空间时间；失败回退复制。
"""
import collections
import csv
import os
import shutil

SRC = r"F:\python_work\逆向\out\assets"
DST = r"F:\python_work\逆向\out\assets_sorted"
CSV = r"F:\python_work\逆向\tools\out\bundles.csv"


def classify(container):
    seg = container.split("/")
    for i, s in enumerate(seg):
        if s == "UnityAssets":
            rest = [x for x in seg[i + 1:i + 4] if x]
            return "/".join(rest) if rest else "UnityAssets"
        if s in ("Creative", "Cri"):
            rest = [x for x in seg[i + 1:i + 3] if x]
            return s + ("/" + "/".join(rest) if rest else "")
    return "zz_other/" + (seg[2] if len(seg) > 3 else "root")


def main():
    os.makedirs(DST, exist_ok=True)
    containers = collections.defaultdict(list)
    with open(CSV, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["type"] != "CONTAINER":
                continue
            parts = row["file"].split("\\")
            # UnityCache\Shared\<h1>\<h2>\__data
            if len(parts) >= 5:
                containers[(parts[2], parts[3])].append(row["name"])

    stats = collections.Counter()
    no_container = 0
    files = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".png"))
    print(f"[+] {len(files)} 个 png，容器索引 {len(containers)} 个 bundle", flush=True)

    for idx, fname in enumerate(files):
        parts = fname.split("_")
        paths = containers.get((parts[0], parts[1])) if len(parts) >= 3 else None
        if not paths:
            no_container += 1
            cat = "zz_unclassified"
        else:
            p = next((q for q in paths if q.lower().endswith((".png", ".tga"))), paths[0])
            cat = classify(p)
        outdir = os.path.join(DST, cat)
        os.makedirs(outdir, exist_ok=True)
        dst = os.path.join(outdir, fname)
        if not os.path.exists(dst):
            try:
                os.link(os.path.join(SRC, fname), dst)
            except OSError:
                shutil.copy2(os.path.join(SRC, fname), dst)
        stats[cat] += 1
        if idx and idx % 4000 == 0:
            print(f"  ...{idx}/{len(files)}", flush=True)

    print(f"[+] 无容器信息的文件: {no_container}")
    print(f"[+] 分类结果（{len(stats)} 个目录）:")
    for c, n in stats.most_common(40):
        print(f"    {n:6d}  {c}")
    print(f"[=] 已归类 {sum(stats.values())} 个文件 -> {DST}")

    with open(os.path.join(DST, "_分类统计.txt"), "w", encoding="utf-8") as f:
        for c, n in stats.most_common():
            f.write(f"{n:6d}\t{c}\n")


if __name__ == "__main__":
    main()
