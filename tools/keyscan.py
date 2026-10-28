# -*- coding: utf-8 -*-
"""Brute-force plausible AES keys from metadata string literals against .data padding oracle."""
import os, re, base64, hashlib, itertools, sys
from Crypto.Cipher import AES

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
md = os.path.join(root, 'Data', 'MasterData')
litfile = r'F:\python_work\逆向\tools\out\literals.txt'

def load(name):
    raw = open(os.path.join(md, name), 'rb').read()
    return base64.b64decode(re.sub(rb'\s+', b'', raw))

lits = []
for line in open(litfile, encoding='utf-8'):
    parts = line.rstrip('\n').split('\t', 1)
    if len(parts) == 2:
        lits.append(parts[1].replace('\\n', '\n'))
print('literals', len(lits))

cands = set()
def add(k, label):
    if k and len(k) in (16, 24, 32):
        cands.add((k, label))

for s in lits:
    if not s.isprintable() or len(s) > 128:
        continue
    b = s.encode()
    if len(b) in (16, 24, 32):
        add(b, 'raw:' + s[:40])
    if len(s) in (22, 43, 44, 24, 32) and re.fullmatch(r'[A-Za-z0-9+/=_-]+', s):
        try:
            d = base64.b64decode(s + '=' * (-len(s) % 4))
            add(d, 'b64:' + s[:40])
        except Exception:
            pass
    if len(s) in (32, 64) and re.fullmatch(r'[0-9a-fA-F]+', s):
        try:
            add(bytes.fromhex(s), 'hex:' + s[:40])
        except Exception:
            pass
    if len(s) >= 4:
        h = s.encode()
        add(hashlib.md5(h).digest(), 'md5:' + s[:40])
        add(hashlib.sha256(h).digest(), 'sha256:' + s[:40])

for extra in ['jp.co.sumzap.pj0007', 'sumzap', 'wonder', 'Wonder', 'utm', 'masterdata', 'MasterData']:
    b = extra.encode()
    add(b, 'lit:' + extra)
    add(hashlib.md5(b).digest(), 'md5:' + extra)
    add(hashlib.sha256(b).digest(), 'sha256:' + extra)

print('candidates', len(cands))

files = ['ad_reward.data', 'assist_medal_rate.data', 'character_rank_member_exp.data',
         'campaign_item_gacha.data', 'character_enhance_change_display.data']
blobs = {f: load(f) for f in files}

def pad_ok(d):
    if not d:
        return False
    p = d[-1]
    return 1 <= p <= 16 and d[-p:] == bytes([p]) * p

def try_key(k):
    for mode in ('ECB', 'CBC0', 'CBCkey'):
        try:
            if mode == 'ECB':
                c = AES.new(k, AES.MODE_ECB)
                outs = {f: c.decrypt(blobs[f]) for f in files}
            else:
                iv = bytes(16) if mode == 'CBC0' else (k[:16] if len(k) >= 16 else bytes(16))
                outs = {f: AES.new(k, AES.MODE_CBC, iv).decrypt(blobs[f]) for f in files}
        except Exception:
            continue
        if all(pad_ok(outs[f]) for f in files):
            return mode, outs
    return None

hits = 0
for k, label in cands:
    r = try_key(k)
    if r:
        hits += 1
        mode, outs = r
        print('HIT', mode, k.hex(), label)
        for f in files:
            print('   ', f, outs[f][:80])
print('done, hits =', hits)
