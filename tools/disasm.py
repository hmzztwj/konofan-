#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Disassemble a function from libil2cpp.so by RVA, annotate adrp/ldr targets,
apply R_AARCH64_RELATIVE relocs, dereference pointers, decode Il2CppString."""
import struct, sys, re
import capstone
from capstone import Cs, CS_MODE_ARM
from capstone.arm64 import ARM64_OP_MEM

PATH = r"F:\python_work\逆向\apk\lib\lib\arm64-v8a\libil2cpp.so"
data = open(PATH, 'rb').read()

e_phoff = struct.unpack_from('<Q', data, 0x20)[0]
e_phentsize = struct.unpack_from('<H', data, 0x36)[0]
e_phnum = struct.unpack_from('<H', data, 0x38)[0]
segs = []
for i in range(e_phnum):
    off = e_phoff + i * e_phentsize
    p_type, p_flags = struct.unpack_from('<II', data, off)
    p_offset, p_vaddr, p_paddr, p_filesz, p_memsz = struct.unpack_from('<QQQQQ', data, off + 8)
    if p_type == 1:
        segs.append((p_vaddr, p_memsz, p_offset, p_filesz, p_flags))
base_va = min(s[0] for s in segs)


def va2off(va):
    for v, s, o, f, fl in segs:
        if v <= va < v + f:
            return o + (va - v)
    return None


# ---- apply R_AARCH64_RELATIVE relocations ----
e_shoff = struct.unpack_from('<Q', data, 0x28)[0]
e_shentsize = struct.unpack_from('<H', data, 0x3A)[0]
e_shnum = struct.unpack_from('<H', data, 0x3C)[0]
reloc = {}
for i in range(e_shnum):
    off = e_shoff + i * e_shentsize
    sh_type = struct.unpack_from('<I', data, off + 4)[0]
    if sh_type == 4:  # SHT_RELA
        sh_offset = struct.unpack_from('<Q', data, off + 0x18)[0]
        sh_size = struct.unpack_from('<Q', data, off + 0x20)[0]
        for k in range(sh_size // 24):
            r_off, r_info, r_add = struct.unpack_from('<QQq', data, sh_offset + k * 24)
            if (r_info & 0xFFFFFFFF) == 1027:  # R_AARCH64_RELATIVE
                reloc[r_off] = base_va + r_add


def rd(va, n):
    o = va2off(va)
    if o is None:
        return None
    return data[o:o + n]


def read_ptr(va):
    if va in reloc:
        return reloc[va]
    b = rd(va, 8)
    return struct.unpack('<Q', b)[0] if b and len(b) == 8 else None


def try_il2cpp_str(va):
    """Il2CppString: [klass*][monitor*][int32 len][utf16 chars...]"""
    b = rd(va, 20)
    if not b or len(b) < 20:
        return None
    ln = struct.unpack_from('<i', b, 16)[0]
    if not (0 < ln < 400):
        return None
    cb = rd(va + 20, ln * 2)
    if not cb or len(cb) < ln * 2:
        return None
    try:
        s = cb.decode('utf-16-le')
    except Exception:
        return None
    if all(32 <= ord(c) < 0x3000 for c in s):
        return s
    return None


def main():
    rva = int(sys.argv[1], 16)
    nbytes = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x200
    b = rd(rva, nbytes)
    md = Cs(capstone.CS_ARCH_AARCH64, CS_MODE_ARM)
    md.detail = True
    regs = {}
    for ins in md.disasm(b, rva):
        line = "0x%X: %-8s %s" % (ins.address, ins.mnemonic, ins.op_str)
        notes = []
        if ins.mnemonic == 'adrp' and len(ins.operands) == 2:
            regs[ins.reg_name(ins.operands[0].reg)] = ins.operands[1].imm
        for op in ins.operands:
            if op.type == ARM64_OP_MEM and op.mem.base != 0:
                base = ins.reg_name(op.mem.base)
                if base in regs:
                    ea = regs[base] + op.mem.disp
                    if ins.mnemonic in ('ldr', 'ldrb'):
                        pv = read_ptr(ea)
                        if pv and pv > 0x1000:
                            s = try_il2cpp_str(pv)
                            notes.append("[0x%X]=0x%X%s" % (ea, pv, (" str=%r" % s) if s else ""))
                        else:
                            notes.append("[0x%X]=%s" % (ea, pv))
        if notes:
            line += "    ; " + " | ".join(notes)
        print(line)
        if ins.mnemonic == 'ret' and ins.address > rva:
            break


if __name__ == '__main__':
    main()
