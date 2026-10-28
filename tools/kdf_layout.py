import base64, hashlib, itertools, os, json
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
ROOT=r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files\Data'
files=[os.path.join(ROOT,'MasterData','ad_reward.data'), os.path.join(ROOT,'notification.data'),
       os.path.join(ROOT,'tutorial.data'), os.path.join(ROOT,'MasterData','character.data')]
raws={}
for p in files:
    if os.path.exists(p):
        raws[os.path.basename(p)]=base64.b64decode(open(p,'rb').read().strip())
def dec(key,iv,ct):
    d=Cipher(algorithms.AES(key),modes.CBC(iv)).decryptor()
    return d.update(ct)+d.finalize()
def ok(pt):
    if len(pt)<17: return False
    n=pt[-1]
    if n<1 or n>16 or pt[-n:]!=bytes([n])*n: return False
    return all(32<=c<127 or c in (9,10,13) for c in pt[:min(64,len(pt)-n)])
a1='FYf7ZgTyUCwA6'; b5='wMsQRZADHaN'; df='P7edmP'
passes={'a1+b5':a1+b5,'b5+a1':b5+a1,'a1':a1,'b5':b5,'a1+b5+df':a1+b5+df,'a1+df':a1+df,'df+a1+b5':df+a1+b5}
salts={'df':df,'a1':a1,'b5':b5,'empty':'','a1+b5':a1+b5,'b5+a1':b5+a1}
hits=0
for pn,pv in passes.items():
    for sn,sv in salts.items():
        for it in (1000,1,10000):
            blob=hashlib.pbkdf2_hmac('sha1',pv.encode(),sv.encode(),it,64)
            variants={
              'k32=0,iv=32':(blob[:32],blob[32:48]),
              'k32=16,iv=0':(blob[16:48],blob[:16]),
              'k16=0,iv=16':(blob[:16],blob[16:32]),
              'k16=32,iv=0':(blob[32:48],blob[:16]),
              'md5k':(hashlib.md5(blob[:32]).digest(), blob[32:48]),
            }
            for vn,(k,iv) in variants.items():
                for fn,ct in raws.items():
                    if len(ct)%16: continue
                    pt=dec(k,iv,ct)
                    if ok(pt):
                        print('HIT',pn,sn,it,vn,fn,len(pt),pt[:80]); hits+=1
print('hits',hits)
