# -*- coding: utf-8 -*-
"""Recon 6: global-metadata header + keyword strings; SaveStory contents."""
import os, re, sys, struct

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
mp = os.path.join(root, 'il2cpp', 'Metadata', 'global-metadata.dat')
b = open(mp, 'rb').read()
print('metadata size', len(b))
magic, ver = struct.unpack_from('<Ii', b, 0)
print('magic %08x version %d' % (magic & 0xffffffff, ver))
print('head hex', b[:64].hex())

# ASCII strings
strs = re.findall(rb'[\x20-\x7e]{5,}', b)
print('ascii strings', len(strs))
kw = ['aes', 'rijndael', 'crypto', 'decrypt', 'encrypt', 'secret', 'salt', 'bundle',
      'wonder', 'catalog', 'utage', 'http', 'api', 'cri', 'cpk', 'usm', 'masterdata']
low = [s.lower() for s in strs]
for k in kw:
    hits = [s for s in strs if k.encode() in s.lower()]
    print(f'--- {k}: {len(hits)}')
    for s in hits[:12]:
        print('   ', s.decode('latin1')[:140])

# CJK / utf8 strings containing 素晴 or ゲーム
for enc, pat in (('utf-8', '素晴'),):
    try:
        hits = [m.group(0) for m in re.finditer(pat.encode(enc), b)]
        print(pat, 'occurrences', len(hits))
    except Exception as e:
        print(e)

print('=== Utage folder ===')
for dirpath, dirnames, filenames in os.walk(os.path.join(root, 'Utage')):
    print('DIR', os.path.relpath(dirpath, root), 'files', filenames[:10])
    for fn in filenames[:5]:
        fp = os.path.join(dirpath, fn)
        print('   ', fn, os.path.getsize(fp), open(fp, 'rb').read(48))

print('=== .bundle files elsewhere? ===')
cnt = 0
for dirpath, dirnames, filenames in os.walk(root):
    if 'UnityCache' in dirpath or 'Cri' in dirpath:
        continue
    for fn in filenames:
        if fn.endswith('.bundle'):
            cnt += 1
            if cnt < 6:
                print('   ', os.path.join(dirpath, fn))
print('total stray .bundle', cnt)
