# -*- coding: utf-8 -*-
"""最小 dex 补丁器：把指定方法的第一条指令改成 return-void（0x000e）。

用途：把 com.platinmods.PMLauncher.init(Activity) 变成空函数，
这样 Unity 的主 Activity 就不会去加载 libplatinmods.so。

用法: python tools/dex_patch.py <in.dex> <out.dex> <Lcom/x/Y;> <methodName> [proto]
"""
import struct
import sys


class Dex:
    def __init__(self, buf):
        self.buf = bytearray(buf)
        (self.string_ids_size, self.string_ids_off,
         self.type_ids_size, self.type_ids_off,
         self.proto_ids_size, self.proto_ids_off,
         self.field_ids_size, self.field_ids_off,
         self.method_ids_size, self.method_ids_off,
         self.class_defs_size, self.class_defs_off) = struct.unpack_from("<12I", buf, 56)

    def u32(self, off):
        return struct.unpack_from("<I", self.buf, off)[0]

    def string_data(self, idx):
        off = self.u32(self.string_ids_off + 4 * idx)
        p = off
        while self.buf[p] & 0x80:
            p += 1
        p += 1
        e = self.buf.index(b"\x00", p)
        return self.buf[p:e].decode("utf-8", "replace")

    def type_name(self, idx):
        return self.string_data(self.u32(self.type_ids_off + 4 * idx))

    def method_name(self, idx):
        return self.string_data(self.u32(self.method_ids_off + 8 * idx + 4))

    def method_class(self, idx):
        return self.type_name(struct.unpack_from("<H", self.buf, self.method_ids_off + 8 * idx)[0])

    def method_proto(self, idx):
        proto_idx = struct.unpack_from("<H", self.buf, self.method_ids_off + 8 * idx + 2)[0]
        ret_idx = self.u32(self.proto_ids_off + 12 * proto_idx + 4)
        params_off = self.u32(self.proto_ids_off + 12 * proto_idx + 8)
        ret = self.type_name(ret_idx)
        params = ""
        if params_off:
            n = self.u32(params_off)
            params = "".join(self.type_name(struct.unpack_from("<H", self.buf, params_off + 4 + 2 * i)[0]) for i in range(n))
        return "(" + params + ")" + ret


def uleb(buf, p):
    r = 0
    s = 0
    while True:
        b = buf[p]
        p += 1
        r |= (b & 0x7F) << s
        if not (b & 0x80):
            return r, p
        s += 7


def fix_header(buf):
    """重算 dex 的 SHA-1 签名与 Adler-32 校验和（否则 ART 可能拒绝加载）。"""
    import hashlib
    import zlib
    buf[12:32] = hashlib.sha1(bytes(buf[32:])).digest()
    struct.pack_into("<I", buf, 8, zlib.adler32(bytes(buf[12:])) & 0xFFFFFFFF)


def patch(inp, outp, cls, mname, proto=None):
    d = Dex(open(inp, "rb").read())
    # 找 method_id
    target = None
    for mi in range(d.method_ids_size):
        if d.method_name(mi) != mname:
            continue
        if d.method_class(mi) != cls:
            continue
        if proto and d.method_proto(mi) != proto:
            continue
        target = mi
        print(f"[+] 找到 method_id #{mi}: {cls}->{mname}{d.method_proto(mi)}")
        break
    if target is None:
        raise SystemExit("method not found")

    # 遍历 class_defs 找 class_data，再找该 method 的 code_off
    for ci in range(d.class_defs_size):
        base = d.class_defs_off + 32 * ci
        class_idx = d.u32(base)
        if d.type_name(class_idx) != cls:
            continue
        class_data_off = d.u32(base + 24)
        if not class_data_off:
            continue
        p = class_data_off
        sf, p = uleb(d.buf, p)
        inf, p = uleb(d.buf, p)
        dm, p = uleb(d.buf, p)
        vm, p = uleb(d.buf, p)
        for _ in range(sf + inf):      # 跳过 encoded_field（field_idx_diff + access_flags）
            _, p = uleb(d.buf, p)
            _, p = uleb(d.buf, p)
        for count, is_direct in ((dm, True), (vm, False)):
            midx = 0
            for _ in range(count):
                diff, p = uleb(d.buf, p)
                access, p = uleb(d.buf, p)
                code_off, p = uleb(d.buf, p)
                midx += diff
                if midx == target and code_off:
                    insns = code_off + 16
                    print(f"[+] code_item @0x{code_off:x}, 第一条指令 0x{struct.unpack_from('<H', d.buf, insns)[0]:04x} -> 0x000e")
                    struct.pack_into("<H", d.buf, insns, 0x000E)
                    fix_header(d.buf)
                    open(outp, "wb").write(d.buf)
                    return
    raise SystemExit("code_off not found")


if __name__ == "__main__":
    patch(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4],
          sys.argv[5] if len(sys.argv) > 5 else None)
