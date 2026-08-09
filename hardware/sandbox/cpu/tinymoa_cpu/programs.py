"""Programs shared with hardware/tests/integration/ecore/test_ecore_top_fibonacci.py."""

from __future__ import annotations

# Local copies of the encoders so the sandbox package does not import the RTL test tree.
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


def addi(rd, rs1, imm):
    return _i(imm, rs1, 0x0, rd, 0x13)


def add(rd, rs1, rs2):
    return _r(0x00, rs2, rs1, 0x0, rd, 0x33)


def beq(rs1, rs2, imm):
    return _b(imm, rs2, rs1, 0x0, 0x63)


def jal(rd, imm):
    return _j(imm, rd, 0x6F)


def sw(rs1, rs2, imm):
    return _s(imm, rs2, rs1, 0x2, 0x23)


FIB_RESULT_ADDR = 0x100
FIB_RESULT = 55

# Identical instruction stream to test_ecore_top_fibonacci.PROGRAM
FIBONACCI = [
    addi(5, 0, 10),  # addi t0, zero, 10
    addi(6, 0, 0),  # addi t1, zero, 0
    addi(7, 0, 1),  # addi t2, zero, 1
    beq(5, 0, 24),  # beq  t0, zero, done
    add(8, 6, 7),  # add  s0, t1, t2
    addi(6, 7, 0),  # addi t1, t2, 0
    addi(7, 8, 0),  # addi t2, s0, 0
    addi(5, 5, -1),  # addi t0, t0, -1
    jal(0, -20),  # jal  zero, loop
    addi(9, 0, 0x100),  # addi s1, zero, 0x100
    sw(9, 6, 0),  # sw   t1, 0(s1)
    jal(0, 0),  # halt: jal zero, halt
]

FIB_HALT_PC = (len(FIBONACCI) - 1) * 4


def imem_from_words(words: list[int]) -> dict[int, int]:
    return {i * 4: w & 0xFFFFFFFF for i, w in enumerate(words)}
