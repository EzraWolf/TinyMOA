"""
Shared programs for sandbox + RTL lockstep.

Instruction words must stay byte-identical to `tests.common.encode_rv32i`
encodings (enforced by `tests/test_sandbox.py`).
"""

from __future__ import annotations


def _r(funct7, rs2, rs1, funct3, rd, opcode):
    return (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def _i(imm, rs1, funct3, rd, opcode):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def _s(imm, rs2, rs1, funct3, opcode):
    return (
        (((imm >> 5) & 0x7F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | ((imm & 0x1F) << 7)
        | opcode
    )


def _b(imm, rs2, rs1, funct3, opcode):
    return (
        (((imm >> 12) & 1) << 31)
        | (((imm >> 5) & 0x3F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (((imm >> 1) & 0xF) << 8)
        | (((imm >> 11) & 1) << 7)
        | opcode
    )


def _j(imm, rd, opcode):
    return (
        (((imm >> 20) & 1) << 31)
        | (((imm >> 1) & 0x3FF) << 21)
        | (((imm >> 11) & 1) << 20)
        | (((imm >> 12) & 0xFF) << 12)
        | (rd << 7)
        | opcode
    )


FIB_RESULT_ADDR = 0x100
FIB_RESULT = 55

FIBONACCI = [
    _i(10, 0, 0x0, 5, 0x13),  # addi t0, zero, 10
    _i(0, 0, 0x0, 6, 0x13),  # addi t1, zero, 0
    _i(1, 0, 0x0, 7, 0x13),  # addi t2, zero, 1
    _b(24, 0, 5, 0x0, 0x63),  # beq  t0, zero, done
    _r(0x00, 7, 6, 0x0, 8, 0x33),  # add  s0, t1, t2
    _i(0, 7, 0x0, 6, 0x13),  # addi t1, t2, 0
    _i(0, 8, 0x0, 7, 0x13),  # addi t2, s0, 0
    _i(-1 & 0xFFF, 5, 0x0, 5, 0x13),  # addi t0, t0, -1
    _j(-20, 0, 0x6F),  # jal  zero, loop
    _i(0x100, 0, 0x0, 9, 0x13),  # addi s1, zero, 0x100
    _s(0, 6, 9, 0x2, 0x23),  # sw   t1, 0(s1)
    _j(0, 0, 0x6F),  # halt
]

FIB_HALT_PC = (len(FIBONACCI) - 1) * 4


def imem_from_words(words: list[int]) -> dict[int, int]:
    return {i * 4: w & 0xFFFFFFFF for i, w in enumerate(words)}


def run_fibonacci(width: int = 32, depth: int = 32):
    from tinymoa_cpu.top import Core

    return Core(width=width, depth=depth, imem=imem_from_words(FIBONACCI)).run(
        halt_pc=FIB_HALT_PC
    )
