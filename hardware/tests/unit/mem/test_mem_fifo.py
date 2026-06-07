import os
import cocotb
import random
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


@cocotb.test()
async def params_set(dut):
    await setup(dut)
    assert WIDTH == len(dut.i_data)
    assert WIDTH == len(dut.o_data)

    # depth...?


@cocotb.test()
async def reset_empty(dut):
    await setup(dut)
    assert dut.o_empty.value
    assert not dut.o_full.value
    assert dut.o_data.value == 0
