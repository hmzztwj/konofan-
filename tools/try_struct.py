import json, base64, os, hashlib, itertools
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

lits = json.load(open(r'tools/out/literals_byindex.json', encoding='utf-8'))
slots = [int(l.split()[2],16) for l in open(r'tools/out/implicit.txt',encoding='utf-8') if l.startswith('IMPLICIT')]
idx = [(v >> 1) & 0x7fffff for v in slots]
toks = [lits[k] for k in idx]

DATA = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
blobs = []
for f in os.listdir(DATA):
    p = os.path.join(DATA, f)
    if f.endswith('.data') and os.path.getsize(p) < 20000:
        raw = open(p,'rb').read().strip()
        try:
            b = base64.b64decode(raw, validate=True)
            if b and len(b) % 16 == 0: blobs.append((f, b))
        except Exception: pass
print('blobs', len(blobs), [f for f,_ in blobs][:5])

def derive(pw, salt, n):
    return hashlib.pbkdf2_hmac('sha1', pw.encode(), salt.encode(), 1000, n)

def good(pt):
    if len(pt) < 3: return None
    n = pt[-1]
    if 1 <= n <= 16 and pt[-n:] == bytes([n])*n:
        body = pt[:-n]
    elif pt[-1] == 0 or pt[-2:] == b'\0\0':
        body = pt.rstrip(b'\0')
    else:
        return None
    if not body: return None
    try:
        s = body.decode('utf-8')
    except Exception:
        return None
    if not s: return None
    asc = sum(1 for ch in s if ' ' <= ch <= '~' or ch in '\n\t\r')
    if asc / len(s) < 0.95: return None
    return s

def try_pair(pw, salt):
    for nb in (48, 32):
        d = derive(pw, salt, nb)
        key, iv = d[:nb-16], d[nb-16:]
        for f, ct in blobs:
            pt = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor().update(ct)
            g = good(pt)
            if g: return (nb, f, g[:80])
    return None

cands = []
cands.append((toks[0]+toks[1], None))
cands.append((toks[1]+toks[0], None))
cands.append((toks[0], None))
cands.append((toks[1], None))
for pw, _ in list(cands):
    for salt in toks:
        r = try_pair(pw, salt)
        if r:
            print('HIT pw=%r salt=%r' % (pw, salt), r); raise SystemExit
print('structured: no hit')
