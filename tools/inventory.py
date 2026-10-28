# -*- coding: utf-8 -*-
"""从 Addressables catalog + 本地 bundle 清单整理游戏内容清单（不涉及解密）。

产出:
  out/inventory.md   人读的分类统计
  out/inventory_assets.csv  每条资产: path, category, ext, in_local_bundle
"""
import collections
import csv
import json
import os

ROOT = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"
OUT = r"F:\python_work\逆向\out"
BUNDLES_CSV = r"F:\python_work\逆向\tools\out\bundles.csv"


def category(path):
    p = path.lower()
    seg = path.split("/")
    if "/cri/usm" in p:
        sub = seg[4] if len(seg) > 5 else ""
        return f"CRI 视频 · {sub}"
    if "/cri/cpk" in p:
        sub = "/".join(seg[4:6]) if len(seg) > 6 else ""
        return f"CRI 音频 · {sub}"
    if "creative/battle" in p:
        return "战斗特效/演出（Creative）"
    if "/test/dataservice/json" in p:
        return "API 响应样例（Test/DataService）"
    if "srdebugger" in p:
        return "调试面板（SRDebugger）"
    for key, name in (
        ("/common/introduction", "通用 · 介绍动画(Introduction)"),
        ("/unityassets/common/images", "通用 · 图片(Images)"),
        ("/unityassets/common", "通用 · 其他(Common)"),
        ("/unityassets/story", "剧情 · 资源(Story)"),
        ("/unityassets/battle", "战斗 · 资源(Battle)"),
        ("/unityassets/outgame", "大厅/UI · 资源(OutGame)"),
        ("/unityassets/tutorial", "新手引导 · 资源(Tutorial)"),
    ):
        if key in p:
            return name
    return "其他"


def main():
    os.makedirs(OUT, exist_ok=True)
    cat = json.load(open(os.path.join(ROOT, "com.unity.addressables", "catalog_stable.json"), encoding="utf-8"))
    ids = cat["m_InternalIds"]

    assets, bundles = [], []
    for s in ids:
        (bundles if s.startswith("{") and s.endswith(".bundle") else assets).append(s)
    assets = sorted(set(assets))
    bundles = sorted(set(bundles))

    # 本地 bundle 的容器路径
    local = set()
    cabmap = {}
    if os.path.exists(BUNDLES_CSV):
        with open(BUNDLES_CSV, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["type"] == "CONTAINER":
                    local.add(row["name"])
                    cabmap.setdefault(row["name"], set()).add(row["cab"])

    rows = []
    per_cat = collections.Counter()
    per_cat_local = collections.Counter()
    for a in assets:
        c = category(a)
        ext = os.path.splitext(a)[1].lower() or "(无)"
        hit = a in local
        per_cat[c] += 1
        if hit:
            per_cat_local[c] += 1
        rows.append({"path": a, "category": c, "ext": ext,
                     "in_local_bundle": "Y" if hit else "N",
                     "local_bundle": ",".join(sorted(cabmap.get(a, []))[:2])})

    with open(os.path.join(OUT, "inventory_assets.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["path", "category", "ext", "in_local_bundle", "local_bundle"])
        w.writeheader()
        w.writerows(rows)

    ext_counts = collections.Counter(r["ext"] for r in rows)
    bundle_ext = collections.Counter(os.path.splitext(b)[1] for b in bundles)

    lines = []
    lines.append("# 素晴（このファン）本地数据内容清单\n")
    lines.append(f"- 数据根：`{ROOT}`")
    lines.append(f"- catalog 里资产条目：**{len(assets):,}**；bundle 条目：**{len(bundles):,}**")
    lines.append(f"- 本地实际缓存的 bundle 容器（可按名寻址的资产）：**{len(local):,}**\n")
    lines.append("## 一、按内容分类（catalog 声明 vs 本地已缓存）\n")
    lines.append("| 分类 | catalog 条目 | 本地已缓存 | 覆盖率 |")
    lines.append("|---|---:|---:|---:|")
    for c, n in per_cat.most_common():
        l = per_cat_local.get(c, 0)
        lines.append(f"| {c} | {n:,} | {l:,} | {l*100.0/n:.1f}% |")
    lines.append("")
    lines.append("## 二、资产类型分布\n")
    lines.append("| 扩展名 | 数量 |")
    lines.append("|---|---:|")
    for e, n in ext_counts.most_common(20):
        lines.append(f"| `{e}` | {n:,} |")
    lines.append("")
    lines.append("## 三、CRI 媒体文件名（来自 catalog，可直接读）\n")
    cri = [a for a in assets if ".cpk.bytes" in a or ".usm.bytes" in a]
    lines.append(f"- CRI 媒体条目共 **{len(cri):,}** 条（`.cpk.bytes` + `.usm.bytes`）")
    pref = collections.Counter()
    for a in cri:
        b = os.path.basename(a)
        pref["".join(ch for ch in b if not ch.isdigit())[:24]] += 1
    lines.append("- 文件名前缀分布（前 15）：")
    for k, v in pref.most_common(15):
        lines.append(f"  - `{k}` → {v:,}")
    lines.append("")
    lines.append("## 三·补、CRI 媒体实体文件（磁盘上真实存在的）\n")
    n_cpk = n_usm = 0
    for sub, tag in (("Cpk", "cpk"), ("Usm", "usm")):
        d = os.path.join(ROOT, "bundles", "Cri", sub)
        if os.path.isdir(d):
            n = len([f for f in os.listdir(d) if f.lower().endswith("." + tag)])
            lines.append(f"- `{sub}`：**{n:,}** 个 `.{tag}` 文件")
            if tag == "cpk":
                n_cpk = n
            else:
                n_usm = n
    lines.append("- 这些文件名是 URL 编码的 base64，解出 32 字节（首字节恒为 `0xfb`），"
                 "**不是普通 hash**（sha256/md5/sha1 已全部验证不匹配），"
                 "属于 `ShaEncryption.EncryptStreamingAssetsNameString` 的加密命名，"
                 "因此无法与上面的 catalog 明文名逐条对齐（需同一把钥匙）。\n")
    lines.append("## 四、Spine 与剧情资源\n")
    spine = [r for r in rows if r["ext"] in (".atlas", ".skel", ".json")]
    lines.append(f"- catalog 里带扩展名的 `.atlas`/`.json`/`.skel` 条目：{len(spine):,}"
                 "（Spine 数据实际以**无扩展名的 TextAsset** 存放，本地 bundle 里有 1,004 个 TextAsset，"
                 "其中 12 个是 `<id>.atlas`，其余是 `<id>` 的 Spine JSON）")
    story = [r for r in rows if "剧情 · 资源" in r["category"]]
    story_ext = collections.Counter(r["ext"] for r in story)
    lines.append(f"- 剧情目录条目 {len(story):,}，类型：{dict(story_ext.most_common(8))}")
    lines.append("  - 其中 1,433 个 `.asset` 是 Utage ADV 的剧情数据（scenario），1,308 个 `.prefab` 是立绘/背景/演出预制体")
    lines.append("- 本地已缓存的剧情资产只有 196 条（7.1%）⇒ **主线/活动剧情文本大部分不在这份拷贝里**")
    lines.append("\n## 五、文件位置\n")
    lines.append("- 逐条明细：`out/inventory_assets.csv`")
    lines.append("- 本地 bundle 全量对象表（851,654 行）：`tools/out/bundles.csv`")

    md = os.path.join(OUT, "inventory.md")
    open(md, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print("\n".join(lines[:40]))
    print(f"\n[saved] {md}  ({len(rows)} rows)")


if __name__ == "__main__":
    main()
