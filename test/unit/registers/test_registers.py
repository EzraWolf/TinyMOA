"""Test suite for RV32E register file."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from numpy import random


async def setup_registers(dut):
    """Initialize register file with clock and reset."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.write_en.value = 0
    dut.read_addr_a.value = 0
    dut.read_addr_b.value = 0
    dut.write_dest.value = 0
    dut.data_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1

    return dut


async def write_register(dut, reg, value):
    """Write a value to a register."""
    dut.write_dest.value = reg
    dut.data_in.value = int(value)
    dut.write_en.value = 1
    await ClockCycles(dut.clk, 8)


async def read_registers(dut, rs1, rs2):
    """Read from both register ports and return values."""
    dut.read_addr_a.value = rs1
    dut.read_addr_b.value = rs2
    dut.write_en.value = 0
    await ClockCycles(dut.clk, 8)

    dut.write_dest.value = 0  # Point to x0 (hardcoded) to avoid corrupting registers
    dut.write_en.value = 1
    dut.data_in.value = 0
    await ClockCycles(dut.clk, 1)

    return int(dut.data_port_a.value), int(dut.data_port_b.value)


@cocotb.test()
async def test_all_registers(dut):
    """Test write/read for all 16 registers including hardcoded ones."""
    await setup_registers(dut)

    hardcoded = {
        0: 0x00000000,  # x0 is $zero
        3: 0x01000400,  # x3 is $ga
        4: 0x08000000,  # x4 is $tp
    }

    test_values = {}

    # Write random values to ALL registers first
    for reg in range(16):
        value = random.randint(0, 0xFFFFFFFF)
        test_values[reg] = hardcoded.get(reg, value)
        await write_register(dut, reg, value)

    # Now read back ALL registers and verify they held the values
    for reg in range(16):
        rs1_value, rs2_value = await read_registers(dut, reg, reg)
        expected = test_values[reg]

        assert rs1_value == rs2_value, (
            f"x{reg} port mismatch: rs1={hex(rs1_value)}, rs2={hex(rs2_value)}"
        )

        assert rs1_value == expected, (
            f"x{reg}: got {hex(rs1_value)}, expected {hex(expected)}"
        )

        await ClockCycles(dut.clk, 7)


@cocotb.test()
async def test_dual_port_read(dut):
    """Test reading two different registers simultaneously."""
    await setup_registers(dut)

    # Write random values to two different registers
    reg_a, reg_b = 1, 2
    test_value_a = random.randint(0, 0xFFFFFFFF)
    test_value_b = random.randint(0, 0xFFFFFFFF)

    await write_register(dut, reg_a, test_value_a)
    await write_register(dut, reg_b, test_value_b)

    # Read both ports simultaneously
    rs1_value, rs2_value = await read_registers(dut, reg_a, reg_b)

    assert rs1_value == int(test_value_a), (
        f"rs1 (x{reg_a}): got {hex(rs1_value)}, expected {hex(int(test_value_a))}"
    )
    assert rs2_value == int(test_value_b), (
        f"rs2 (x{reg_b}): got {hex(rs2_value)}, expected {hex(int(test_value_b))}"
    )


@cocotb.test()
async def test_write_enable_gating(dut):
    """Verify writes only happen when write_en is high."""
    await setup_registers(dut)

    reg = random.randint(5, 14)  # Avoid hardcoded registers
    initial_value = random.randint(0, 0xFFFFFFFF)
    blocked_value = random.randint(0, 0xFFFFFFFF)

    # Write initial value with write_en high
    await write_register(dut, reg, initial_value)

    # Attempt write with write_en low (should be blocked)
    dut.write_dest.value = reg
    dut.data_in.value = int(blocked_value)
    dut.write_en.value = 0
    await ClockCycles(dut.clk, 8)

    # Read back and verify initial value unchanged
    read_value, _ = await read_registers(dut, reg, 0)

    assert read_value == int(initial_value), (
        f"Write enable failed: got {hex(read_value)}, expected {hex(int(initial_value))}"
    )
