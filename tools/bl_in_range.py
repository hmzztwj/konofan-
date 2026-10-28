import struct, json, bisect, sys
from capstone import *
from capstone.arm64 import *
SO=r'F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so'
buf=open(SO,'rb').read()
e_phoff=struct.unpack_from('<Q',buf,0x20)[0]; e_phentsize=struct.unpack_from('<H',buf,0x36)[0]; e_phnum=struct.unpack_from('<H',buf,0x38)[0]
segs=[]
for i in range(e_phnum):
    off=e_phoff+i*e_phentsize
    p_type,p_flags=struct.unpack_from('<II',buf,off)
    p_offset,p_vaddr,p_paddr,p_filesz=struct.unpack_from('<QQQQ',buf,off+8)
    if p_type==1 and p_filesz: segs.append((p_vaddr,p_offset,p_filesz,p_flags))
def va2off(va):
    for v,o,s,f in segs:
        if v<=va<v+s: return o+(va-v)
    return None
d=json.load(open(r'tools\il2cppdumper\out570\script.json',encoding='utf-8'))
items=sorted((int(m['Address']), m['Name']) for m in d['ScriptMethod'])
A=[a for a,_ in items]
def name(a):
    i=bisect.bisect_right(A,a)-1
    return items[i][1] if i>=0 else '?'
start=int(sys.argv[1],16); ln=int(sys.argv[2],16)
off=va2off(start)
md=Cs(CS_ARCH_AARCH64, CS_MODE_ARM); md.detail=True
seen={}
for ins in md.disasm(buf[off:off+ln], start):
    if ins.mnemonic in ('bl','b') and ins.operands and ins.operands[0].type==ARM64_OP_IMM:
        t=ins.operands[0].imm
        if t<start or t>start+ln:
            seen.setdefault(t,[]).append(ins.address)
for t,addrs in sorted(seen.items()):
    print('%#x  %-70s  from %s' % (t, name(t), ','.join(hex(a) for a in addrs[:3])))
