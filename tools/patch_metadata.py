"""改 IL2CPP global-metadata.dat 里的字符串字面量（等长或更短，只改 bytes + 长度字段）。

用法：python tools/patch_metadata.py <in.dat> <out.dat> <旧串> <新串>

原理：metadata v29 的 stringLiteral 表在 stringLiteralOffset 处，每项 8 字节
{uint32 length; int32 dataIndex}；literal 数据在 stringLiteralDataOffset + dataIndex。
把新串写进原槽位（新串必须 <= 旧串长度），并更新该项的 length 字段即可，
文件大小与所有偏移都不变。
"""
import struct
import sys

SANITY = 0xFAB11BAF


def patch(src, dst, old, new):
    buf = bytearray(open(src, "rb").read())
    sanity, ver = struct.unpack_from("<Ii", buf, 0)
    assert sanity == SANITY, hex(sanity)

    # header 从 offset 8 开始是 (offset,size) 对：stringLiteral, stringLiteralData, string, stringData...
    lit_off, lit_size = struct.unpack_from("<Ii", buf, 8)
    litdata_off, litdata_size = struct.unpack_from("<Ii", buf, 16)
    count = lit_size // 8 if lit_size % 8 == 0 else lit_size // 8
    # 有的版本 size 是字节数，有的（v29+）是条目数；两种都兼容
    if lit_size % 8 == 0 and lit_size // 8 * 8 == lit_size and lit_size < len(buf):
        count = lit_size // 8
    n = 0
    hits = []
    for i in range(count):
        length, data_index = struct.unpack_from("<Ii", buf, lit_off + 8 * i)
        if length == 0 or length > litdata_size:
            continue
        s = bytes(buf[litdata_off + data_index: litdata_off + data_index + length])
        if s == old.encode("utf-8"):
            hits.append((i, length, data_index))
    if not hits:
        raise SystemExit("没找到目标字面量: %r" % old)
    newb = new.encode("utf-8")
    for i, length, data_index in hits:
        if len(newb) > length:
            raise SystemExit("新串比旧串长（%d > %d），无法原地替换" % (len(newb), length))
        start = litdata_off + data_index
        buf[start: start + len(newb)] = newb
        struct.pack_into("<I", buf, lit_off + 8 * i, len(newb))  # 更新长度
        n += 1
        print("patched literal #%d (%d -> %d bytes)" % (i, length, len(newb)))
    open(dst, "wb").write(bytes(buf))
    print("total %d 处" % n)


if __name__ == "__main__":
    patch(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
