# -*- coding: utf-8 -*-
"""看 Utage 剧情资产里的 settingList（角色设定表：CharacterId -> CharacterName/NameText）。"""
import csv
import os

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.21f1"
BASE = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files"


def g(o, k, d=None):
    try:
        return o.__dict__[k]
    except Exception:
        return getattr(o, k, d)


def grid_rows(grid):
    out = []
    for r in g(grid, "rows", []) or []:
        out.append([str(s) for s in (g(r, "strings", []) or [])])
    return out


def main():
    for rel in [
        r"31f15d27e82cb81bf6a7f31155a4885f\1532ab24a0f44aca3af1907fd5b377b9\__data",
        r"e1261ade46c67382010a3b2f36b4cae8\a92ff2141ddfb6162dbbcd62a740df1d\__data",
    ]:
        env = UnityPy.load(os.path.join(BASE, rel))
        for obj in env.objects:
            if obj.type.name != "MonoBehaviour":
                continue
            d = obj.read()
            sl = g(d, "settingList", None)
            if not sl:
                continue
            print("=" * 60)
            print(g(d, "m_Name"))
            for s in sl:
                rows = grid_rows(s)
                print("  sheet:", g(s, "name"), "rows", len(rows))
                for r in rows[:14]:
                    print("   ", " | ".join(r))


if __name__ == "__main__":
    main()
