"""Test suite for counter module."""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_counter(dut_counter, is_increment=True):
    clock = Clock(dut_counter.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut_counter.nrst.value = 0
    await ClockCycles(dut_counter.clk, 8)
    dut_counter.nrst.value = 1
    dut_counter.increment.value = 1 if is_increment else 0
    await ClockCycles(dut_counter.clk, 1)


@cocotb.test()
async def test_counter_increment(dut_counter):
    """Test basic counter incrementing."""
    await setup_counter(dut_counter)

    for i in range(100):
        await ClockCycles(dut_counter.clk, 8)
        assert dut_counter.result.value == i, (
            f"Expected {i}, got {dut_counter.result.value}"
        )


@cocotb.test()
async def test_counter_overflow(dut_counter):
    """Test nibble carry propagation and 32b overflow"""
    await setup_counter(dut_counter)

    # Set counter to near max and check carry and value propagation
    await ClockCycles(dut_counter.clk, 7)
    dut_counter.dut_counter.register.value = 0xFFFFFEFF
    await ClockCycles(dut_counter.clk, 1)

    for i in range(16):
        expected = 0xFFFFFFEF + i
        await ClockCycles(dut_counter.clk, 8)
        assert int(dut_counter.carry_out.value) == 0, f"Unexpected carry at {i}"
        assert int(dut_counter.result.value) == expected, (
            f"Expected 0x{expected:X}, got 0x{int(dut_counter.result.value):X}"
        )

    await ClockCycles(dut_counter.clk, 8)
    assert int(dut_counter.carry_out.value) == 1, "Carry should be 1"
    assert int(dut_counter.result.value) == 0xFFFFFFFF, (
        f"Expected 0xFFFFFFFF, got 0x{int(dut_counter.result.value):X}"
    )

    await ClockCycles(dut_counter.clk, 8)
    assert int(dut_counter.carry_out.value) == 0, "Carry should be 0"
    assert int(dut_counter.result.value) == 0, (
        f"Expected 0, got {int(dut_counter.result.value)}"
    )


@cocotb.test()
async def test_counter_conditional_increment(dut_counter):
    """Test counter only increments when increment signal is high."""
    await setup_counter(dut_counter, is_increment=False)
    await ClockCycles(
        dut_counter.clk, 8
    )  # Already incremented by one in setup, doesn't matter though.

    retired = 0
    last_retired = 0
    last_retired2 = 0

    for i in range(100):
        assert dut_counter.result.value == last_retired2, (
            f"Iteration {i}: Expected {last_retired2}, got {dut_counter.result.value}"
        )
        last_retired2 = last_retired
        await ClockCycles(dut_counter.clk, 7)
        last_retired = retired
        x = random.randint(0, 1)
        retired += x
        dut_counter.increment.value = x
        await ClockCycles(dut_counter.clk, 1)
