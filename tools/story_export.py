# -*- coding: utf-8 -*-
"""导出 Utage 剧情书（AdvImportBook）里的场景网格到文本。

bundle 里 *.book 是 Wonder.Story.AdvImportBook（Utage 的导入数据）：
  importGridList: List<AdvImportScenarioSheet>，每个含 name + StringGrid(rows: List<StringGridRow>)
  StringGridRow.strings 就是 Excel 行：Command / Arg1 / Arg2 / ... 与台词列

用法: python tools/story_export.py [outdir]
"""
import csv
import os
import sys

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.21f1"
CSV = r"F:\python_work\逆向\tools\out\bundles.csv"
BASE = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"


def get(obj, name, default=None):
    try:
        return obj.__dict__[name]
    except Exception:
        try:
            return getattr(obj, name)
        except Exception:
            return default


def rows_to_grid(grid):
    out = []
    for r in get(grid, "rows", []) or []:
        out.append([str(s) for s in (get(r, "strings", []) or [])])
    return out


def main():
    outdir = sys.argv[1] if len(sys.argv) > 1 else r"F:\python_work\逆向\out\story"
    os.makedirs(outdir, exist_ok=True)
    books = [r for r in csv.DictReader(open(CSV, encoding="utf-8-sig"))
             if r["name"].endswith(".book")]
    seen = set()
    index = []
    for rec in books:
        path = os.path.join(BASE, rec["file"])
        key = (path, rec["name"])
        if key in seen:
            continue
        seen.add(key)
        env = UnityPy.load(path)
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour" or obj.peek_name() != rec["name"]:
                continue
            data = obj.read()
            sheets = get(data, "importGridList", []) or []
            lines = [f"# {rec['name']}  (bundle {rec['cab']})", ""]
            total_rows = 0
            for sh in sheets:
                sname = get(sh, "name", "") or ""
                grid = get(sh, "grid", None) or get(sh, "sheet", None)
                if grid is None:
                    # AdvImportScenarioSheet 自身可能直接带 rows
                    grid = sh
                rows = rows_to_grid(grid)
                if not rows:
                    continue
                lines.append(f"## sheet: {sname}   rows={len(rows)}")
                total_rows += len(rows)
                for r in rows:
                    lines.append(" | ".join(r))
                lines.append("")
            fn = os.path.join(outdir, rec["name"].replace(".", "_") + ".txt")
            with open(fn, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            index.append((rec["name"], rec["cab"], len(sheets), total_rows, os.path.basename(fn)))
            print(f"[+] {rec['name']:22s} sheets={len(sheets)} rows={total_rows}")
    with open(os.path.join(outdir, "_index.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["book", "bundle", "sheets", "rows", "file"])
        w.writerows(index)
    print(f"[+] 共 {len(index)} 本 -> {outdir}")


if __name__ == "__main__":
    main()
