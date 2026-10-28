# -*- coding: utf-8 -*-
"""看看已缓存 bundle 里的 Utage 剧情资产（*.chapter.asset）长什么样、能不能读出正文。

用法: python tools/story_probe.py
"""
import os
import re

import UnityPy

UnityPy.config.FALLBACK_UNITY_VERSION = "2022.3.21f1"
BASE = r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\UnityCache\Shared"
TARGETS = [
    r"31f15d27e82cb81bf6a7f31155a4885f\1532ab24a0f44aca3af1907fd5b377b9\__data",
    r"cd006ca873ae45c4c6542c79c0de35f6\d9b59dd0b95d5cd266f1f2a8dd1cf3f5\__data",
]


def dump_obj(obj, depth=0, seen=None):
    seen = seen or set()
    pad = "  " * depth
    try:
        data = obj.read()
    except Exception as e:
        print(pad, "read fail", e)
        return
    for k in dir(data):
        if k.startswith("_") or k in ("assets_file", "object_reader", "assets", "peek_name"):
            continue
        try:
            v = getattr(data, k)
        except Exception:
            continue
        if callable(v):
            continue
        s = repr(v)
        if len(s) > 200:
            s = s[:200] + "..."
        print(f"{pad}{k} = {s}")


def main():
    for rel in TARGETS:
        p = os.path.join(BASE, rel)
        print("=" * 70)
        print(p)
        env = UnityPy.load(p)
        for obj in env.objects:
            print(f"-- {obj.type.name} path_id={obj.path_id} name={obj.peek_name()}")
            if obj.type.name == "MonoBehaviour":
                dump_obj(obj)
            elif obj.type.name == "TextAsset":
                d = obj.read()
                body = getattr(d, "m_Script", "") or ""
                print("   text head:", repr(body[:300]))


if __name__ == "__main__":
    main()
