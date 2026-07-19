from enum import IntEnum


class AluOp(IntEnum):
    ADD = 0b0000
    ADDW = 0b0001
    SUB = 0b0010
    SUBW = 0b0011
    OR = 0b0100
    AND = 0b0101
    XOR = 0b0110
    SLT = 0b0111
    SLTU = 0b1000
    SLL = 0b1001
    SLLW = 0b1010
    SRL = 0b1011
    SRLW = 0b1100
    SRA = 0b1101
    SRAW = 0b1110


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
    FU = 1
    PC = 2
    MEM = 3
