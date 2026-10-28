# -*- coding: utf-8 -*-
"""Compare decoded MasterData .data blobs: sizes, alignment, prefixes, entropy."""
import os, re, base64, math, sys, collections

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
data_root = os.path.join(root, 'Data')

def entropy(buf):
    if not buf: return 0.0
    c = collections.Counter(buf)
    n = len(buf)
    return -sum(v/n * math.log2(v/n) for v in c.values())

files = []
for dp, dn, fn in os.walk(data_root):
    for f in fn:
        if f.endswith('.data'):
            files.append(os.path.join(dp, f))
files.sort()
print('total .data files:', len(files))

prefixes = collections.Counter()
rows = []
for p in files:
    raw = open(p, 'rb').read()
    try:
        dec = base64.b64decode(re.sub(rb'\s+', b'', raw), validate=False)
    except Exception as e:
        print('B64FAIL', os.path.basename(p), e); continue
    pre = dec[:16].hex()
    prefixes[pre] += 1
    rows.append((os.path.relpath(p, data_root), len(raw), len(dec), dec[:32].hex(), entropy(dec[:4096])))

print('\n=== top 12 first-16-byte prefixes ===')
for k, v in prefixes.most_common(12):
    print('%4d  %s' % (v, k))

print('\n=== per file (rel, b64len, bytes, len%%16, len%%8, first32hex, H) ===')
for rel, n, m, h, H in rows:
    print('%-46s %9d %9d  m16=%d m8=%d  %s  H=%.3f' % (rel, n, m, m % 16, m % 8, h, H))
