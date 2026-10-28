# -*- coding: utf-8 -*-
"""Recon 5: open a couple of cached bundles with UnityPy, list object types/names."""
import os, sys, collections, glob

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
sh = os.path.join(root, 'UnityCache', 'Shared')
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.21f1'

entries = sorted(os.listdir(sh))
picked = []
for d in entries:
    dp = os.path.join(sh, d)
    if not os.path.isdir(dp):
        continue
    for sub in os.listdir(dp):
        data = os.path.join(dp, sub, '__data')
        if os.path.exists(data):
            picked.append(data)
        if len(picked) >= 4:
            break
    if len(picked) >= 4:
        break

# pick one large and one small
picked.sort(key=os.path.getsize, reverse=True)
targets = [picked[0], picked[-1]] + picked[1:3]
for p in targets:
    print('=' * 70)
    print('BUNDLE', os.path.getsize(p), os.path.relpath(p, sh))
    try:
        env = UnityPy.load(p)
        print('  files:', [f for f in env.files.keys()][:6])
        cnt = collections.Counter()
        for obj in env.objects:
            cnt[obj.type.name] += 1
        print('  object types:', dict(cnt))
        shown = 0
        for obj in env.objects:
            if obj.type.name in ('TextAsset', 'MonoBehaviour', 'AssetBundle', 'Texture2D', 'AudioClip', 'Sprite'):
                try:
                    if obj.type.name == 'TextAsset':
                        d = obj.read()
                        nm = getattr(d, 'm_Name', '?')
                        raw = d.m_Script if isinstance(d.m_Script, bytes) else bytes(d.m_Script.encode('utf-8', 'surrogateescape'))
                        print('   TextAsset', nm, len(raw), repr(raw[:120]))
                    elif obj.type.name == 'MonoBehaviour':
                        d = obj.read()
                        print('   MonoBehaviour', getattr(d, 'm_Name', '?'), 'script', getattr(d, 'm_Script', None))
                    elif obj.type.name == 'AssetBundle':
                        d = obj.read()
                        print('   AssetBundle name', getattr(d, 'm_AssetBundleName', '?'), 'deps', getattr(d, 'm_Dependencies', None))
                except Exception as e:
                    print('   ERR', obj.type.name, e)
                shown += 1
                if shown > 6:
                    break
    except Exception as e:
        import traceback; traceback.print_exc()
