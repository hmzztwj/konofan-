#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tiny straight-line AArch64 tracer for libil2cpp.so: resolves adrp/add/ldr chains
so that data loads of string-literal slots become visible."""
import struct, sys
import capstone
from capstone import Cs, CS_MODE_ARM
from capstone.arm64 import ARM64_OP_REG, ARM64_OP_IMM, ARM64_OP_MEM

PATH = r"F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so"
data = open(PATH, 'rb').read()

phoff = struct.unpack_from('<Q', data, 0x20)[0]
phentsize = struct.unpack_from('<H', data, 0x36)[0]
phnum = struct.unpack_from('<H', data, 0x38)[0]
segs = []
for i in range(phnum):
    o = phoff + i * phentsize
    t, fl = struct.unpack_from('<II', data, o)
    po, pv, pp, pf, pm = struct.unpack_from('<QQQQQ', data, o + 8)
    if t == 1:
        segs.append((pv, pm, po, pf, fl))
base_va = min(s[0] for s in segs)

shoff = struct.unpack_from('<Q', data, 0x28)[0]
shentsize = struct.unpack_from('<H', data, 0x3A)[0]
shnum = struct.unpack_from('<H', data, 0x3C)[0]
reloc = {}
for i in range(shnum):
    o = shoff + i * shentsize
    st = struct.unpack_from('<I', data, o + 4)[0]
    if st == 4:
        so = struct.unpack_from('<Q', data, o + 0x18)[0]
        ss = struct.unpack_from('<Q', data, o + 0x20)[0]
        for k in range(ss // 24):
            ro, ri, ra = struct.unpack_from('<QQq', data, so + k * 24)
            if (ri & 0xFFFFFFFF) == 1027:
                reloc[ro] = base_va + ra


def va2off(va):
    for v, m, o, f, fl in segs:
        if v <= va < v + f:
            return o + (va - v)
    return None


def mem8(va):
    if va in reloc:
        return reloc[va]
    o = va2off(va)
    if o is None:
        return None
    return struct.unpack_from('<Q', data, o)[0]


def ilstr(va):
    o = va2off(va)
    if o is None:
        return None
    ln = struct.unpack_from('<i', data, o + 16)[0]
    if not (0 < ln < 400):
        return None
    raw = data[o + 20:o + 20 + ln * 2]
    if len(raw) < ln * 2:
        return None
    try:
        s = raw.decode('utf-16-le')
    except Exception:
        return None
    return s if all(32 <= ord(c) < 0x3000 for c in s) else None


def main():
    rva = int(sys.argv[1], 16)
    nbytes = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200
    o = va2off(rva)
    md = Cs(capstone.CS_ARCH_AARCH64, CS_MODE_ARM)
    md.detail = True
    R = {}
    for ins in md.disasm(data[o:o + nbytes], rva):
        mn = ins.mnemonic
        ops = ins.operands
        line = "0x%X: %-8s %s" % (ins.address, mn, ins.op_str)
        note = ""
        if mn == 'adrp' and len(ops) == 2:
            R[ins.reg_name(ops[0].reg)] = ops[1].imm
        elif mn == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG:
            b = ins.reg_name(ops[1].reg)
            if b in R:
                R[ins.reg_name(ops[0].reg)] = R[b] + ops[2].imm
        elif mn == 'ldr' and len(ops) == 2 and ops[1].type == ARM64_OP_MEM:
            base = ins.reg_name(ops[1].mem.base)
            if base in R:
                ea = R[base] + ops[1].mem.disp
                pv = mem8(ea)
                if pv is not None:
                    R[ins.reg_name(ops[0].reg)] = pv
                    s = ilstr(pv)
                    note = "  ; slot 0x%X -> 0x%X%s" % (ea, pv, ("  ILSTR=%r" % s) if s else "")
                else:
                    note = "  ; slot 0x%X unreadable" % ea
        elif mn == 'bl' or mn == 'blr':
            for r in list(R):
                if r in ('x0', 'x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8', 'x9', 'x10', 'x11', 'x12', 'x13', 'x14', 'x15', 'x16', 'x17'):
                    R.pop(r, None)
        elif mn in ('mov',) and len(ops) == 2 and ops[1].type == ARM64_OP_REG:
            b = ins.reg_name(ops[1].reg)
            if b in R:
                R[ins.reg_name(ops[0].reg)] = R[b]
        print(line + note)
        if mn == 'ret' and ins.address > rva:
            break


if __name__ == '__main__':
    main()
