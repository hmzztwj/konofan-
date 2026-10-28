# -*- coding: utf-8 -*-
"""Group membership + mtimes for identical-prefix .data files."""
import os, re, base64, collections, datetime

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
md = os.path.join(root, 'Data', 'MasterData')

def load(p):
    raw = open(p, 'rb').read()
    return base64.b64decode(re.sub(rb'\s+', b'', raw))

groups = collections.defaultdict(list)
for f in sorted(os.listdir(md)):
    p = os.path.join(md, f)
    d = load(p)
    st = os.stat(p)
    groups[d[:16]].append((f, len(d), datetime.datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')))

for k, v in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    mtimes = collections.Counter(x[2] for x in v)
    print('\n=== prefix %s  files=%d  mtimes=%s' % (k.hex(), len(v), dict(mtimes.most_common(4))))
    for f, n, t in v[:20]:
        print('    %-50s %9d  %s' % (f, n, t))
