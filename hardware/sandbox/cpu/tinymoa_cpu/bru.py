"""Branch unit — port of hardware/rtl/ecore/ecore_bru.veryl."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BruResult:
    taken: bool
    target: int


def bru(
    valid: bool,
    funct3: int,
    pc: int,
    rs1: int,
    rs2: int,
    imm: int,
    width: int = 32,
) -> BruResult:
    m = (1 << width) - 1
    pc &= m
    rs1 &= m
    rs2 &= m
    imm &= m
    if not valid:
        return BruResult(taken=False, target=pc)

    eq = rs1 == rs2
    sa = rs1 - (1 << width) if (rs1 >> (width - 1)) & 1 else rs1
    sb = rs2 - (1 << width) if (rs2 >> (width - 1)) & 1 else rs2
    lt = sa < sb
    ltu = rs1 < rs2
    taken = {
        0b000: eq,
        0b001: not eq,
        0b100: lt,
        0b101: not lt,
        0b110: ltu,
        0b111: not ltu,
    }.get(funct3 & 0x7, False)
    target = ((pc + imm) & m) if taken else pc
    return BruResult(taken=taken, target=target)
