# -*- coding: utf-8 -*-
"""Recon 2: understand UnityCache layout and file headers."""
import os, sys

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
sh = os.path.join(root, 'UnityCache', 'Shared')
entries = sorted(os.listdir(sh))
print('Shared entries:', len(entries))
dirs = [e for e in entries if os.path.isdir(os.path.join(sh, e))]
files = [e for e in entries if not os.path.isdir(os.path.join(sh, e))]
print('dirs:', len(dirs), 'files:', len(files), files[:5])

for d in dirs[:3]:
    dp = os.path.join(sh, d)
    for dirpath, dirnames, filenames in os.walk(dp):
        for fn in filenames:
            fp = os.path.join(dirpath, fn)
            sz = os.path.getsize(fp)
            with open(fp, 'rb') as f:
                b = f.read(64)
            print(os.path.relpath(fp, sh), '|', sz, '|', b[:16].hex(), '|', repr(b[:32]))
print('--- one entry deep listing ---')
d = dirs[0]
for dirpath, dirnames, filenames in os.walk(os.path.join(sh, d)):
    print('DIR', os.path.relpath(dirpath, sh))
    for fn in filenames:
        fp = os.path.join(dirpath, fn)
        print('   ', fn, os.path.getsize(fp))
