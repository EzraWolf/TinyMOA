import os
import cocotb
import pytest
from random import randint
from cocotb.triggers import Timer

from tests import CHECK_DELAY_NS, N_FUZZ
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
XLEN_MASK = (1 << WIDTH) - 1


async def _check(
    dut,
    i_valid=0,
    i_op=0,
    i_pc=0,
    i_rs1_data=0,
    i_rs2_data=0,
    i_imm=0,
    o_taken=0,
    o_pc=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.i_valid.value == i_valid
    assert dut.i_op.value == i_op
    assert dut.i_pc.value == i_pc
    assert dut.i_rs1_data.value == i_rs1_data
    assert dut.i_rs2_data.value == i_rs2_data
    assert dut.i_imm.value == i_imm
    assert dut.o_taken.value == o_taken
    assert dut.o_pc.value == o_pc


async def _branch(dut, op, data1, data2, taken, pc=None, imm=None):
    pc = randint(0, XLEN_MASK) if pc is None else pc
    imm = randint(-2048, 2047) * 2 if imm is None else imm
    dut.i_valid.value = 1
    dut.i_op.value = op
    dut.i_pc.value = pc
    dut.i_rs1_data.value = data1
    dut.i_rs2_data.value = data2
    dut.i_imm.value = imm & XLEN_MASK
    await _check(
        dut,
        i_valid=1,
        i_op=op,
        i_pc=pc,
        i_rs1_data=data1,
        i_rs2_data=data2,
        i_imm=imm & XLEN_MASK,
        o_taken=taken,
        o_pc=(pc + imm) & XLEN_MASK if taken else pc,
    )


@cocotb.test()
async def proper_io_widths(dut):
    assert WIDTH == len(dut.i_pc)
    assert WIDTH == len(dut.i_rs1_data)
    assert WIDTH == len(dut.i_rs2_data)
    assert WIDTH == len(dut.i_imm)
    assert WIDTH == len(dut.o_pc)


@cocotb.test()
async def beq_equal_taken(dut):
    for _ in range(N_FUZZ):
        data = randint(0, XLEN_MASK)
        await _branch(dut, 0b000, data, data, 1)


@cocotb.test()
async def beq_unequal_not_taken(dut):
    for _ in range(N_FUZZ):
        data = randint(0, XLEN_MASK)
        await _branch(dut, 0b000, data, data ^ 1, 0)


@cocotb.test()
async def bne_unequal_taken(dut):
    for _ in range(N_FUZZ):
        data = randint(0, XLEN_MASK)
        await _branch(dut, 0b001, data, data ^ 1, 1)


@cocotb.test()
async def bne_equal_not_taken(dut):
    for _ in range(N_FUZZ):
        data = randint(0, XLEN_MASK)
        await _branch(dut, 0b001, data, data, 0)


@cocotb.test()
async def blt_signed_less_taken(dut):
    for i in range(N_FUZZ):
        if i % 2 == 0:
            data1 = randint(1 << (WIDTH - 1), XLEN_MASK)
            data2 = randint(0, (1 << (WIDTH - 1)) - 1)
        else:
            data1 = randint(0, (1 << (WIDTH - 1)) - 2)
            data2 = randint(data1 + 1, (1 << (WIDTH - 1)) - 1)
        await _branch(dut, 0b100, data1, data2, 1)


@cocotb.test()
async def blt_signed_greater_equal_not_taken(dut):
    for i in range(N_FUZZ):
        data1 = randint(0, (1 << (WIDTH - 1)) - 1)
        if i % 2 == 0:
            data2 = data1
        else:
            data2 = randint(1 << (WIDTH - 1), XLEN_MASK)
        await _branch(dut, 0b100, data1, data2, 0)


@cocotb.test()
async def bge_signed_greater_equal_taken(dut):
    for i in range(N_FUZZ):
        data1 = randint(0, (1 << (WIDTH - 1)) - 1)
        if i % 3 == 0:
            data2 = data1
        elif i % 3 == 1:
            data2 = randint(1 << (WIDTH - 1), XLEN_MASK)
        else:
            data1 = randint(1, (1 << (WIDTH - 1)) - 1)
            data2 = randint(0, data1 - 1)
        await _branch(dut, 0b101, data1, data2, 1)


@cocotb.test()
async def bge_signed_less_not_taken(dut):
    for i in range(N_FUZZ):
        if i % 2 == 0:
            data1 = randint(1 << (WIDTH - 1), XLEN_MASK)
            data2 = randint(0, (1 << (WIDTH - 1)) - 1)
        else:
            data1 = randint(0, (1 << (WIDTH - 1)) - 2)
            data2 = randint(data1 + 1, (1 << (WIDTH - 1)) - 1)
        await _branch(dut, 0b101, data1, data2, 0)


@cocotb.test()
async def bltu_less_taken(dut):
    for _ in range(N_FUZZ):
        data1 = randint(0, XLEN_MASK - 1)
        data2 = randint(data1 + 1, XLEN_MASK)
        await _branch(dut, 0b110, data1, data2, 1)


@cocotb.test()
async def bltu_greater_equal_not_taken(dut):
    for i in range(N_FUZZ):
        data1 = randint(0, XLEN_MASK)
        if i % 2 == 0:
            data2 = data1
        else:
            data2 = randint(0, data1)
        await _branch(dut, 0b110, data1, data2, 0)


@cocotb.test()
async def bgeu_greater_equal_taken(dut):
    for i in range(N_FUZZ):
        data1 = randint(0, XLEN_MASK)
        if i % 2 == 0:
            data2 = data1
        else:
            data2 = randint(0, data1)
        await _branch(dut, 0b111, data1, data2, 1)


@cocotb.test()
async def bgeu_less_not_taken(dut):
    for _ in range(N_FUZZ):
        data1 = randint(0, XLEN_MASK - 1)
        data2 = randint(data1 + 1, XLEN_MASK)
        await _branch(dut, 0b111, data1, data2, 0)


@cocotb.test()
async def taken_target_positive(dut):
    await _branch(dut, 0b000, 1, 1, 1, pc=0x100, imm=8)


@cocotb.test()
async def taken_target_negative(dut):
    await _branch(dut, 0b000, 1, 1, 1, pc=0x100, imm=-8)


@cocotb.test()
async def taken_target_wraps(dut):
    await _branch(dut, 0b000, 1, 1, 1, pc=XLEN_MASK - 3, imm=8)


@cocotb.test()
async def invalid_op_not_taken(dut):
    for op in (0b010, 0b011):
        dut.i_valid.value = 1
        dut.i_op.value = op
        dut.i_pc.value = 4
        dut.i_rs1_data.value = 1
        dut.i_rs2_data.value = 1
        dut.i_imm.value = 8
        await _check(
            dut,
            i_valid=1,
            i_op=op,
            i_pc=4,
            i_rs1_data=1,
            i_rs2_data=1,
            i_imm=8,
            o_pc=4,
        )


@cocotb.test()
async def invalid_input_not_taken(dut):
    dut.i_valid.value = 0
    dut.i_op.value = 0
    dut.i_pc.value = 4
    dut.i_rs1_data.value = 0
    dut.i_rs2_data.value = 0
    dut.i_imm.value = 8
    await _check(dut, i_pc=4, i_imm=8, o_pc=4)


@pytest.mark.parametrize("p", [{"WIDTH": 32}, {"WIDTH": 64}])
def test_cpu_bru(p):
    run("cpu", "bru", ["~cpu/cpu_bru.sv"], params=p)
