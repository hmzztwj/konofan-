# -*- coding: utf-8 -*-
"""Inventory every cached UnityFS bundle: objects (class, name), containers, dependencies, CAB name."""
import os, sys, csv, traceback
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.21f1'

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
cache = os.path.join(root, 'UnityCache', 'Shared')
outdir = r'F:\python_work\逆向\tools\out'
os.makedirs(outdir, exist_ok=True)

paths = []
for d in os.listdir(cache):
    sub = os.path.join(cache, d)
    if not os.path.isdir(sub):
        continue
    for d2 in os.listdir(sub):
        p = os.path.join(sub, d2, '__data')
        if os.path.isfile(p):
            paths.append(p)
print('bundle files:', len(paths), flush=True)

rows = []
errs = 0
for i, p in enumerate(paths):
    rel = os.path.relpath(p, root)
    size = os.path.getsize(p)
    try:
        env = UnityPy.load(p)
        cab = ''
        deps = ''
        objs = []
        for obj in env.objects:
            t = obj.type.name
            try:
                nm = obj.peek_name() or ''
            except Exception:
                nm = ''
            if t == 'AssetBundle':
                try:
                    ab = obj.read()
                    cab = ab.m_Name
                    deps = ';'.join(ab.m_Dependencies or [])
                except Exception:
                    pass
            objs.append((obj.path_id, t, nm))
        conts = []
        for cpath, obj in env.container.items():
            conts.append((cpath, obj.path_id))
        for path_id, t, nm in objs:
            rows.append([rel, size, cab, deps, path_id, t, nm, ''])
        for cpath, pid in conts:
            rows.append([rel, size, cab, deps, pid, 'CONTAINER', cpath, ''])
    except Exception as e:
        errs += 1
        rows.append([rel, size, '', '', '', 'ERROR', repr(e), ''])
    if i % 100 == 0:
        print(i, rel, flush=True)

with open(os.path.join(outdir, 'bundles.csv'), 'w', newline='', encoding='utf-8-sig') as fh:
    w = csv.writer(fh)
    w.writerow(['file', 'size', 'cab', 'deps', 'path_id', 'type', 'name', 'extra'])
    w.writerows(rows)
print('done rows=%d errors=%d' % (len(rows), errs), flush=True)
