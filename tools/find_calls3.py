import numpy as np, struct, json, bisect, sys
SO=r'F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so'
buf=open(SO,'rb').read()
e_phoff=struct.unpack_from('<Q',buf,0x20)[0]; e_phentsize=struct.unpack_from('<H',buf,0x36)[0]; e_phnum=struct.unpack_from('<H',buf,0x38)[0]
segs=[]
for i in range(e_phnum):
    off=e_phoff+i*e_phentsize
    p_type,p_flags=struct.unpack_from('<II',buf,off)
    p_offset,p_vaddr,p_paddr,p_filesz=struct.unpack_from('<QQQQ',buf,off+8)
    if p_type==1 and p_filesz: segs.append((p_vaddr,p_offset,p_filesz,p_flags))
want=[int(x,16) for x in sys.argv[1:]]
d=json.load(open(r'tools\il2cppdumper\out570\script.json',encoding='utf-8'))
items=sorted((int(m['Address']), m['Name']) for m in d['ScriptMethod'])
A=[a for a,_ in items]
def name(a):
    i=bisect.bisect_right(A,a)-1
    return items[i][1] if i>=0 else '?'
for va in want:
    hits=[]
    for vaddr,off,sz,flags in segs:
        if not (flags & 1): continue
        n=sz//4
        w=np.frombuffer(buf[off:off+n*4],dtype='<u4')
        m=(w & np.uint32(0xFC000000))==np.uint32(0x94000000)
        idx=np.nonzero(m)[0]
        imm=(w[idx].astype(np.int64) & 0x3FFFFFF)
        imm=np.where(imm>=0x2000000, imm-0x4000000, imm)
        addr=vaddr+idx.astype(np.int64)*4
        tgt=addr+(imm<<2)
        for x in addr[tgt==va]: hits.append(int(x))
    print('== %#x -> %d callers' % (va,len(hits)))
    for a in hits: print('   %#x %s' % (a, name(a)))
