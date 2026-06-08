import cocotb
import random
from enum import Enum
from cocotb.triggers import Timer

X32_MASK = 0xFFFF_FFFF
X64_MASK = 0xFFFF_FFFF_FFFF_FFFF


class AluOp(Enum):
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


async def _alu(dut, i_op: AluOp, i_a, i_b):
    dut.i_op.value = i_op.value
    dut.i_a.value = i_a
    dut.i_b.value = i_b
    await Timer(1, "ns")
    return int(dut.o_res.value)


def _sext32(x: int):
    return x | 0xFFFF_FFFF_0000_0000 if x >> 31 else x


@cocotb.test()
async def add_basic(dut):
    for _ in range(20):
        a = random.randint(0, X64_MASK)
        b = random.randint(0, X64_MASK)
        assert (a + b) & X64_MASK == await _alu(dut, AluOp.ADD, a, b)


@cocotb.test()
async def addw_basic(dut):
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, X32_MASK)
        assert _sext32((a + b) & X32_MASK) == await _alu(dut, AluOp.ADDW, a, b)


@cocotb.test()
async def sub_basic(dut):
    for _ in range(20):
        a = random.randint(0, X64_MASK)
        b = random.randint(0, X64_MASK)
        assert (a - b) & X64_MASK == await _alu(dut, AluOp.SUB, a, b)


@cocotb.test()
async def subw_basic(dut):
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, X32_MASK)
        assert _sext32((a - b) & X32_MASK) == await _alu(dut, AluOp.SUBW, a, b)


@cocotb.test()
async def or_basic(dut):
    for _ in range(20):
        a = random.randint(0, X64_MASK)
        b = random.randint(0, X64_MASK)
        assert (a | b) == await _alu(dut, AluOp.OR, a, b)


@cocotb.test()
async def and_basic(dut):
    for _ in range(20):
        a = random.randint(0, X64_MASK)
        b = random.randint(0, X64_MASK)
        assert (a & b) == await _alu(dut, AluOp.AND, a, b)


@cocotb.test()
async def xor_basic(dut):
    for _ in range(20):
        a = random.randint(0, X64_MASK)
        b = random.randint(0, X64_MASK)
        assert (a ^ b) == await _alu(dut, AluOp.XOR, a, b)
