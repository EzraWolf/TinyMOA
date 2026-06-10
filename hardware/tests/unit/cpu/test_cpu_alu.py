import os
import random
import pytest
import cocotb
from enum import Enum
from cocotb.triggers import Timer
from ...runner import run


WIDTH = int(os.environ.get("WIDTH", 8))
XLEN_MASK = 2**WIDTH - 1


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


def _sext(x: int, bits: int):
    if x & (1 << (bits - 1)):
        return x | ((-1) << bits)
    return x


@cocotb.test()
async def params_set(dut):
    assert WIDTH == len(dut.i_a)
    assert WIDTH == len(dut.i_b)
    assert WIDTH == len(dut.o_res)


@cocotb.test()
async def add_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = (a + b) & XLEN_MASK
        res = await _alu(dut, AluOp.ADD, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def addw_basic(dut):
    X32_MASK = 0xFFFF_FFFF
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, X32_MASK)
        exp = _sext((a + b) & X32_MASK, 32) & XLEN_MASK
        res = await _alu(dut, AluOp.ADDW, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sub_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = (a - b) & XLEN_MASK
        res = await _alu(dut, AluOp.SUB, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def subw_basic(dut):
    X32_MASK = 0xFFFF_FFFF
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, X32_MASK)
        exp = _sext((a - b) & X32_MASK, 32) & XLEN_MASK
        res = await _alu(dut, AluOp.SUBW, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def or_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = a | b
        res = await _alu(dut, AluOp.OR, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def and_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = a & b
        res = await _alu(dut, AluOp.AND, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def xor_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = a ^ b
        res = await _alu(dut, AluOp.XOR, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def slt_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = 1 if _sext(a, WIDTH) < _sext(b, WIDTH) else 0
        res = await _alu(dut, AluOp.SLT, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sltu_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
        exp = 1 if a < b else 0
        res = await _alu(dut, AluOp.SLTU, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@pytest.mark.parametrize(
    "p",
    [
        {"WIDTH": 8},
        {"WIDTH": 32},
        {"WIDTH": 64},
    ],
)
def test_cpu_alu(p):
    run("cpu", "alu", ["~cpu/cpu_alu.sv", "~cpu/pkgs/pkg_cpu_alu.sv"], params=p)
