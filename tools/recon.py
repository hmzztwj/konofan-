# -*- coding: utf-8 -*-
"""Recon: dump headers of sample files across the game data tree."""
import os, glob, sys

root = sys.argv[1] if len(sys.argv) > 1 else r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'

groups = {
    'usm':   glob.glob(os.path.join(root, 'bundles', 'Cri', 'Usm', '**', '*.*'), recursive=True)[:3],
    'cpk':   glob.glob(os.path.join(root, 'bundles', 'Cri', 'Cpk', '**', '*.*'), recursive=True)[:3],
    'cache': glob.glob(os.path.join(root, 'UnityCache', 'Shared', '*', '*'))[:4],
    'data':  glob.glob(os.path.join(root, 'Data', '*.data'))[:4],
    'master': glob.glob(os.path.join(root, 'Data', 'MasterData', '**', '*.*'), recursive=True)[:4],
}
for k, v in groups.items():
    print('====', k)
    for p in v:
        try:
            with open(p, 'rb') as f:
                b = f.read(80)
            print(' ', os.path.relpath(p, root)[:110], '|', len(b), '|',
                  b[:16].hex(), '|', repr(b[:40]))
        except Exception as e:
            print(' ', p, 'ERR', e)
