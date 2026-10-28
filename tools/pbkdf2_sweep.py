import json,base64,hashlib,os,time,sys
from Crypto.Cipher import AES
D=r"F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data"
lit=json.load(open(r"F:\python_work\逆向\tools\il2cppdumper\lookup_cache.json",encoding='utf-8'))["strs"]
vals=sorted({v for v in lit.values() if v and 1<=len(v)<=80})
print('candidates',len(vals),flush=True)
def load(name):
    raw=open(os.path.join(D,name),'rb').read()
    try: return base64.b64decode(raw,validate=False)
    except Exception: return None
targets={}
for n in ('tutorial.data','local_setting.data','notification.data'):
    b=load(n)
    if b: targets[n]=b
print({k:len(v) for k,v in targets.items()},flush=True)
def ok(pt):
    try: s=pt.decode('utf-8')
    except Exception: return False
    return sum(1 for c in s[:200] if 32<=ord(c)<127 or c in '\r\n\t')>=len(s[:200])*0.9
def test(key,iv):
    for n,b in targets.items():
        try:
            c=AES.new(key,AES.MODE_CBC,iv)
            pt=c.decrypt(b)
        except Exception: return None
        pad=pt[-1]
        if 1<=pad<=16 and pt[-pad:]==bytes([pad])*pad:
            body=pt[:-pad]
            if ok(body): return (n,body[:120])
    return None
salts=["", "salt", "konofan", "Konofan", "sumzap", "jp.co.sumzap.pj0007", "pjsalt"]
t0=time.time(); hit=None
for i,p in enumerate(vals):
    if i%2000==0: print(i,round(time.time()-t0,1),flush=True)
    sl=[p]+salts
    for s in sl:
        for kb,ks in ((48,None),(32,None)):
            dk=hashlib.pbkdf2_hmac('sha1',p.encode('utf-8'),s.encode('utf-8'),1000,kb if kb==48 else 32)
            if kb==48: key,iv=dk[:32],dk[32:48]
            else: key,iv=dk[:16],dk[16:32]
            r=test(key,iv)
            if r:
                print('HIT',repr(p),repr(s),kb,r,flush=True); hit=(p,s,kb); sys.exit(0)
print('no hit',round(time.time()-t0,1),flush=True)
