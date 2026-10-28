# -*- coding: utf-8 -*-
"""二进制 AndroidManifest.xml 的最小改写器。

支持两种操作（够用了）：
  1. 删掉指定 class 名开头的元素子树（<service>/<activity>/<receiver> ...）；
  2. 删掉指定元素上的某个属性（例如 <application android:name="com.vyiche.apjrwtd">）。

用法:
  python tools/axml_edit.py in.apk out_manifest.xml --drop-class com.platinmods. --drop-class com.vyiche. \
      --clear-attr application android:name
"""
import struct
import sys
import zipfile

CHUNK_STRING_POOL = 0x0001
CHUNK_RES_MAP = 0x0180
CHUNK_START_NS = 0x0100
CHUNK_END_NS = 0x0101
CHUNK_START_EL = 0x0102
CHUNK_END_EL = 0x0103
CHUNK_CDATA = 0x0104


def read_pool(buf, off):
    hsz = struct.unpack_from("<H", buf, off + 2)[0]
    size, cnt = struct.unpack_from("<II", buf, off + 4)
    flags, sstart = struct.unpack_from("<II", buf, off + 16)
    utf8 = bool(flags & 0x100)
    offs = [struct.unpack_from("<I", buf, off + hsz + 4 * i)[0] for i in range(cnt)]
    base = off + sstart
    out = []
    for o in offs:
        p = base + o
        if utf8:
            n = buf[p]
            p += 2 if n & 0x80 else 1
            n = buf[p]
            p += 2 if n & 0x80 else 1
            out.append(buf[p:p + n].decode("utf-8", "replace"))
        else:
            n = struct.unpack_from("<H", buf, p)[0]
            p += 2
            if n & 0x8000:
                n = ((n & 0x7FFF) << 16) | struct.unpack_from("<H", buf, p)[0]
                p += 2
            out.append(buf[p:p + n * 2].decode("utf-16-le", "replace"))
    return out


def chunk_iter(buf):
    total = struct.unpack_from("<I", buf, 4)[0]
    off = 8
    while off < total:
        ctype, chsz, csize = struct.unpack_from("<HHI", buf, off)
        if csize == 0:
            break
        yield off, ctype, chsz, csize
        off += csize


def start_element_info(buf, off):
    ns, name = struct.unpack_from("<II", buf, off + 16)
    astart, asize, acount = struct.unpack_from("<HHH", buf, off + 24)
    attrs = []
    for i in range(acount):
        p = off + 16 + astart + i * asize
        attrs.append(bytearray(buf[p:p + asize]))
    return ns, name, astart, asize, acount, attrs


def attr_name_index(buf, attr):
    return struct.unpack_from("<I", attr, 4)[0]


def attr_string_value(buf, attr, strings):
    _ns, _n, _raw, _sz, _r0, atype, data = struct.unpack_from("<IIIHBBI", attr, 0)
    if atype == 0x03:
        return strings[data]
    return None


def edit(buf, drop_prefixes, clear_attrs, verbose=True):
    """clear_attrs: {tag_name: set(attr_names)}，例如 {'application': {'android:name'}}"""
    hdr = bytearray(buf[:8])
    chunks = list(chunk_iter(buf))
    strings = None
    for off, ctype, chsz, csize in chunks:
        if ctype == CHUNK_STRING_POOL:
            strings = read_pool(buf, off)
            break
    if strings is None:
        raise SystemExit("no string pool")

    # attr 的 name 索引对应的是全局资源 ID 映射，这里用 string pool 里 "android:name" 等名字做匹配
    out = bytearray(buf[:8])
    i = 0
    while i < len(chunks):
        off, ctype, chsz, csize = chunks[i]
        if ctype == CHUNK_START_EL:
            ns, name, astart, asize, acount, attrs = start_element_info(buf, off)
            tag = strings[name]
            # 0) 先按 clear_attrs 过滤属性，再用剩下的属性判断是否整块删除
            keep0 = attrs
            if tag in clear_attrs:
                ban = clear_attrs[tag]
                keep0 = []
                for a in attrs:
                    aname = strings[attr_name_index(buf, a)]
                    if aname in ban:
                        if verbose:
                            print(f"  drop attr <{tag}> {aname}")
                        continue
                    keep0.append(a)
            # 1) 元素本身要不要删
            drop = False
            for a in keep0:
                v = attr_string_value(buf, a, strings)
                if v and any(v.startswith(pp) for pp in drop_prefixes):
                    drop = True
                    break
            if drop:
                if verbose:
                    print(f"  drop <{tag}>"
                          + (f' name={attr_string_value(buf, attrs[0], strings)}' if attrs else ""))
                depth = 1
                i += 1
                while i < len(chunks) and depth:
                    _o, ct, _h, _s = chunks[i]
                    if ct == CHUNK_START_EL:
                        depth += 1
                    elif ct == CHUNK_END_EL:
                        depth -= 1
                    i += 1
                continue
            # 2) 删属性（上面已经算过）
            keep = keep0
            # 重建 chunk
            body = bytearray(buf[off + 16: off + 16 + astart])
            new = bytearray()
            new += struct.pack("<HHI", CHUNK_START_EL, 16, 16 + astart + asize * len(keep))
            new += buf[off + 8: off + 16]          # lineNumber + comment
            new += body                             # ns, name, astart, asize, ... indexes
            struct.pack_into("<H", new, 28, len(keep))  # attributeCount
            for a in keep:
                new += a
            out += new
        else:
            out += buf[off:off + csize]
        i += 1
    struct.pack_into("<I", out, 4, len(out))
    return bytes(out)


def main():
    src, dst = sys.argv[1], sys.argv[2]
    args = sys.argv[3:]
    drop, clear = [], {}
    i = 0
    while i < len(args):
        if args[i] == "--drop-class":
            drop.append(args[i + 1])
            i += 2
        elif args[i] == "--clear-attr":
            clear.setdefault(args[i + 1], set()).add(args[i + 2])
            i += 3
        else:
            raise SystemExit("bad arg " + args[i])
    with zipfile.ZipFile(src) as z:
        buf = z.read("AndroidManifest.xml")
    out = edit(buf, drop, clear)
    open(dst, "wb").write(out)
    print(f"written {dst}: {len(buf)} -> {len(out)} bytes")


if __name__ == "__main__":
    main()
