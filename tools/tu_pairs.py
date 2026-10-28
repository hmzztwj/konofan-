import base64, hashlib, json, os, itertools
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
vals=json.load(open(r'tools\out\textutil_vals.json',encoding='utf-8'))
if isinstance(vals,dict): vals=list(vals.values())
vals=[v for v in vals if isinstance(v,str) and v]
print('tokens',len(vals))
ROOT=r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
tests=['MasterData/ad_reward.data','notification.data','tutorial.data']
raws=[]
for t in tests:
    p=os.path.join(ROOT,t.replace('/',os.sep))
    if os.path.exists(p):
        try: raws.append((t,base64.b64decode(open(p,'rb').read().strip())))
        except Exception: pass
print('files',[r[0] for r in raws])
def dec(k,iv,ct):
    d=Cipher(algorithms.AES(k),modes.CBC(iv)).decryptor()
    return d.update(ct)+d.finalize()
def ok(pt):
    if len(pt)<32: return False
    n=pt[-1]
    if n<1 or n>16 or pt[-n:]!=bytes([n])*n: return False
    body=pt[:-n]
    if not body: return False
    printme=all(32<=c<127 or c in (9,10,13) for c in body[:64])
    return printme and body[:1] in (b'{',b'[',b'"')
hits=0
for p,s in itertools.product(vals,vals):
    blob=hashlib.pbkdf2_hmac('sha1',p.encode(),s.encode(),1000,48)
    for k,iv in ((blob[:32],blob[32:]),(blob[16:],blob[:16])):
        for fn,ct in raws:
            if len(ct)%16: continue
            pt=dec(k,iv,ct)
            if ok(pt):
                print('HIT pass=%r salt=%r file=%s' % (p,s,fn)); print(pt[:120]); hits+=1
                if hits>3: raise SystemExit
print('hits',hits)
