"""ALU ops matching hardware/rtl/ecore/ecore_alu.veryl (XLEN=32 path)."""

from __future__ import annotations

from tinymoa_cpu.types import AluOp


def _mask(width: int) -> int:
    return (1 << width) - 1


def _sext(value: int, bits: int, width: int) -> int:
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        value |= ~((1 << bits) - 1)
    return value & _mask(width)


def alu(op: AluOp, a: int, b: int, width: int = 32) -> int:
    m = _mask(width)
    a &= m
    b &= m
    shamt = b & (width - 1)

    if op == AluOp.ADD:
        return (a + b) & m
    if op == AluOp.SUB:
        return (a - b) & m
    if op == AluOp.AND:
        return a & b
    if op == AluOp.OR:
        return a | b
    if op == AluOp.XOR:
        return a ^ b
    if op == AluOp.SLL:
        return (a << shamt) & m
    if op == AluOp.SRL:
        return (a >> shamt) & m
    if op == AluOp.SRA:
        signed_a = a - (1 << width) if (a >> (width - 1)) & 1 else a
        return (signed_a >> shamt) & m
    if op == AluOp.SLT:
        sa = a - (1 << width) if a >> (width - 1) else a
        sb = b - (1 << width) if b >> (width - 1) else b
        return 1 if sa < sb else 0
    if op == AluOp.SLTU:
        return 1 if a < b else 0

    # RV64 W-ops: keep for WIDTH>=64 callers; unused on RV32 path
    if op == AluOp.ADDW:
        return _sext((a + b) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SUBW:
        return _sext((a - b) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SLLW:
        return _sext((a << (b & 31)) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SRLW:
        return _sext(((a & 0xFFFFFFFF) >> (b & 31)) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SRAW:
        wa = _sext(a & 0xFFFFFFFF, 32, 32)
        return _sext((wa >> (b & 31)) & 0xFFFFFFFF, 32, width)

    return 0


def branch_taken(funct3: int, rs1: int, rs2: int, width: int = 32) -> bool:
    m = _mask(width)
    rs1 &= m
    rs2 &= m
    eq = rs1 == rs2
    sa = rs1 - (1 << width) if rs1 >> (width - 1) else rs1
    sb = rs2 - (1 << width) if rs2 >> (width - 1) else rs2
    lt = sa < sb
    ltu = rs1 < rs2
    return {
        0b000: eq,
        0b001: not eq,
        0b100: lt,
        0b101: not lt,
        0b110: ltu,
        0b111: not ltu,
    }.get(funct3 & 0x7, False)
