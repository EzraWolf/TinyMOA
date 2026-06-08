import os
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Timer

# parameters
WIDTH = int(os.environ.get("WIDTH", 64))
DEPTH = int(os.environ.get("DEPTH", 128))


async def setup(dut):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rst.value = 1
    dut.i_wen.value = 0
    dut.i_data.value = 0
    dut.i_ren.value = 0

    await ClockCycles(dut.clk, 1)
    dut.rst.value = 0
    await Timer(1, unit="ns")
    dut.rst.value = 1
    await ClockCycles(dut.clk, 1)


async def _check_dut(
    dut, rst=1, i_wen=0, i_data=0, o_full=0, i_ren=0, o_data=0, o_empty=1
):
    await Timer(1, unit="ns")
    assert int(dut.rst.value) == rst
    assert int(dut.i_wen.value) == i_wen
    assert int(dut.i_data.value) == i_data
    assert int(dut.o_full.value) == o_full
    assert int(dut.i_ren.value) == i_ren
    assert int(dut.o_data.value) == o_data
    assert int(dut.o_empty.value) == o_empty


@cocotb.test()
async def params_set(dut):
    await setup(dut)
    assert WIDTH == len(dut.i_data)
    assert WIDTH == len(dut.o_data)

    # TODO: figure out how to test param DEPTH


@cocotb.test()
async def reset_empty(dut):
    await setup(dut)
    await _check_dut(dut)


@cocotb.test()
async def write_deasserts_empty(dut):
    await setup(dut)
    dut.i_wen.value = 1
    dut.i_data.value = 0xDEAD
    await ClockCycles(dut.clk, 1)
    await _check_dut(dut, i_wen=1, i_data=0xDEAD, o_empty=0)
