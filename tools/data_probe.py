# -*- coding: utf-8 -*-
"""Probe .data encryption: ECB block dups, XOR-diff between files, single-byte XOR, header structure."""
import os, re, base64, collections, math

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
md = os.path.join(root, 'Data', 'MasterData')

def load(name):
    raw = open(os.path.join(md, name), 'rb').read()
    return base64.b64decode(re.sub(rb'\s+', b'', raw))

def show(tag, buf, n=48):
    print(tag, buf[:n].hex())
    print('    ascii:', ''.join(chr(c) if 32 <= c < 127 else '.' for c in buf[:n]))

# 1) ECB duplicate blocks
print('== ECB duplicate-block test ==')
for name in ['assetname.data', 'character.data', 'battle_enemy.data', 'ad_reward.data']:
    d = load(name)
    blocks = [d[i:i+16] for i in range(0, len(d) - 15, 16)]
    c = collections.Counter(blocks)
    dup = sum(v - 1 for v in c.values() if v > 1)
    print('%-28s bytes=%8d blocks=%7d distinct=%7d dupblocks=%7d' % (name, len(d), len(blocks), len(c), dup))

# 2) XOR diff between two same-prefix files and two different-prefix files
print('\n== XOR-diff (same prefix) ad_reward vs assist ==')
a, b = load('ad_reward.data'), load('assist.data')
x = bytes(p ^ q for p, q in zip(a, b))
printable = ''.join(chr(c) if 32 <= c < 127 else '.' for c in x[:256])
print(printable)

print('\n== XOR-diff (diff prefix) ad_reward vs animation_loginbonus_days ==')
c2 = load('animation_loginbonus_days.data')
x2 = bytes(p ^ q for p, q in zip(a, c2))
print(''.join(chr(c) if 32 <= c < 127 else '.' for c in x2[:256]))

# 3) single-byte XOR / additive scan for JSON markers on ad_reward
print('\n== single-byte XOR scan (score = count of { } [ ] " : , digits letters in first 512B) ==')
d = load('ad_reward.data')
best = []
for k in range(256):
    s = bytes(v ^ k for v in d[:512])
    score = sum(1 for ch in s if ch in b'{}[]":,0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-. ')
    best.append((score, k, s))
best.sort(reverse=True)
for score, k, s in best[:5]:
    print('key=%02x score=%d  %s' % (k, score, s[:120]))

# 4) additive (mod 256) single-byte scan
print('\n== additive scan ==')
best = []
for k in range(256):
    s = bytes((v - k) & 0xff for v in d[:512])
    score = sum(1 for ch in s if ch in b'{}[]":,0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-. ')
    best.append((score, k, s))
best.sort(reverse=True)
for score, k, s in best[:5]:
    print('add=%02x score=%d  %s' % (k, score, s[:120]))

# 5) do all files share a 4-byte tail or structure? check last 16 bytes of same-prefix files
print('\n== tails ==')
for name in ['ad_reward.data', 'assist.data', 'character.data', 'ad_movie.data']:
    d = load(name)
    show('%-24s tail' % name, d[-16:])
