# -*- coding: utf-8 -*-
"""Extract IL2CPP v29 string literals -> tools/out/literals.txt ; hunt crypto-ish literals."""
import os, struct, re, sys

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
mp = os.path.join(root, 'il2cpp', 'Metadata', 'global-metadata.dat')
b = open(mp, 'rb').read()
f = struct.unpack_from('<' + 'i' * 62, b, 8)
lit_off, lit_cnt, litdata_off, litdata_cnt = f[0], f[1], f[2], f[3]
n = lit_cnt // 8
lits = []
for i in range(n):
    ln, di = struct.unpack_from('<Ii', b, lit_off + i * 8)
    s = b[litdata_off + di: litdata_off + di + ln]
    lits.append(s.decode('utf-8', 'replace'))
print('literals:', len(lits))

out = r'F:\python_work\逆向\tools\out'
os.makedirs(out, exist_ok=True)
with open(os.path.join(out, 'literals.txt'), 'w', encoding='utf-8') as fh:
    for i, s in enumerate(lits):
        fh.write('%06d\t%s\n' % (i, s.replace('\n', '\\n').replace('\r', '\\r')))

# --- hunt ---
def report(title, pred, limit=80):
    hits = [(i, s) for i, s in enumerate(lits) if pred(s)]
    print('\n=== %s : %d hits ===' % (title, len(hits)))
    for i, s in hits[:limit]:
        print('%06d  %r' % (i, s[:160]))

crypto_words = re.compile(r'(?i)(key|iv\b|salt|aes|rijndael|crypt|xor|secret|token|passw|sign|hmac|hash)')
report('crypto words', lambda s: crypto_words.search(s) and len(s) < 120, 120)

b64ish = re.compile(r'^[A-Za-z0-9+/=_-]{16,64}$')
report('16-64 char b64-ish', lambda s: bool(b64ish.match(s)), 120)

hexish = re.compile(r'^[0-9a-fA-F]{16,128}$')
report('hex-ish 16-128', lambda s: bool(hexish.match(s)), 60)

url = re.compile(r'https?://')
report('urls', lambda s: bool(url.search(s)), 120)
