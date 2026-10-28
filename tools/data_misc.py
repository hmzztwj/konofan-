# -*- coding: utf-8 -*-
"""Survey non-MasterData .data files; print heads; test base64-ness."""
import os, re, base64

root = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
data_root = os.path.join(root, 'Data')

B64 = re.compile(rb'^[A-Za-z0-9+/\r\n=]+$')
for dp, dn, fn in os.walk(data_root):
    if os.path.basename(dp) == 'MasterData':
        continue
    for f in sorted(fn):
        p = os.path.join(dp, f)
        raw = open(p, 'rb').read()
        isb64 = bool(B64.match(raw[:2000]))
        print('%-40s %9d  b64=%s  head=%r' % (os.path.relpath(p, root), len(raw), isb64, raw[:120]))
        if not isb64:
            try:
                print('    text:', raw[:400].decode('utf-8', 'replace').replace('\n', '\\n'))
            except Exception:
                pass
        else:
            dec = base64.b64decode(re.sub(rb'\s+', b'', raw))
            print('    decoded %d bytes head=%s ascii=%r' % (len(dec), dec[:24].hex(),
                  dec[:60].decode('utf-8', 'replace')))
