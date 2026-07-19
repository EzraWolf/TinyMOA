import os
import pytest
import cocotb
from random import randint
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 64))
DEPTH = int(os.environ.get("DEPTH", 128))
XLEN_MASK = (1 << WIDTH) - 1


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    dut.rst.value = 0
    dut.i_wen.value = 0
    dut.i_data.value = 0
    dut.i_ren.value = 0

    await FallingEdge(dut.clk)
    dut.rst.value = 1

    await _check(dut)


async def _check(dut, rst=1, i_wen=0, i_data=0, o_full=0, i_ren=0, o_data=0, o_empty=1):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.rst.value == rst
    assert dut.i_wen.value == i_wen
    assert dut.i_data.value == i_data
    assert dut.o_full.value == o_full
    assert dut.i_ren.value == i_ren
    assert dut.o_data.value == o_data
    assert dut.o_empty.value == o_empty


@cocotb.test()
async def proper_io_width(dut):
    await setup(dut)

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
    await FallingEdge(dut.clk)
    await _check(dut, i_wen=1, i_data=0xDEAD, o_empty=0)


@cocotb.test()
async def fill_full(dut):
    await setup(dut)

    for _ in range(DEPTH):
        dut.i_wen.value = 1
        dut.i_data.value = randint(0, XLEN_MASK)
        await FallingEdge(dut.clk)

    dut.i_wen.value = 0
    dut.i_data.value = 0
    await _check(dut, o_full=1, o_empty=0)


@cocotb.test()
async def write_on_full(dut):
    await setup(dut)

    first = randint(0, XLEN_MASK)
    dut.i_wen.value = 1
    dut.i_data.value = first
    await FallingEdge(dut.clk)
    for _ in range(DEPTH - 1):
        dut.i_data.value = randint(0, XLEN_MASK)
        await FallingEdge(dut.clk)

    dut.i_wen.value = 0
    dut.i_data.value = 0
    dut.i_ren.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_ren=1, o_data=first, o_empty=0)


@cocotb.test()
async def read_empty(dut):
    await setup(dut)

    dut.i_ren.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_ren=1, o_empty=1, o_data=0)


@cocotb.test()
async def read_to_empty(dut):
    await setup(dut)

    vals = []
    dut.i_wen.value = 1
    for _ in range(DEPTH):
        v = randint(0, XLEN_MASK)
        vals.append(v)
        dut.i_data.value = v
        await FallingEdge(dut.clk)

    dut.i_wen.value = 0
    dut.i_ren.value = 1
    dut.i_data.value = 0
    for v in vals:
        dut.i_ren.value = 1
        await FallingEdge(dut.clk)
        assert dut.o_data.value == v, f"expected {hex(v)} got {hex(dut.o_data.value)}"
    await _check(dut, i_ren=1, o_empty=1, o_data=vals[-1])


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
