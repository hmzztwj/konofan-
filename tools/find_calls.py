import numpy as np, struct, sys
SO=r'F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so'
buf=open(SO,'rb').read()
# parse ELF64 program headers
e_phoff=struct.unpack_from('<Q',buf,0x20)[0]
e_phentsize=struct.unpack_from('<H',buf,0x36)[0]
e_phnum=struct.unpack_from('<H',buf,0x38)[0]
segs=[]
for i in range(e_phnum):
    off=e_phoff+i*e_phentsize
    p_type,p_flags=struct.unpack_from('<II',buf,off)
    p_offset,p_vaddr,p_paddr,p_filesz=struct.unpack_from('<QQQQ',buf,off+8)
    if p_type==1 and p_filesz:
        segs.append((p_vaddr,p_offset,p_filesz,p_flags))
print('segments',[(hex(v),hex(o),hex(s),hex(f)) for v,o,s,f in segs])
targets={'DecryptString(2)':0x2E80AC8,'DecryptString(3)':0x2E80FC8,'GenerateKey':0x2E803A0,
         'NetworkDecrypt':0x2E7DC8C,'NetworkEncrypt':0x2E7D0F4,'EncryptString':0x2E7FEBC,
         'EncryptString2':0x2E80640,'get_Pass':0x2E7FC8C,'get_Salt':0x2E7FDA4}
res={k:[] for k in targets}
for vaddr,off,sz,flags in segs:
    if not (flags & 0x1): continue  # ejecutable only
    n=sz//4
    w=np.frombuffer(buf[off:off+n*4],dtype='<u4')
    m=(w & np.uint32(0xFC000000))==np.uint32(0x94000000)
    idx=np.nonzero(m)[0]
    if not len(idx): continue
    imm=(w[idx].astype(np.int64) & 0x3FFFFFF)
    imm=np.where(imm>=0x2000000, imm-0x4000000, imm)
    addr=vaddr+idx.astype(np.int64)*4
    tgt=addr+(imm<<2)
    for k,va in targets.items():
        h=addr[tgt==va]
        if len(h): res[k].extend(int(x) for x in h)
for k,v in res.items():
    print('%-18s callers=%d %s' % (k,len(v),[hex(x) for x in v[:10]]))
import json; json.dump({k:v for k,v in res.items()}, open(r'tools/out/callers.json','w'))
