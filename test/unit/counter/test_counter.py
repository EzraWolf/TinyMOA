"""
Test suite for general purpose program/nibble counters

- reset_clears_count
- increment_when_enabled
- hold_when_disabled
- over_run_wraps_to_zero
- under_run_wraps_to_max_val
- done_asserted_at_max_val
- done_not_asserted_before_max_val
- load_overrides_count
- load_to_zero
- load_to_max_val
- nibble_mode_eight_cycle_wrap
- nibble_mode_four_cycle_wrap
- load_mid_count
- max_val_one
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_tb_counter(dut):
    """Initialize the counter"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset the DUT
    dut.nrst.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


@cocotb.test()
async def test_foo(dut):
    """Test template"""
    await setup_tb_counter(dut)
    await ClockCycles(dut.clk, 1)

    raise NotImplementedError("Test not implemented yet")
