import json, sys
P=r'tools\il2cppdumper\out570\script.json'
d=json.load(open(P,encoding='utf-8'))
print('keys',list(d.keys()))
ss=d['ScriptString']; sm=d['ScriptMetadata']; smm=d['ScriptMetadataMethod']
print('counts',len(ss),len(sm),len(smm))
want={0x68F1600,0x6859AD8,0x68CE848,0x6632D30,0x68F15F8,0x68E2250}
import collections
for e in ss[:2]: print('SS sample',e)
for e in sm[:2]: print('SM sample',e)
for e in smm[:2]: print('SMM sample',e)
hits=[e for e in ss if int(str(e['Address']),0) in want]
print('SS hits',len(hits),hits[:5])
hits2=[e for e in sm if int(str(e['Address']),0) in want]
print('SM hits',len(hits2),hits2[:5])
hits3=[e for e in smm if int(str(e['Address']),0) in want]
print('SMM hits',len(hits3),hits3[:5])
