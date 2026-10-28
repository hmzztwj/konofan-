import json, base64, os, hashlib, sys, time
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

lits_all = json.load(open(r'tools/out/literals_byindex.json', encoding='utf-8'))
slots = [int(l.split()[2],16) for l in open(r'tools/out/implicit.txt',encoding='utf-8') if l.startswith('IMPLICIT')]
toks = [lits_all[(v>>1)&0x7fffff] for v in slots]
a1, b5, df = toks[0], toks[1], toks[2]
print('a1=%r b5=%r df=%r' % (a1,b5,df))

DATA = r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
blobs=[]
for f in sorted(os.listdir(DATA)):
    p=os.path.join(DATA,f)
    if f.endswith('.data') and os.path.getsize(p) < 40000:
        try:
            b=base64.b64decode(open(p,'rb').read().strip(), validate=True)
            if b and len(b)%16==0: blobs.append((f,b))
        except Exception: pass
print('blobs',len(blobs))

def jsonish(pt):
    if len(pt)<8: return None
    for strip in ('pkcs7','zero','none'):
        if strip=='pkcs7':
            n=pt[-1]
            body = pt[:-n] if 1<=n<=16 and pt[-n:]==bytes([n])*n else None
        elif strip=='zero':
            body = pt.rstrip(b'\0')
        else:
            body = pt
        if body is None or len(body)<4: continue
        try: s=body.decode('utf-8')
        except Exception: continue
        asc=sum(1 for ch in s if ' '<=ch<='~' or ch in '\n\t\r')
        if asc/len(s) < 0.93: continue
        t=s.lstrip()
        if t[:1] in '{[' or ('"' in t and ':' in t):
            return (strip, s[:100])
    return None

def test(pw, salt, tag):
    cleanpw = ''.join(ch for ch in pw if 32 <= ord(ch) < 0x110000)
    for nb in (48,32,16+0):
        try:
            d=hashlib.pbkdf2_hmac('sha1', cleanpw.encode(), salt.encode(), 1000, nb)
        except Exception: continue
        schemes=[]
        if nb==48: schemes=[('k32v16', d[:32], d[32:48])]
        if nb==32: schemes=[('k16v16', d[:16], d[16:32])]
        for name,key,iv in schemes:
            for f,ct in blobs:
                pt=Cipher(algorithms.AES(key), modes.CBC(iv)).decryptor().update(ct)
                r=jsonish(pt)
                if r: return (tag,name,f,r,key.hex(),iv.hex())
            # iv prefixed in file
            for f,ct in blobs:
                if len(ct)<32: continue
                pt=Cipher(algorithms.AES(key), modes.CBC(ct[:16])).decryptor().update(ct[16:])
                r=jsonish(pt)
                if r: return (tag+'+ivpre',name,f,r,key.hex(),iv.hex())
    return None

t0=time.time()
pws=[('a1+b5',a1+b5),('b5+a1',b5+a1),('a1',a1),('b5',b5)]
saltcands=[('df',df)]
# all tokens as salt + all literals as salt
seen=set()
for t in toks: 
    if t not in seen: saltcands.append((t[:8],t)); seen.add(t)
n=0
for pwtag,pw in pws:
    for st,salt in saltcands:
        n+=1
        if n%2000==0: print(n, '%.1fs'%(time.time()-t0), flush=True)
        r=test(pw,salt,pwtag+'|'+st)
        if r: print('HIT',r); sys.exit()
print('no hit', n, '%.1fs'%(time.time()-t0))
