import json, base64, os, hashlib, sys, time, itertools
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

lits_all = json.load(open(r'tools/out/literals_byindex.json', encoding='utf-8'))
slots=[int(l.split()[2],16) for l in open(r'tools/out/implicit.txt',encoding='utf-8') if l.startswith('IMPLICIT')]
toks=[lits_all[(v>>1)&0x7fffff] for v in slots]
print('toks[0:3]=',toks[:3])

DATA=r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
blobs=[]
for f in sorted(os.listdir(DATA)):
    p=os.path.join(DATA,f)
    if f.endswith('.data') and os.path.getsize(p)<60000:
        try:
            b=base64.b64decode(open(p,'rb').read().strip(),validate=True)
            if b and len(b)%16==0: blobs.append((f,b))
        except Exception: pass
print('blobs',len(blobs))

def pad_ok(pt):
    n=pt[-1]
    return 1<=n<=16 and pt[-n:]==bytes([n])*n

def check(key,iv):
    for f,ct in blobs:
        pt=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor().update(ct)
        if not pad_ok(pt): return None
    return True

def trial(pw,salt,tag):
    for nb,kn in ((48,32),(32,16)):
        d=hashlib.pbkdf2_hmac('sha1',pw.encode(),salt.encode(),1000,nb)
        if check(d[:kn],d[kn:kn+16]): return (tag,nb,d.hex())
    return None

t0=time.time()
# structured: pass = tok[i]+tok[j] for i,j<8, salt = tok[k] all 76
found=[]
for i,j in itertools.product(range(8),repeat=2):
    pw=toks[i]+toks[j]
    for k,salt in enumerate(toks):
        r=trial(pw,salt,'t%d+t%d|s%d'%(i,j,k))
        if r: print('HIT',r,toks[i],toks[j],salt); found.append(r)
print('stage1 done %.1fs hits=%d'%(time.time()-t0,len(found)))
if not found:
    # also singleton pass
    for i in range(8):
        for k in range(len(toks)):
            r=trial(toks[i],toks[k],'t%d|s%d'%(i,k))
            if r: print('HIT',r); found.append(r)
    print('stage2 done %.1fs hits=%d'%(time.time()-t0,len(found)))
