# -*- coding: utf-8 -*-
"""最小 CRI CPK 解析器（@UTF 表），用于把 .cpk 里的 HCA 音频按真实文件名拆出来。

CPK 布局:
  0x00 "CPK " + 版本等
  0x10 "@UTF" CpkHeader 表: FileSize / ContentOffset / ContentSize / TocOffset / TocSize / ...
  TocOffset 处 "@UTF" 表名 "Toc": DirName, FileName, FileSize, ExtractSize, FileOffset, ID, UserString

@UTF 表结构:
  0x00 magic '@UTF'  0x04 table_size  0x08 rows_offset  0x0C string_offset
  0x10 data_offset   0x14 name_offset(u32)  0x18 num_columns(u16)  0x1A row_width(u16)
  0x1C num_rows(u32)
  0x20 每列 8 字节: flags(u32) name_offset(u32)
  列名 = string_offset + name_offset
  行: rows_offset 起 row_width 字节/行; 字符串列 = u32 偏移(相对 string_offset);
      数据列 = (u32 offset, u32 size) 相对 data_offset

用法:
  python tools/cpk.py tables <cpk>            # 打印所有 @UTF 表的列名/行数
  python tools/cpk.py list <cpk>              # 列出 CPK 内文件
  python tools/cpk.py extract <cpk> <outdir>  # 导出内部文件
"""
import struct
import sys


class UTFTable:
    def __init__(self, buf, off):
        self.buf = buf
        self.off = off
        if buf[off:off + 4] != b"@UTF":
            raise ValueError("not @UTF at %#x" % off)
        (self.table_size, self.rows_off, self.str_off, self.data_off,
         self.name_off) = struct.unpack_from("<5I", buf, off + 4)
        self.ncols, self.row_width = struct.unpack_from("<HH", buf, off + 0x18)
        self.nrows = struct.unpack_from("<I", buf, off + 0x1C)[0]
        self.cols = []
        for i in range(self.ncols):
            flags, noff = struct.unpack_from("<II", buf, off + 0x20 + i * 8)
            name = self._cstr(self.off + self.str_off + noff)
            self.cols.append((name, flags))

    def _cstr(self, p):
        e = self.buf.index(b"\0", p)
        return self.buf[p:e].decode("utf-8", "replace")

    def rows(self):
        base = self.off + self.rows_off
        for r in range(self.nrows):
            p = base + r * self.row_width
            row = {}
            for name, flags in self.cols:
                t = flags >> 4
                if t == 1:                      # string
                    o = struct.unpack_from("<I", self.buf, p)[0]
                    row[name] = self._cstr(self.off + self.str_off + o) if o else ""
                    p += 4
                elif t == 3:                    # float
                    row[name] = struct.unpack_from("<f", self.buf, p)[0]
                    p += 4
                elif t == 4:                    # u64
                    row[name] = struct.unpack_from("<Q", self.buf, p)[0]
                    p += 8
                elif t == 5:                    # u8
                    row[name] = self.buf[p]
                    p += 1
                elif t == 6:                    # u16
                    row[name] = struct.unpack_from("<H", self.buf, p)[0]
                    p += 2
                elif t == 7:                    # u32
                    row[name] = struct.unpack_from("<I", self.buf, p)[0]
                    p += 4
                elif t == 9:                    # data (offset,size)
                    o, s = struct.unpack_from("<II", self.buf, p)
                    row[name] = (self.off + self.data_off + o, s)
                    p += 8
                else:
                    row[name] = None
                    p += 4
            yield row


def open_cpk(path):
    buf = open(path, "rb").read()
    if buf[:4] != b"CPK ":
        raise ValueError("not CPK")
    off = buf.find(b"@UTF", 0x10)
    hdr = UTFTable(buf, off)
    meta = next(hdr.rows())
    return buf, meta


def toc_rows(buf, meta):
    t = UTFTable(buf, meta["TocOffset"])
    return t, list(t.rows())


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "tables"
    path = sys.argv[2]
    buf, meta = open_cpk(path)
    t, rows = toc_rows(buf, meta)
    if cmd == "tables":
        print("header:", {k: v for k, v in meta.items() if isinstance(v, (int, str))})
        print("toc table:", t.nrows, "rows, cols:", [c[0] for c in t.cols])
        print("first row:", rows[0] if rows else None)
    elif cmd == "list":
        for r in rows:
            print(f"{r.get('DirName','')}/{r.get('FileName','')}  {r.get('ExtractSize')}")
    elif cmd == "extract":
        import os
        outdir = sys.argv[3]
        os.makedirs(outdir, exist_ok=True)
        n = 0
        for r in rows:
            data = r.get("UserString")
            if not isinstance(data, tuple):
                continue
            p, s = data
            d = os.path.join(outdir, r.get("DirName") or "")
            os.makedirs(d, exist_ok=True)
            fn = os.path.join(d, r.get("FileName") or f"f{n}")
            open(fn, "wb").write(buf[p:p + s])
            n += 1
        print("extracted", n)


if __name__ == "__main__":
    main()
