"""ALU ops matching hardware/rtl/ecore/ecore_alu.veryl."""

from __future__ import annotations

from tinymoa_cpu.types import AluOp


def _mask(width: int) -> int:
    return (1 << width) - 1


def _as_signed(value: int, width: int) -> int:
    value &= _mask(width)
    if value >> (width - 1):
        return value - (1 << width)
    return value


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
        return (_as_signed(a, width) >> shamt) & m
    if op == AluOp.SLT:
        return 1 if _as_signed(a, width) < _as_signed(b, width) else 0
    if op == AluOp.SLTU:
        return 1 if a < b else 0
    if op == AluOp.ADDW:
        return _sext((a + b) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SUBW:
        return _sext((a - b) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SLLW:
        return _sext((a << (b & 31)) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SRLW:
        return _sext(((a & 0xFFFFFFFF) >> (b & 31)) & 0xFFFFFFFF, 32, width)
    if op == AluOp.SRAW:
        return _sext((_as_signed(a & 0xFFFFFFFF, 32) >> (b & 31)) & 0xFFFFFFFF, 32, width)
    raise ValueError(f"unknown AluOp: {op!r}")
