import json, sys, bisect
d=json.load(open(r'tools\il2cppdumper\out570\script.json',encoding='utf-8'))
sm=d['ScriptMethod']
items=sorted((int(m['Address']), m['Name']) for m in sm)
addr=[a for a,_ in items]; names=[n for _,n in items]
def find(a):
    i=bisect.bisect_right(addr,a)-1
    if i<0: return None
    return items[i]
for arg in sys.argv[1:]:
    a=int(arg,16)
    print(hex(a), '->', find(a))
