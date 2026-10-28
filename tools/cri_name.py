import base64, hashlib, json, os, urllib.parse
ROOT=r'F:\python_work\逆向\素晴\素晴\jp.co.sumzap.pj0007\files'
CAT=os.path.join(ROOT,'com.unity.addressables','catalog_stable.json')
cat=json.load(open(CAT,encoding='utf-8'))
ids=cat['m_InternalIds']
plain=[]
for s in ids:
    if '.cpk.bytes' in s or '.usm.bytes' in s:
        b=os.path.basename(s)
        plain.append(b[:-6] if b.endswith('.bytes') else b)
plain=sorted(set(plain))
print('catalog CRI names:',len(plain),plain[:3])
disk=[]
for sub in ('Cpk','Usm'):
    d=os.path.join(ROOT,'bundles','Cri',sub)
    if not os.path.isdir(d): continue
    for f in sorted(os.listdir(d))[:3]:
        raw=urllib.parse.unquote(f)
        try: b=base64.b64decode(raw+'='*(-len(raw)%4))
        except Exception as e:
            print('decode fail',f,e); continue
        disk.append((sub,f,b))
        print(sub,f,'->',len(b),b.hex()[:32])
# 试各种哈希
cands=plain[:40]
tests=[]
for name in cands:
    stem=os.path.splitext(name)[0]
    for variant in (name,stem,name.lower(),stem.lower(),name+'\n'):
        for enc in ('utf-8',):
            d=variant.encode(enc)
            for h in ('sha256','sha1','md5'):
                hh=getattr(hashlib,h)(d).digest()
                tests.append((variant,h,hh))
print('tests',len(tests))
hit=0
for sub,f,b in disk:
    for v,h,hh in tests:
        if hh[:len(b)]==b or hh==b:
            print('MATCH',sub,f,v,h); hit+=1
print('hit',hit)
