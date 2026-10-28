import sys, json, struct, re
from capstone import *
from capstone.arm64 import *

ELF=r"F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so"
buf=open(ELF,'rb').read()
# parse program headers
e_phoff=struct.unpack_from('<Q',buf,0x20)[0]
e_phentsize=struct.unpack_from('<H',buf,0x36)[0]
e_phnum=struct.unpack_from('<H',buf,0x38)[0]
segs=[]
for i in range(e_phnum):
    off=e_phoff+i*e_phentsize
    p_type,p_flags=struct.unpack_from('<II',buf,off)
    p_offset,p_vaddr,p_paddr,p_filesz,p_memsz=struct.unpack_from('<QQQQQ',buf,off+8)
    if p_type==1: segs.append((p_vaddr,p_filesz,p_offset))
def va2off(va):
    for v,sz,o in segs:
        if v<=va<v+sz: return o+(va-v)
    return None
def read8(va):
    o=va2off(va)
    if o is None or o+8>len(buf): return None
    return struct.unpack_from('<Q',buf,o)[0]
# relocations R_AARCH64_RELATIVE: applied to .data => slot content = addend
e_shoff=struct.unpack_from('<Q',buf,0x28)[0]
e_shentsize=struct.unpack_from('<H',buf,0x3a)[0]
e_shnum=struct.unpack_from('<H',buf,0x3c)[0]
e_shstrndx=struct.unpack_from('<H',buf,0x3e)[0]
shs=[]
for i in range(e_shnum):
    o=e_shoff+i*e_shentsize
    name,typ,flags,addr,offset,size,link,info,align,entsize=struct.unpack_from('<IIQQQQIIQQ',buf,o)
    shs.append((name,typ,flags,addr,offset,size,entsize))
reloc={}
for name,typ,flags,addr,offset,size,entsize in shs:
    if typ==4 and entsize==24:  # SHT_RELA
        n=size//24
        for k in range(n):
            r_off,r_info,r_add=struct.unpack_from('<QQq',buf,offset+k*24)
            if (r_info & 0xffffffff)==1027:
                reloc[r_off]=r_add & 0xffffffffffffffff
def slotval(va):
    if va in reloc: return reloc[va]
    return read8(va)
lit=json.load(open(r"tools/il2cppdumper/lookup_cache.json",encoding='utf-8'))["strs"]
lit={int(k):v for k,v in lit.items()}
rva=int(sys.argv[1],16); size=int(sys.argv[2],16)
off=va2off(rva)
md=Cs(CS_ARCH_AARCH64, CS_MODE_ARM); md.detail=True
code=buf[off:off+size]
regs={}
out=[]
for ins in md.disasm(code, rva):
    mn=ins.mnemonic; ops=ins.op_str
    if mn=='adrp':
        r=ops.split(',')[0].strip()
        imm=ins.operands[1].imm
        regs[r]=imm
    elif mn=='add':
        m=re.match(r'(x\d+), (x\d+), #(0x[0-9a-f]+|\d+)$', ops)
        if m and m.group(2) in regs and regs[m.group(2)] is not None:
            regs[m.group(1)]=regs[m.group(2)]+int(m.group(3),0)
    elif mn=='ldr':
        m=re.match(r'(x\d+), \[(x\d+)(?:, #(0x[0-9a-f]+|\d+))?\]$', ops)
        if m:
            base=regs.get(m.group(2)); d=m.group(1)
            if base is not None:
                addr=base+(int(m.group(3),0) if m.group(3) else 0)
                v=slotval(addr)
                regs[d]=v
                if m.group(3): out.append(('ldr_slot',ins.address,addr,v))
            else: regs[d]=None
    elif mn=='mov':
        m=re.match(r'(x\d+), (x\d+)$', ops)
        if m: regs[m.group(1)]=regs.get(m.group(2))
    elif mn.startswith('bl'):
        t=ops
        out.append(('call',ins.address,t,regs.get('x0')))
    elif mn=='str':
        m=re.match(r'(x\d+), \[(x\d+)(?:, #(0x[0-9a-f]+|\d+))?\]$', ops)
        if m:
            fb=regs.get(m.group(2))
            off2=int(m.group(3),0) if m.group(3) else 0
            # only record when base looks like static_fields (unknown) -> record raw
            out.append(('str',ins.address,m.group(2),off2,regs.get(m.group(1))))
    elif mn=='ret':
        out.append(('ret',ins.address)); break
# print sequence: for calls to op_Implicit, show x0 literal
for e in out:
    if e[0]=='call' and e[2].startswith('0x2aeeb40'):
        v=e[3]; print('IMPLICIT', hex(e[1]), hex(v) if v else None, repr(lit.get(v))[:90] if v in lit else '')
    elif e[0]=='str':
        print('STR', hex(e[1]), e[2], hex(e[3]), hex(e[4]) if e[4] else None, repr(lit.get(e[4]))[:60] if e[4] in lit else '')
