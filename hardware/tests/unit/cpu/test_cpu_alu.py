import os
import random
import pytest
import cocotb
from enum import Enum
from cocotb.triggers import Timer
from ...runner import run


WIDTH = int(os.environ.get("WIDTH", 8))
SHAMT_MASK = (1 << (WIDTH.bit_length() - 1)) - 1
XLEN_MASK = (1 << WIDTH) - 1
X32_MASK = 0xFFFF_FFFF


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


@cocotb.test()
async def add_carry(dut):
    exp = (XLEN_MASK + XLEN_MASK) & XLEN_MASK
    res = await _alu(dut, AluOp.ADD, XLEN_MASK, XLEN_MASK)
    assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def add_wrap(dut):
    exp = (XLEN_MASK + 1) & XLEN_MASK
    res = await _alu(dut, AluOp.ADD, XLEN_MASK, 1)
    assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def addw_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
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


@cocotb.test()
async def sub_borrow(dut):
    exp = (0 - 1) & XLEN_MASK
    res = await _alu(dut, AluOp.SUB, 0, 1)
    assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sub_borrow_one(dut):
    exp = (0 - XLEN_MASK) & XLEN_MASK
    res = await _alu(dut, AluOp.SUB, 0, XLEN_MASK)
    assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def subw_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, XLEN_MASK)
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


@cocotb.test()
async def slt_equal(dut):
    res = await _alu(dut, AluOp.SLT, 42, 42)
    assert res == 0, f"expected 0 got {hex(res)}"


@cocotb.test()
async def slt_neg(dut):
    res = await _alu(dut, AluOp.SLT, XLEN_MASK, 0)
    assert res == 1, f"expected 1 got {hex(res)}"


@cocotb.test()
async def slt_pos(dut):
    res = await _alu(dut, AluOp.SLT, 0, XLEN_MASK)
    assert res == 0, f"expected 0 got {hex(res)}"


@cocotb.test()
async def sltu_equal(dut):
    res = await _alu(dut, AluOp.SLTU, 42, 42)
    assert res == 0, f"expected 0 got {hex(res)}"


@cocotb.test()
async def sltu_zero(dut):
    res = await _alu(dut, AluOp.SLTU, 0, XLEN_MASK)
    assert res == 1, f"expected 1 got {hex(res)}"


@cocotb.test()
async def sltu_max(dut):
    res = await _alu(dut, AluOp.SLTU, XLEN_MASK, 0)
    assert res == 0, f"expected 0 got {hex(res)}"


@cocotb.test()
async def sll_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, SHAMT_MASK)
        exp = (a << b) & XLEN_MASK
        res = await _alu(dut, AluOp.SLL, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def srl_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, SHAMT_MASK)
        exp = a >> b
        res = await _alu(dut, AluOp.SRL, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sra_basic(dut):
    for _ in range(20):
        a = random.randint(0, XLEN_MASK)
        b = random.randint(0, SHAMT_MASK)
        exp = (_sext(a, WIDTH) >> b) & XLEN_MASK
        res = await _alu(dut, AluOp.SRA, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sll_shift_out(dut):
    msb = 1 << (WIDTH - 1)
    res = await _alu(dut, AluOp.SLL, msb, SHAMT_MASK)
    assert res == 0, f"expected 0 got {hex(res)}"


@cocotb.test()
async def srl_fill_zero(dut):
    exp = XLEN_MASK >> SHAMT_MASK
    res = await _alu(dut, AluOp.SRL, XLEN_MASK, SHAMT_MASK)
    assert res == exp, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test()
async def sra_fill_sign(dut):
    res = await _alu(dut, AluOp.SRA, XLEN_MASK, SHAMT_MASK)
    assert res == XLEN_MASK, f"expected {hex(XLEN_MASK)} got {hex(res)}"


@cocotb.test()
async def sra_fill_zero(dut):
    pos = XLEN_MASK >> 1
    exp = pos >> SHAMT_MASK
    res = await _alu(dut, AluOp.SRA, pos, SHAMT_MASK)
    assert res == exp, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def sllw_basic(dut):
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, SHAMT_MASK)
        exp = _sext((a << b) & X32_MASK, 32) & XLEN_MASK
        res = await _alu(dut, AluOp.SLLW, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def srlw_basic(dut):
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, SHAMT_MASK)
        exp = _sext(a >> b, 32) & XLEN_MASK
        res = await _alu(dut, AluOp.SRLW, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def sraw_basic(dut):
    for _ in range(20):
        a = random.randint(0, X32_MASK)
        b = random.randint(0, SHAMT_MASK)
        sra32 = (_sext(a, 32) >> b) & X32_MASK
        exp = _sext(sra32, 32) & XLEN_MASK
        res = await _alu(dut, AluOp.SRAW, a, b)
        assert exp == res, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def sllw_sign(dut):
    exp = _sext(0x80000000, 32) & XLEN_MASK
    res = await _alu(dut, AluOp.SLLW, 0x40000000, 1)
    assert res == exp, f"expected {hex(exp)} got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def srlw_no_sign(dut):
    res = await _alu(dut, AluOp.SRLW, 0x80000001, 1)
    assert res == 0x40000000, f"expected 0x40000000 got {hex(res)}"


@cocotb.test(skip=(WIDTH < 64))
async def sraw_sign(dut):
    res = await _alu(dut, AluOp.SRAW, 0x80000000, 1)
    exp = _sext(0xC0000000, 32) & XLEN_MASK
    assert res == exp, f"expected {hex(exp)} got {hex(res)}"


@pytest.mark.parametrize(
    "p",
    [
        {"WIDTH": 8},
        {"WIDTH": 32},
        {"WIDTH": 64},
        {"WIDTH": 128},
    ],
)
def test_cpu_alu(p):
    run("cpu", "alu", ["~cpu/cpu_alu.sv", "~cpu/pkgs/pkg_cpu_alu.sv"], params=p)
