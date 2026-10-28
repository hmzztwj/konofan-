#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Look up Il2CppDumper script.json: map address -> literal string / method name."""
import json, sys, os

BASE = r"F:\python_work\逆向\tools\il2cppdumper\out570"
CACHE = os.path.join(BASE, "..", "lookup_cache.json")


def build():
    with open(os.path.join(BASE, "script.json"), encoding="utf-8") as f:
        d = json.load(f)
    strs = {e["Address"]: e["Value"] for e in d.get("ScriptString", [])}
    meths = {e["Address"]: e["Name"] for e in d.get("ScriptMethod", [])}
    meta = {e["Address"]: e for e in d.get("ScriptMetadata", [])}
    metam = {e["Address"]: e for e in d.get("ScriptMetadataMethod", [])}
    json.dump({"strs": strs, "meths": meths,
               "meta_keys": list(meta)[:5],
               "metam": {k: v for k, v in list(metam.items())[:5]}},
              open(CACHE, "w", encoding="utf-8"))
    return strs, meths


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "build":
        s, m = build()
        print("strings", len(s), "methods", len(m))
    else:
        d = json.load(open(CACHE, encoding="utf-8"))
        strs, meths = d["strs"], d["meths"]
        for a in sys.argv[2:]:
            v = int(a, 16)
            print("%s  meth=%s  str=%r" % (a, meths.get(v), strs.get(v)))
