import json,base64,hashlib,os,re,math,sys
from collections import Counter
from Crypto.Cipher import AES
base=r"F:\python_work\逆向"
lit=json.load(open(base+r"\tools\il2cppdumper\lookup_cache.json",encoding='utf-8'))["strs"]
vals=set(v for v in lit.values() if v)
def ent(s):
    c=Counter(s); n=len(s); return -sum(v/n*math.log2(v/n) for v in c.values())
tok=sorted(v for v in vals if re.fullmatch(r'[A-Za-z0-9+/=]{10,48}',v) and re.search(r'[a-z]',v) and re.search(r'[A-Z]',v) and re.search(r'[0-9]',v) and ent(v)>3.4)
print('tokens',len(tok),flush=True)
D=base+r"\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
targets={n:base64.b64decode(open(os.path.join(D,n),'rb').read()) for n in ('tutorial.data','notification.data','local_setting.data')}
def test(key,iv):
    for n,b in targets.items():
        c=AES.new(key,AES.MODE_CBC,iv); pt=c.decrypt(b)
        pad=pt[-1]
        if 1<=pad<=16 and pt[-pad:]==bytes([pad])*pad:
            body=pt[:-pad]
            try: s=body.decode('utf-8')
            except Exception: continue
            if s and s.lstrip()[:1] in '{[': return (n,body[:120])
    return None
n=0
for p in tok:
    for s in tok:
        for kb in (48,32):
            dk=hashlib.pbkdf2_hmac('sha1',p.encode(),s.encode(),1000,kb)
            key,iv=(dk[:32],dk[32:48]) if kb==48 else (dk[:16],dk[16:32])
            n+=1
            r=test(key,iv)
            if r: print('HIT',kb,repr(p),repr(s),r,flush=True); sys.exit(0)
print('no hit',n,flush=True)
