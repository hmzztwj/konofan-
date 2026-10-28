import struct, sys, json
MD = r'F:\python_work\逆向\apk\lib\assets\bin\Data\Managed\Metadata\global-metadata.dat'
data = open(MD,'rb').read()
sanity, ver = struct.unpack_from('<Ii', data, 0)
print('sanity=%08x ver=%d size=%d' % (sanity & 0xffffffff, ver, len(data)))
litOff, litSz, litDataOff, litDataSz = struct.unpack_from('<iiii', data, 8)
strOff, strSz, strDataOff, strDataSz = struct.unpack_from('<iiii', data, 24)
print('litOff=%d litSz=%d litDataOff=%d litDataSz=%d' % (litOff, litSz, litDataOff, litDataSz))
n = litSz // 8
literals = []
for i in range(n):
    ln, di = struct.unpack_from('<Ii', data, litOff + i*8)
    s = data[litDataOff+di: litDataOff+di+ln]
    literals.append(s.decode('utf-8', 'replace'))
print('literals:', n)
json.dump(literals, open(r'tools/out/literals_byindex.json','w',encoding='utf-8'), ensure_ascii=False)

slots = []
for line in open(r'tools/out/implicit.txt', encoding='utf-8'):
    p = line.split()
    if p and p[0] == 'IMPLICIT':
        slots.append(int(p[2], 16))
print('slots:', len(slots))
idx = [(v >> 1) & 0x7fffff for v in slots]
print('index range', min(idx), max(idx))
for i, (v, k) in enumerate(zip(slots, idx)):
    s = literals[k] if k < n else '<OOR>'
    print('%2d %#010x idx=%-6d %r' % (i, v, k, s))
