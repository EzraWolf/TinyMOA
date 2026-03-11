"""Test suite for minimal CSR module (cycle counter)."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup(dut):
    """Initialize CSR module with clock and reset."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.csr_addr.value = 0
    dut.csr_read.value = 0
    await ClockCycles(dut.clk, 2)
    dut.nrst.value = 1
    await ClockCycles(dut.clk, 1)


async def read_csr(dut, addr):
    """Read a CSR over a full nibble rotation, returns 32-bit value."""
    dut.csr_addr.value = addr
    dut.csr_read.value = 1

    # Full 8 cycle read
    await ClockCycles(dut.clk, 8)

    val = int(dut.csr_rdata.value)
    dut.csr_read.value = 0
    return val


@cocotb.test()
async def test_cycle_counter_starts_small(dut):
    """After reset, cycle counter should read a small value."""
    await setup(dut)
    val = await read_csr(dut, 0xC00)
    assert val < 64, f"Expected near-zero after reset, got {val}"


@cocotb.test()
async def test_cycle_counter_increments(dut):
    """Cycle counter should increase between reads."""
    await setup(dut)

    val1 = await read_csr(dut, 0xC00)
    await ClockCycles(dut.clk, 24)
    val2 = await read_csr(dut, 0xC00)

    assert val2 > val1, f"Cycle counter not increasing: {val1} -> {val2}"


@cocotb.test()
async def test_unknown_csr_reads_zero(dut):
    """Reading an unimplemented CSR address should return 0."""
    await setup(dut)
    val = await read_csr(dut, 0x123)
    assert val == 0, f"Unknown CSR should read 0, got {hex(val)}"
