# -*- coding: utf-8 -*-
"""把已缓存 bundle 里的 Utage 剧情书渲染成人可读的对话脚本。

数据来源：bundle 内 AdvImportBook.importGridList（每个 sheet 是 Excel 网格）。
列名见第 0 行：Command / Arg1 / Arg2 / Text / Voice / PageCtrl / WaitType ...

产物: out/story/<book>.md
"""
import csv
import os
import re

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.21f1"
BASE = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"
CSVIN = r"F:\python_work\逆向\tools\out\bundles.csv"
OUT = r"F:\python_work\逆向\out\story"


def g(o, k, d=None):
    try:
        return o.__dict__[k]
    except Exception:
        return getattr(o, k, d)


def grid(gridobj):
    for r in g(gridobj, "rows", []) or []:
        yield [str(s) for s in (g(r, "strings", []) or [])]


def render_book(name, sheets):
    lines = [f"# {name}", ""]
    for sname, rows in sheets:
        if not rows:
            continue
        header = rows[0]
        idx = {}
        for i, h in enumerate(header):
            h = h.strip()
            if h and h not in idx:
                idx[h] = i
        i_cmd = idx.get("Command", 2)
        i_a1 = idx.get("Arg1", 3)
        i_txt = idx.get("Text", 13)
        i_voice = idx.get("Voice", idx.get("// CueId", 17))
        short = sname.split(":")[-1] if sname else "scenario"
        lines.append(f"## {short}")
        lines.append("")
        n_lines = 0
        for r in rows[1:]:
            if not r or (r[0].strip().startswith("//") and len(r) <= 2):
                continue
            cmd = r[i_cmd].strip() if len(r) > i_cmd else ""
            a1 = r[i_a1].strip() if len(r) > i_a1 else ""
            txt = r[i_txt].strip() if len(r) > i_txt else ""
            voice = r[i_voice].strip() if len(r) > i_voice else ""
            if not txt:
                continue
            n_lines += 1
            if cmd == "Character":
                who = a1 or "?"
                v = f"  <!-- {voice} -->" if voice else ""
                lines.append(f"**{who}**：「{txt}」{v}")
            elif cmd in ("StoryTitle", "Title"):
                lines.append(f"### 【{txt}】")
            else:
                lines.append(f"*[{cmd}] {txt}*")
            lines.append("")
        if n_lines == 0:
            lines.append("（本 sheet 没有台词）")
            lines.append("")
    return "\n".join(lines)


def main():
    os.makedirs(OUT, exist_ok=True)
    books = [r for r in csv.DictReader(open(CSVIN, encoding="utf-8-sig"))
             if r["name"].endswith(".book")]
    done = {}
    index = []
    for rec in books:
        path = os.path.join(BASE, rec["file"])
        env = UnityPy.load(path)
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour" or obj.peek_name() != rec["name"]:
                continue
            if rec["name"] in done:
                continue
            d = obj.read()
            sheets = []
            for sh in g(d, "importGridList", []) or []:
                sheets.append((g(sh, "name", "") or "", list(grid(sh))))
            if not any(rows for _, rows in sheets):
                continue
            md = render_book(rec["name"], sheets)
            fn = os.path.join(OUT, rec["name"].replace(".", "_") + ".md")
            with open(fn, "w", encoding="utf-8") as f:
                f.write(md)
            n = sum(1 for ln in md.splitlines() if ln.startswith("**"))
            index.append((rec["name"], rec["cab"], n, os.path.basename(fn)))
            done[rec["name"]] = True
            print(f"[+] {rec['name']:20s} 台词 {n:4d} 行 -> {os.path.basename(fn)}")
    with open(os.path.join(OUT, "_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["book", "bundle", "dialogue_lines", "file"])
        w.writerows(index)
    print(f"[+] {len(index)} 本有内容")


if __name__ == "__main__":
    main()
