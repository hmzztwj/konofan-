import json,base64,hashlib,os,re,itertools,sys
from Crypto.Cipher import AES
base=r"F:\python_work\逆向"
lit=json.load(open(base+r"\tools\il2cppdumper\lookup_cache.json",encoding='utf-8'))["strs"]
lit={int(k):v for k,v in lit.items()}
addrs=sorted(lit)
vals=[]
for l in open(base+r"\tools\out\implicit.txt",encoding='utf-8'):
    m=re.match(r'IMPLICIT 0x[0-9a-f]+ (0x[0-9a-f]+)',l)
    if m: vals.append(int(m.group(1),16))
print('usages',len(vals))
def dec(v):
    i=(v&0xffff)>>1
    return lit[addrs[i]] if 0<=i<len(addrs) else None
cands=[dec(v) for v in vals]
for i,c in enumerate(cands[:5]): print(i,repr(c)[:70])
D=base+r"\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
def load(n):
    b=base64.b64decode(open(os.path.join(D,n),'rb').read())
    return b
targets={n:load(n) for n in ('tutorial.data','notification.data')}
def test(key,iv):
    for n,b in targets.items():
        c=AES.new(key,AES.MODE_CBC,iv); pt=c.decrypt(b)
        pad=pt[-1]
        if 1<=pad<=16 and pt[-pad:]==bytes([pad])*pad:
            body=pt[:-pad]
            try: s=body.decode('utf-8')
            except Exception: continue
            if s and s[0] in '{[': return (n,body[:100])
    return None
u=[c for c in cands if c]
print('unique',len(set(u)))
tried=0
for p in set(u):
    for s in set(u):
        for kb in (48,32):
            dk=hashlib.pbkdf2_hmac('sha1',p.encode(),s.encode(),1000,kb)
            key,iv=(dk[:32],dk[32:48]) if kb==48 else (dk[:16],dk[16:32])
            tried+=1
            r=test(key,iv)
            if r:
                print('HIT kb',kb,'pass',repr(p),'salt',repr(s),r); sys.exit(0)
print('no hit, tried',tried)
