"""
Test suite for the register file (tinymoa_registers)

- x0_reads_zero
- x0_write_ignored
- gp_reads_0x000400
- tp_reads_0x400000
- write_then_read_nibble_serial
- write_all_storage_registers
- simultaneous_rs1_rs2_different_regs
- simultaneous_rs1_rs2_same_reg
- no_cross_contamination_between_regs
- reset_clears_all_registers
- rd_wr_en_low_does_not_corrupt
- nibble_position_alignment_after_partial_cycle
- write_zero_to_register
- write_max_to_register
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup(dut):
    """Initialize the register file"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.rs1_sel.value = 0
    dut.rs2_sel.value = 0
    dut.rd_sel.value = 0
    dut.rd_data.value = 0
    dut.rd_wen.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


async def write_reg(dut, reg, value):
    """Write a 32-bit value to a register over 8 nibble cycles."""
    dut.rd_sel.value = reg
    dut.rd_data.value = int(value)
    dut.rd_wen.value = 1
    await ClockCycles(dut.clk, 8)
    dut.rd_wen.value = 0


async def read_regs(dut, rs1, rs2):
    """Read two registers over 8 nibble cycles. Returns (rs1_val, rs2_val)."""
    dut.rs1_sel.value = rs1
    dut.rs2_sel.value = rs2
    dut.rd_wen.value = 0
    await ClockCycles(dut.clk, 8)
    dut.rd_sel.value = 0
    dut.rd_data.value = 0
    dut.rd_wen.value = 1
    await ClockCycles(dut.clk, 1) # Resolve to read
    return int(dut.rs1_data.value), int(dut.rs2_data.value)


@cocotb.test()
async def test_x0_reads_zero(dut):
    """x0 always reads zero"""
    await setup(dut)
    rs1, _ = await read_regs(dut, 0, 0)
    assert rs1 == 0, f"x0: expected 0, got {hex(rs1)}"


@cocotb.test()
async def test_x0_write_ignored(dut):
    """Writing to x0 has no effect"""
    await setup(dut)
    await write_reg(dut, 0, 0xDEADBEEF)
    rs1, _ = await read_regs(dut, 0, 0)
    assert rs1 == 0, f"x0 after write: expected 0, got {hex(rs1)}"


@cocotb.test()
async def test_gp_reads_0x000400(dut):
    """x3 (gp) reads 0x000400"""
    await setup(dut)
    rs1, _ = await read_regs(dut, 3, 3)
    assert rs1 == 0x000400, f"gp: expected 0x000400, got {hex(rs1)}"


@cocotb.test()
async def test_tp_reads_0x400000(dut):
    """x4 (tp) reads 0x400000"""
    await setup(dut)
    rs1, _ = await read_regs(dut, 4, 4)
    assert rs1 == 0x400000, f"tp: expected 0x400000, got {hex(rs1)}"


@cocotb.test()
async def test_write_then_read_nibble_serial(dut):
    """Write random values to storage registers and read them back."""
    await setup(dut)
    # Skip x0 (hardwired), x3 (gp), x4 (tp)
    storage_regs = [r for r in range(16) if r not in (0, 3, 4)]
    values = {r: random.randint(0, 0xFFFFFFFF) for r in storage_regs}

    for reg in storage_regs:
        await write_reg(dut, reg, values[reg])

    for reg in storage_regs:
        rs1, rs2 = await read_regs(dut, reg, reg)
        assert rs1 == values[reg], (
            f"x{reg}: expected {hex(values[reg])}, got {hex(rs1)}"
        )
        assert rs1 == rs2, (
            f"x{reg} port mismatch: rs1={hex(rs1)}, rs2={hex(rs2)}"
        )