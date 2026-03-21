"""
Test suite for TinyMOA RV32EC CPU core

Reset and fetch:
- reset_pc_zero
- reset_registers_zero
- fetch_from_correct_address
- fetch_stall_on_mem_not_ready

Execute (32-bit):
- add_end_to_end_8_cycles
- sub_end_to_end
- and_or_xor_end_to_end
- slt_sltu_end_to_end
- sll_srl_sra_end_to_end
- lui_loads_upper_immediate
- auipc_adds_pc
- lw_sw_round_trip
- lb_lh_sign_extension
- lbu_lhu_zero_extension
- branch_beq_taken
- branch_beq_not_taken
- branch_bne_taken
- branch_blt_bltu
- branch_bge_bgeu
- jal_pc_jump_and_link
- jalr_pc_from_rs1
- czero_eqz_czero_nez

Execute (compressed):
- caddi_four_cycle_execute
- cli_loads_immediate
- cmv_register_copy
- cadd_end_to_end
- cmul_end_to_end
- cjal_cj_jump
- cbeqz_cbnez_branch
- clw_csw_round_trip

Special registers:
- gp_reads_as_0x000400
- tp_reads_as_0x400000
- x0_writes_ignored

Pipeline:
- back_to_back_alu_instructions
- memory_stall_holds_pipeline
- nop_advances_pc

Programs:
- fibonacci_rv32i
- fibonacci_rv32c
- matmul_rv32i
- matmul_rv32c
- tcm_write_read
- qspi_flash_write_read
"""

import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_tb_cpu(dut):
    """Initialize the CPU"""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset the DUT
    dut.nrst.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


@cocotb.test()
async def test_foo(dut):
    """Test template"""
    await setup_tb_cpu(dut)
    await ClockCycles(dut.clk, 1)

    raise NotImplementedError("Test not implemented yet")
