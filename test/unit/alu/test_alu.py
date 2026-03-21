"""
Test suite for the ALU (tinymoa_alu, tinymoa_shifter, tinymoa_multiplier)

tinymoa_alu:
- add_basic
- add_carry_propagation
- add_overflow_wrap
- sub_basic
- sub_borrow_propagation
- sub_negative_result
- and_basic
- or_basic
- xor_basic
- bitwise_all_zeros
- bitwise_all_ones
- slt_positive_less_than
- slt_negative_less_than
- slt_equal
- sltu_unsigned_compare
- czero_eqz
- czero_nez
- carry_chain_across_nibbles
- cmp_out_accumulation_across_nibbles

tinymoa_shifter:
- sll_by_zero
- sll_by_one
- sll_by_sixteen
- sll_by_thirtyone
- srl_by_one
- srl_by_sixteen
- srl_by_thirtyone
- sra_positive_by_one
- sra_negative_by_one
- sra_negative_by_thirtyone
- nibble_extraction_all_positions

tinymoa_multiplier:
- positive_times_positive
- negative_times_positive
- negative_times_negative
- zero_times_n
- max_times_max
- min_times_min
- product_nibble_extraction
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup(dut):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    dut.nrst.value = 0
    dut.opcode.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    dut.c_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


async def run_alu_op(dut, a, b, iterations=150):
    """Run ALU operation over many random inputs."""
    dut.a_in.value = int(a)
    dut.b_in.value = int(b)
    await ClockCycles(dut.clk, 1)
    results = []
    for _ in range(iterations):
        await ClockCycles(dut.clk, 7)
        next_a = random.randint(0, 0xFFFFFFFF)
        next_b = random.randint(0, 0xFFFFFFFF)
        dut.a_in.value = int(next_a)
        dut.b_in.value = int(next_b)
        await ClockCycles(dut.clk, 1)
        results.append((int(dut.result.value), a, b))
        a, b = next_a, next_b
    return results


@cocotb.test()
async def test_add_basic(dut):
    """Test ADD operation"""
    await setup(dut)
    dut.opcode.value = 0b0000
    dut.c_in.value = 0
    a = random.randint(0, 0xFFFFFFFF)
    b = random.randint(0, 0xFFFFFFFF)
    for result, a_val, b_val in await run_alu_op(dut, a, b):
        expected = (a_val + b_val) & 0xFFFFFFFF
        assert result == expected, (
            f"{a_val} + {b_val}: expected {expected}, got {result}"
        )


@cocotb.test()
async def test_sub_basic(dut):
    """Test SUB operation"""
    await setup(dut)
    dut.opcode.value = 0b1000
    dut.c_in.value = 1
    a = random.randint(0, 0xFFFFFFFF)
    b = random.randint(0, 0xFFFFFFFF)
    for result, a_val, b_val in await run_alu_op(dut, a, b):
        expected = (a_val - b_val) & 0xFFFFFFFF
        assert result == expected, (
            f"{a_val} - {b_val}: expected {expected}, got {result}"
        )
