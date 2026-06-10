import os
import random
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer
from ...runner import run


WIDTH = int(os.environ.get("WIDTH", 64))
DEPTH = int(os.environ.get("DEPTH", 128))
XLEN_MASK = (1 << WIDTH) - 1


async def setup(dut):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst.value = 0
    dut.i_wen.value = 0
    dut.i_data.value = 0
    dut.i_ren.value = 0

    await ClockCycles(dut.clk, 1)
    dut.rst.value = 1
    await Timer(1, unit="ns")

    await _check_dut(dut)


async def _check_dut(
    dut, rst=1, i_wen=0, i_data=0, o_full=0, i_ren=0, o_data=0, o_empty=1
):
    await Timer(1, unit="ns")
    assert dut.rst.value == rst, f"rst expected {rst}, got {dut.rst.value}"
    assert dut.i_wen.value == i_wen, f"i_wen expected {i_wen}, got {dut.i_wen.value}"
    assert dut.i_data.value == i_data, (
        f"i_data expected {i_data}, got {dut.i_data.value}"
    )
    assert dut.o_full.value == o_full, (
        f"o_full expected {o_full}, got {dut.o_full.value}"
    )
    assert dut.i_ren.value == i_ren, f"i_ren expected {i_ren}, got {dut.i_ren.value}"
    assert dut.o_data.value == o_data, (
        f"o_data expected {o_data}, got {dut.o_data.value}"
    )
    assert dut.o_empty.value == o_empty, (
        f"o_empty expected {o_empty}, got {dut.o_empty.value}"
    )


@cocotb.test()
async def setup_is_proper(dut):
    await setup(dut)
    await _check_dut(dut)

    # TODO: figure out how to test param DEPTH
    assert WIDTH == len(dut.i_data)
    assert WIDTH == len(dut.o_data)


@cocotb.test()
# @cocotb.parametrize(DATA=[0xDEAD,0xBEEF])
# async def write_deasserts_empty(dut, DATA):
async def write_deasserts_empty(dut):
    await setup(dut)
    dut.i_wen.value = 1
    dut.i_data.value = 0xDEAD
    await ClockCycles(dut.clk, 1)
    await _check_dut(dut, i_wen=1, i_data=0xDEAD, o_empty=0)


@cocotb.test()
async def fill_full(dut):
    await setup(dut)
    for _ in range(DEPTH):
        dut.i_wen.value = 1
        dut.i_data.value = random.randint(0, XLEN_MASK)
        await ClockCycles(dut.clk, 1)
    dut.i_wen.value = 0
    dut.i_data.value = 0
    await _check_dut(dut, o_full=1, o_empty=0)


@cocotb.test()
async def write_on_full(dut):
    await setup(dut)
    first = random.randint(0, XLEN_MASK)
    dut.i_wen.value = 1
    dut.i_data.value = first
    await ClockCycles(dut.clk, 1)
    for _ in range(DEPTH - 1):
        dut.i_data.value = random.randint(0, XLEN_MASK)
        await ClockCycles(dut.clk, 1)
    dut.i_wen.value = 0
    dut.i_data.value = 0
    dut.i_ren.value = 1
    await ClockCycles(dut.clk, 1)
    await _check_dut(dut, i_ren=1, o_data=first, o_empty=0)


@cocotb.test()
async def read_empty(dut):
    await setup(dut)
    dut.i_ren.value = 1
    await ClockCycles(dut.clk, 1)
    await _check_dut(dut, i_ren=1, o_empty=1, o_data=0)


@cocotb.test()
async def read_to_empty(dut):
    await setup(dut)
    vals = []
    dut.i_wen.value = 1
    for _ in range(DEPTH):
        v = random.randint(0, XLEN_MASK)
        vals.append(v)
        dut.i_data.value = v
        await ClockCycles(dut.clk, 1)
    dut.i_wen.value = 0
    dut.i_ren.value = 1
    dut.i_data.value = 0
    for v in vals:
        dut.i_ren.value = 1
        await ClockCycles(dut.clk, 1)
        await Timer(1, "ns")
        assert dut.o_data.value == v, f"expected {hex(v)} got {hex(dut.o_data.value)}"
    await _check_dut(dut, i_ren=1, o_empty=1, o_data=vals[-1])


@pytest.mark.parametrize(
    "p",
    [
        {"WIDTH": 32, "DEPTH": 32},
        {"WIDTH": 64, "DEPTH": 32},
        {"WIDTH": 32, "DEPTH": 128},
    ],
)
def test_mem_fifo(p):
    run("mem", "fifo", ["~mem/mem_fifo.sv"], params=p)
