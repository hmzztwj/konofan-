import json, base64, os, itertools, hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

lits = json.load(open(r'tools/out/literals_byindex.json', encoding='utf-8'))
slots = []
for line in open(r'tools/out/implicit.txt', encoding='utf-8'):
    p = line.split()
    if p and p[0] == 'IMPLICIT':
        slots.append(int(p[2], 16))
idx = [(v >> 1) & 0x7fffff for v in slots]
toks = [lits[k] for k in idx]

DATA = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
files = ['tutorial.data', 'notification.data', 'buttlecutin.data', 'plan_map.data', 'device_local_data.data']
blobs = []
for f in files:
    p = os.path.join(DATA, f)
    if os.path.exists(p):
        raw = open(p, 'rb').read().strip()
        try: blobs.append((f, base64.b64decode(raw, validate=True)))
        except Exception as e: pass
print('blobs', [(f, len(b)) for f, b in blobs])

def dec(key, iv, ct):
    c = Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor()
    return c.update(ct) + c.finalize()

def ok(pt):
    if not pt: return False
    n = pt[-1]
    if n < 1 or n > 16: return False
    if pt[-n:] != bytes([n])*n: return False
    body = pt[:-n]
    if not body: return False
    printable = sum(1 for c in body if 32 <= c < 127 or c in (9,10,13) or c >= 0x80)
    return printable == len(body)

def derive(pw, salt, n):
    return hashlib.pbkdf2_hmac('sha1', pw.encode('utf-8'), salt.encode('utf-8'), 1000, n)

hits = []
tested = 0
# password = tok[i]+tok[j], salt = tok[k], first 10 tokens
N = 10
for i, j, k in itertools.product(range(N), repeat=3):
    pw = toks[i] + toks[j]; salt = toks[k]
    for nbytes in (48, 32):
        d = derive(pw, salt, nbytes)
        key, iv = d[:nbytes-16], d[nbytes-16:]
        tested += 1
        for f, ct in blobs:
            if len(ct) % 16: continue
            pt = dec(key, iv, ct)
            if ok(pt):
                hits.append((pw, salt, nbytes, f, pt[:60]))
                print('HIT', pw, salt, nbytes, f, pt[:60]); break
print('tested', tested, 'hits', len(hits))
