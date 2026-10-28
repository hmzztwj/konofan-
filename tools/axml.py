# -*- coding: utf-8 -*-
"""极简 AXML 解析器：把 AndroidManifest.xml 的标签/属性打印成人能看的样子。

用法: python tools/axml.py <apk|xml> [过滤关键字]
"""
import struct
import sys
import zipfile

RES_STRINGS = {
    0x01010003: "android:name",
    0x01010010: "android:exported",
    0x01010000: "android:theme",
    0x0101020C: "android:minSdkVersion",
    0x0101021B: "android:versionCode",
    0x0101021C: "android:versionName",
    0x01010270: "android:targetSdkVersion",
    0x01010001: "android:label",
    0x01010002: "android:icon",
    0x01010006: "android:permission",
    0x0101020E: "android:launchMode",
    0x0101000E: "android:enabled",
    0x01010018: "android:authorities",
    0x01010024: "android:value",
    0x01010026: "android:resource",
    0x01010223: "android:allowBackup",
    0x01010241: "android:process",
    0x010100AE: "android:screenOrientation",
}

ATTR_TYPE_STR = 0x03
ATTR_TYPE_INT = 0x10
ATTR_TYPE_BOOL = 0x12
ATTR_TYPE_REF = 0x01


def read_string_pool(buf, off):
    typ, hsz, size, cnt, stycnt, flags, strstart, stylestart = struct.unpack_from(
        "<HHIIIIII", buf, off)
    utf8 = bool(flags & 0x100)
    offs = [struct.unpack_from("<I", buf, off + hsz + 4 * i)[0] for i in range(cnt)]
    base = off + strstart
    out = []
    for o in offs:
        p = base + o
        if utf8:
            # u16 字符长度（1/2 字节） + u8 字节长度（1/2 字节）
            n = buf[p]
            p += 2 if n & 0x80 else 1
            n = buf[p]
            p += 2 if n & 0x80 else 1
            s = buf[p:p + n].decode("utf-8", "replace")
        else:
            n = struct.unpack_from("<H", buf, p)[0]
            p += 2
            if n & 0x8000:
                n = (n & 0x7FFF) << 16
                n |= struct.unpack_from("<H", buf, p)[0]
                p += 2
            s = buf[p:p + n * 2].decode("utf-16-le", "replace")
        out.append(s)
    return out, size


def parse(buf, filt=None):
    magic, total = struct.unpack_from("<II", buf, 0)
    assert magic == 0x00080003, hex(magic)
    off = 8
    strings = []
    resmap = []
    depth = 0
    lines = []
    while off < total:
        ctype, chsz, csize = struct.unpack_from("<HHI", buf, off)
        if csize == 0:
            break
        if ctype == 0x0001:
            strings, _ = read_string_pool(buf, off)
        elif ctype == 0x0180:
            n = (csize - chsz) // 4
            resmap = list(struct.unpack_from("<%dI" % n, buf, off + chsz))
        elif ctype == 0x0102:  # START_ELEMENT
            ns, name = struct.unpack_from("<II", buf, off + 16)
            acount = struct.unpack_from("<H", buf, off + 28)[0]
            aoff = off + chsz
            attrs = []
            for i in range(acount):
                p = aoff + i * 20
                ans, aname, raw, asize, res0, atype, data = struct.unpack_from("<IIIHBBI", buf, p)
                key = RES_STRINGS.get(aname) or RES_STRINGS.get(resmap[aname] if aname < len(resmap) else 0)
                key = key or strings[aname]
                if atype == ATTR_TYPE_STR:
                    val = strings[data]
                elif atype == ATTR_TYPE_BOOL:
                    val = "true" if data else "false"
                elif atype == ATTR_TYPE_INT:
                    val = str(struct.unpack("<i", struct.pack("<I", data))[0])
                elif atype == ATTR_TYPE_REF:
                    val = "@0x%08x" % data
                else:
                    val = "0x%08x" % data
                attrs.append((key, val))
            tag = strings[name]
            line = "  " * depth + "<" + tag + "".join(f' {k}="{v}"' for k, v in attrs) + ">"
            if not filt or filt.lower() in line.lower():
                lines.append(line)
            depth += 1
        elif ctype == 0x0103:
            depth -= 1
            ns, name = struct.unpack_from("<II", buf, off + 16)
            tag = strings[name] if name < len(strings) else "?"
            if filt and filt.lower() not in tag.lower():
                pass
            else:
                lines.append("  " * max(depth, 0) + "</" + tag + ">")
        off += csize
    return lines


def main():
    arg = sys.argv[1]
    filt = sys.argv[2] if len(sys.argv) > 2 else None
    if arg.lower().endswith(".apk"):
        with zipfile.ZipFile(arg) as z:
            buf = z.read("AndroidManifest.xml")
    else:
        buf = open(arg, "rb").read()
    for ln in parse(buf, filt):
        print(ln)


if __name__ == "__main__":
    main()
