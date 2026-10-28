# -*- coding: utf-8 -*-
"""Recon 4: parse Addressables catalog and classify asset/bundle names."""
import os, json, sys, collections, re

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
cat_path = os.path.join(root, 'com.unity.addressables', 'catalog_stable.json')

with open(cat_path, 'r', encoding='utf-8') as f:
    cat = json.load(f)

print('catalog keys:', list(cat.keys()))
for k, v in cat.items():
    if isinstance(v, list):
        print(' ', k, 'list len', len(v))
        if v and isinstance(v[0], dict):
            print('    first keys:', list(v[0].keys()))
    elif isinstance(v, (str, int, float, bool)) or v is None:
        print(' ', k, '=', repr(v)[:120])

def look(name, n=5):
    v = cat.get(name) or []
    print('== sample from', name, 'len', len(v))
    for item in v[:n]:
        print('  ', json.dumps(item, ensure_ascii=False)[:300])

for key in ('m_InternalIds', 'm_BundleLocations', 'm_AssetBundleProviderData', 'm_Resources'):
    if key in cat:
        look(key)
