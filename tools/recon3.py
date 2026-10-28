# -*- coding: utf-8 -*-
"""Recon 3: decode a .data file, inspect masterdata, try UnityPy on one bundle."""
import os, sys, base64, zlib, json, binascii, collections

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'

def show_data(name):
    p = os.path.join(root, 'Data', name)
    raw = open(p, 'rb').read()
    print('==', name, 'size', len(raw), 'head', raw[:24])
    try:
        dec = base64.b64decode(raw, validate=False)
        print('  b64 decoded', len(dec), 'head', dec[:24].hex(), repr(dec[:24]))
        # try zlib/gzip after base64
        for fn, label in ((zlib.decompress, 'zlib'),):
            try:
                z = fn(dec)
                print('  ', label, 'OK', len(z), repr(z[:60]))
            except Exception as e:
                pass
        # entropy-ish
        cnt = collections.Counter(dec)
        import math
        ent = -sum(c/len(dec)*math.log2(c/len(dec)) for c in cnt.values())
        print('  entropy %.3f' % ent)
    except Exception as e:
        print('  b64 fail', e)

show_data('device_local_data.data')
show_data('blacksmith_badge.data')
show_data('cri_cache.data')

md = os.path.join(root, 'Data', 'MasterData')
names = sorted(os.listdir(md))
print('MasterData count', len(names))
print(names[:40])

# header multi-check: decode first 16 bytes b64 to see if consistent prefix
print('--- first 8 bytes after b64 of several masterdata ---')
for n in names[:8]:
    raw = open(os.path.join(md, n), 'rb').read()
    dec = base64.b64decode(raw)
    print(n, len(raw), dec[:8].hex(), 'entropy?')
