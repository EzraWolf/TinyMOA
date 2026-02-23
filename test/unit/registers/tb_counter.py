"""Test suite for counter module."""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_counter_increment(dut):
    """Test basic counter incrementing."""
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.rstn.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rstn.value = 1
    dut.increment.value = 1
    await ClockCycles(dut.clk, 1)

    for i in range(20):
        await ClockCycles(dut.clk, 8)
        assert dut.val.value == i, f"Expected {i}, got {dut.val.value}"


@cocotb.test()
async def test_counter_overflow(dut):
    """Test nibble carry propagation and 32b overflow"""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.rstn.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rstn.value = 1
    dut.increment.value = 1
    await ClockCycles(dut.clk, 1)

    # Set counter to near max and check carry and value propagation
    await ClockCycles(dut.clk, 7)
    dut.dut.register.value = 0xFFFFFEFF
    await ClockCycles(dut.clk, 1)

    for i in range(16):
        expected = 0xFFFFFFEF + i
        await ClockCycles(dut.clk, 8)
        assert int(dut.cy.value) == 0, f"Unexpected carry at {i}"
        assert int(dut.val.value) == expected, (
            f"Expected 0x{expected:X}, got 0x{int(dut.val.value):X}"
        )

    await ClockCycles(dut.clk, 8)
    assert int(dut.cy.value) == 1, "Carry should be 1"
    assert int(dut.val.value) == 0xFFFFFFFF, (
        f"Expected 0xFFFFFFFF, got 0x{int(dut.val.value):X}"
    )

    await ClockCycles(dut.clk, 8)
    assert int(dut.cy.value) == 0, "Carry should be 0"
    assert int(dut.val.value) == 0, f"Expected 0, got {int(dut.val.value)}"


@cocotb.test()
async def test_counter_conditional_increment(dut):
    """Test counter only increments when increment signal is high."""
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.rstn.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rstn.value = 1
    dut.increment.value = 0
    await ClockCycles(dut.clk, 8)

    retired = 0
    last_retired = 0
    last_retired2 = 0

    for i in range(100):
        assert dut.val.value == last_retired2, (
            f"Iteration {i}: Expected {last_retired2}, got {dut.val.value}"
        )
        last_retired2 = last_retired
        await ClockCycles(dut.clk, 7)
        last_retired = retired
        x = random.randint(0, 1)
        retired += x
        dut.increment.value = x
        await ClockCycles(dut.clk, 1)
