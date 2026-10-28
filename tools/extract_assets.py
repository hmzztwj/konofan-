# -*- coding: utf-8 -*-
"""Asset extraction toolkit for cached UnityFS bundles.

Usage:
  python extract_assets.py list   [n]          list bundles with container counts
  python extract_assets.py demo                export a few sample sprites/textassets
  python extract_assets.py images <outdir>     export every Texture2D/Sprite (PNG)
  python extract_assets.py text <outdir>       export every TextAsset (raw bytes)
"""
import os, sys, csv, json, io
import UnityPy
UnityPy.config.FALLBACK_UNITY_VERSION = '2022.3.21f1'

ROOT = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
CACHE = os.path.join(ROOT, 'UnityCache', 'Shared')
CSV = r'F:\python_work\逆向\tools\out\bundles.csv'


def bundle_paths():
    for d in sorted(os.listdir(CACHE)):
        sub = os.path.join(CACHE, d)
        if not os.path.isdir(sub):
            continue
        for d2 in sorted(os.listdir(sub)):
            p = os.path.join(sub, d2, '__data')
            if os.path.isfile(p):
                yield os.path.join(d, d2), p


def safe(name):
    return ''.join(c if c.isalnum() or c in '._-@' else '_' for c in name)[:120]


def export_images(outdir, limit=None, only=None):
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for key, path in bundle_paths():
        if only and only not in key:
            continue
        try:
            env = UnityPy.load(path)
        except Exception as e:
            print('LOAD FAIL', key, e)
            continue
        for obj in env.objects:
            if obj.type.name not in ('Texture2D', 'Sprite'):
                continue
            try:
                data = obj.read()
                name = getattr(data, 'm_Name', '') or 'noname'
                img = data.image
                if img is None:
                    continue
                fn = os.path.join(outdir, '%s_%s_%s.png' % (safe(key.replace('\\', '_')), obj.type.name, safe(name)))
                img.save(fn)
                n += 1
                if limit and n >= limit:
                    print('exported', n)
                    return n
            except Exception as e:
                print('OBJ FAIL', key, obj.path_id, obj.type.name, repr(e)[:120])
    print('exported', n)
    return n


def export_text(outdir, limit=None):
    os.makedirs(outdir, exist_ok=True)
    n = 0
    for key, path in bundle_paths():
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        for obj in env.objects:
            if obj.type.name != 'TextAsset':
                continue
            try:
                data = obj.read()
                name = safe(getattr(data, 'm_Name', '') or 'noname')
                raw = data.m_Script
                if isinstance(raw, str):
                    raw = raw.encode('utf-8', 'surrogateescape')
                ext = '.txt'
                if raw[:4] == b'\x00\x00\x00\x00' or (name.endswith('.atlas')):
                    ext = '.atlas' if name.endswith('.atlas') else '.bin'
                fn = os.path.join(outdir, '%s_%s%s' % (safe(key.replace('\\', '_')), name, ext))
                open(fn, 'wb').write(raw)
                n += 1
                if limit and n >= limit:
                    print('exported', n)
                    return n
            except Exception as e:
                print('OBJ FAIL', key, obj.path_id, repr(e)[:120])
    print('exported', n)
    return n


def demo():
    # find first bundles that hold textures and textassets
    counts = {'img': 0, 'txt': 0}
    os.makedirs(r'F:\python_work\逆向\out\demo', exist_ok=True)
    for key, path in bundle_paths():
        try:
            env = UnityPy.load(path)
        except Exception:
            continue
        for obj in env.objects:
            t = obj.type.name
            if t in ('Texture2D', 'Sprite') and counts['img'] < 6:
                try:
                    data = obj.read()
                    img = data.image
                    if img is None:
                        continue
                    fn = r'F:\python_work\逆向\out\demo\%s_%s.png' % (t, safe(getattr(data, 'm_Name', 'x')))
                    img.save(fn)
                    counts['img'] += 1
                    print('IMG', fn, img.size, img.mode)
                except Exception as e:
                    print('img fail', repr(e)[:100])
            if t == 'TextAsset' and counts['txt'] < 4:
                try:
                    data = obj.read()
                    raw = data.m_Script
                    if isinstance(raw, str):
                        raw = raw.encode('utf-8', 'surrogateescape')
                    print('TXT', getattr(data, 'm_Name', ''), len(raw), raw[:120])
                    counts['txt'] += 1
                except Exception as e:
                    print('txt fail', repr(e)[:100])
        if counts['img'] >= 6 and counts['txt'] >= 4:
            break
    print(counts)


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'demo'
    if cmd == 'demo':
        demo()
    elif cmd == 'images':
        export_images(sys.argv[2], limit=int(sys.argv[3]) if len(sys.argv) > 3 else None)
    elif cmd == 'text':
        export_text(sys.argv[2], limit=int(sys.argv[3]) if len(sys.argv) > 3 else None)
    elif cmd == 'list':
        rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig')))
        seen = {}
        for r in rows:
            if r['type'] == 'CONTAINER':
                seen.setdefault(r['file'], []).append(r['name'])
        for f, c in list(seen.items())[:int(sys.argv[2]) if len(sys.argv) > 2 else 10]:
            print(f, len(c))
            for x in c[:5]:
                print('   ', x)
