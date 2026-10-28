import json, re
lines=open(r'tools/out/cc2.txt',encoding='utf-8').read().splitlines()
slotre=re.compile(r'slot (0x[0-9A-Fa-f]+)')
last=None
seq=[]
for ln in lines:
    m=slotre.search(ln)
    if m and 'ldr' in ln: last_ldr=(int(m.group(1),16), ln)
    if 'bl       0x2aeeb40' in ln or 'bl       0x2AEeb40' in ln:
        # find nearest preceding ldr x0
        seq.append(last_ldr)
print('implicit calls:',len(seq))
d=json.load(open(r'tools\il2cppdumper\out570\script.json',encoding='utf-8'))
ss={int(e['Address']): e['Value'] for e in d['ScriptString']}
vals=[]
miss=0
for slot,ln in seq:
    v=ss.get(slot)
    if v is None: miss+=1; v='<MISS:%#x>'%slot
    vals.append(v)
print('miss',miss)
for i,v in enumerate(vals[:12]):
    print(i,repr(v))
json.dump(vals,open(r'tools/out/textutil_vals.json','w',encoding='utf-8'),ensure_ascii=False)
print('a1=%r b5=%r df=%r'%(vals[0],vals[1],vals[2]))
