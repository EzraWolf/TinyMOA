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


async def setup_tb_registers(dut):
    """Initialize the register file"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset the DUT
    dut.nrst.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


@cocotb.test()
async def test_foo(dut):
    """Test template"""
    await setup_tb_registers(dut)
    await ClockCycles(dut.clk, 1)

    raise NotImplementedError("Test not implemented yet")
