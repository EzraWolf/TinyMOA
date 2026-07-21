from enum import IntEnum


class AluOp(IntEnum):
    ADD = 0b0000
    SUB = 0b0001
    SLL = 0b0010
    SRL = 0b0011
    SRA = 0b0100
    AND = 0b0101
    OR = 0b0110
    XOR = 0b0111
    ADDW = 0b1000
    SUBW = 0b1001
    SLLW = 0b1010
    SRLW = 0b1011
    SRAW = 0b1100
    SLT = 0b1101
    SLTU = 0b1110


class FuSrc1(IntEnum):
    NONE = 0
    REG = 1
    PC = 2


class FuSrc2(IntEnum):
    NONE = 0
    REG = 1
    IMM = 2


class WbSel(IntEnum):
    NONE = 0
    MEM = 1
    FU = 2
    PC = 3


class MemOp(IntEnum):
    BYTE = 0b000
    HALF = 0b001
    WORD = 0b010
    DOUBLE = 0b011  # RV64I only
    BYTE_U = 0b100
    HALF_U = 0b101
    WORD_U = 0b110  # RV64I only
