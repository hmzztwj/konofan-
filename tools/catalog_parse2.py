# -*- coding: utf-8 -*-
"""Recon 5: decode catalog key data, summarize bundles."""
import os, json, base64, collections, re, struct

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
cat = json.load(open(os.path.join(root, 'com.unity.addressables', 'catalog_stable.json'), encoding='utf-8'))

ids = cat['m_InternalIds']
print('internal ids', len(ids))
bundle_re = re.compile(r'^(.*)\.bundle$')
bundles = collections.Counter()
others = collections.Counter()
for s in ids:
    m = bundle_re.match(s)
    if m:
        bundles[s] += 1
    else:
        others[os.path.splitext(s)[1] or '<noext>'] += 1
print('unique bundle paths', len(bundles))
print('non-bundle ext histogram', others.most_common(10))
for s in list(bundles)[:15]:
    print('  B', s)

# group by directory / name prefix
groups = collections.Counter()
for s in bundles:
    name = s.split('/')[-1]
    pref = name.split('_')[0] if '_' in name else name
    groups[pref] += 1
print('bundle name prefix top 30:', groups.most_common(30))

# decode keys
kd = base64.b64decode(cat['m_KeyDataString'])
print('keydata len', len(kd))
# Addressables KeyData format: count(int32) then entries: [hash int32][type byte][data...]
print('head hex', kd[:32].hex())
strings = re.findall(rb'[\x20-\x7e]{4,}', kd)
print('printable runs', len(strings))
for s in strings[:30]:
    print('   ', s.decode('latin1')[:120])
