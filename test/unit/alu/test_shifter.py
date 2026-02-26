"""Test suite for tinymoa_shifter."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from numpy import random


async def setup_shifter(dut, opcode):
    """Initialize shifter with clock and reset."""
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.opcode.value = opcode

    dut.nrst.value = 0
    dut.data_in.value = 0
    dut.shift_amnt.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1

    return dut


async def test_shift_operation(dut, operation, iterations=100):
    data = random.randint(0, 0xFFFFFFFF)
    shift_amount = random.randint(0, 31)
    dut.data_in.value = data
    dut.shift_amnt.value = shift_amount
    await ClockCycles(dut.clk, 1)

    for _ in range(iterations):
        await ClockCycles(dut.clk, 7)
        expected = int(operation(data, shift_amount) & 0xFFFFFFFF)

        # Load new values for the next operation
        data = random.randint(0, 0xFFFFFFFF)
        shift_amount = random.randint(0, 31)
        dut.data_in.value = data
        dut.shift_amnt.value = shift_amount
        await ClockCycles(dut.clk, 1)

        result = int(dut.result.value)
        assert result == expected, f"Expected 0x{expected:08X}, got 0x{result:08X}"


@cocotb.test()
async def test_sll(dut):
    """Test SLL: Shift Left Logical
    opcode[3] = 0 (not arithmetic)
    opcode[2] = 0 (not right shift)
    """

    await setup_shifter(dut, 0b00)
    await test_shift_operation(dut, lambda data, shift: data << shift)


@cocotb.test()
async def test_srl(dut):
    """Test SRL: Shift Right Logical
    opcode[3] = 0 (not arithmetic)
    opcode[2] = 1 (right shift)
    """

    await setup_shifter(dut, 0b01)
    await test_shift_operation(dut, lambda data, shift: data >> shift)


@cocotb.test()
async def test_sra(dut):
    """Test SRA: Shift Right Arithmetic
    opcode[3] = 1 (arithmetic)
    opcode[2] = 1 (right shift)
    """

    await setup_shifter(dut, 0b11)

    def sra_operation(data, shift):
        if data & 0x80000000:
            return (data >> shift) | (~0xFFFFFFFF >> shift)
        else:
            return data >> shift

    await test_shift_operation(dut, sra_operation)
