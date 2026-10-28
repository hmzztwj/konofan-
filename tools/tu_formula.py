import json,base64,hashlib,os,re,sys
from Crypto.Cipher import AES
base=r"F:\python_work\逆向"
lit=json.load(open(base+r"\tools\il2cppdumper\lookup_cache.json",encoding='utf-8'))["strs"]
lit={int(k):v for k,v in lit.items()}
addrs=sorted(lit)
vals=[]
for l in open(base+r"\tools\out\implicit.txt",encoding='utf-8'):
    m=re.match(r'IMPLICIT 0x[0-9a-f]+ (0x[0-9a-f]+)',l)
    if m: vals.append(int(m.group(1),16))
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
forms={
 'low16shr1': lambda v:(v&0xffff)>>1,
 'low32shr1': lambda v:(v&0xffffffff)>>1,
 'minus':     lambda v:v-0xa0000000,
 'minus2':    lambda v:(v-0xa0000000)>>1,
 'low20shr1': lambda v:(v&0xfffff)>>1,
 'low32':     lambda v:v&0xffffffff,
 'xor':       lambda v:(v^0xa0000000),
 'low24shr1': lambda v:(v&0xffffff)>>1,
}
for name,f in forms.items():
    idx=[f(v) for v in vals]
    if any(not(0<=i<len(addrs)) for i in idx):
        print(name,'SKIP out-of-range', max(idx)); continue
    cands=sorted({lit[addrs[i]] for i in idx if lit[addrs[i]]})
    print(name,'cands',len(cands),'sample',[c[:28] for c in cands[:3]])
    found=False
    for p in cands:
        for s in cands:
            for kb in (48,32):
                dk=hashlib.pbkdf2_hmac('sha1',p.encode(),s.encode(),1000,kb)
                key,iv=(dk[:32],dk[32:48]) if kb==48 else (dk[:16],dk[16:32])
                r=test(key,iv)
                if r:
                    print('HIT',name,kb,repr(p),repr(s),r); found=True; sys.exit(0)
print('none')
