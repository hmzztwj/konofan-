# -*- coding: utf-8 -*-
"""Test whether files sharing the same 16-byte prefix share a keystream (two-time-pad test)."""
import os, re, base64, math, collections, itertools

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
md = os.path.join(root, 'Data', 'MasterData')

def load(p):
    raw = open(p, 'rb').read()
    return base64.b64decode(re.sub(rb'\s+', b'', raw))

def H(buf):
    if not buf: return 0
    c = collections.Counter(buf); n = len(buf)
    return -sum(v/n*math.log2(v/n) for v in c.values())

files = sorted(os.listdir(md))
groups = collections.defaultdict(list)
for f in files:
    d = load(os.path.join(md, f))
    groups[d[:16]].append((f, d))

print('groups:', [(len(v), k.hex()) for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))][:8])

# pick same-prefix pairs from biggest group and different-prefix pairs
big = [v for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))][0]
print('\nbig group size', len(big))
pairs = [(big[0], big[1]), (big[2], big[3]), (big[4], big[5])]
print('\n== same-prefix XOR stats ==')
for (fa, da), (fb, db) in pairs:
    n = min(len(da), len(db))
    x = bytes(p ^ q for p, q in zip(da[:n], db[:n]))
    lo = sum(1 for c in x if c < 0x60) / n
    zero = x.count(0)
    ascii_ok = sum(1 for c in x if 0x20 <= c < 0x7f) / n
    print('%-34s %-34s n=%7d H=%.3f  <0x60=%.3f  zero=%d  printable=%.3f'
          % (fa, fb, n, H(x), lo, zero, ascii_ok))
    print('   ', ''.join(chr(c) if 32 <= c < 127 else '.' for c in x[:200]))

print('\n== cross-prefix XOR stats (control) ==')
other = [v for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1]))][1]
(fa, da), (fb, db) = big[0], other[0]
n = min(len(da), len(db))
x = bytes(p ^ q for p, q in zip(da[:n], db[:n]))
print('%-34s %-34s n=%7d H=%.3f  <0x60=%.3f  zero=%d' % (fa, fb, n, H(x), sum(1 for c in x if c < 0x60)/n, x.count(0)))

# same file shifted: keystream structure? check autocorrelation of one file
d = big[0][1]
print('\n== file autocorrelation (repeat distance) ' + big[0][0] + ' ==')
c = collections.Counter()
for off in range(1, 65):
    m = len(d) - off
    c[off] = sum(1 for i in range(m) if d[i] == d[i+off]) / m
for off in sorted(c, key=lambda k: -c[k])[:8]:
    print('  offset %2d match=%.4f (random~%.4f)' % (off, c[off], 1/256))
