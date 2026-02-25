"""Simple atomic tests for TinyMOA RV32EC decoder

Tests each instruction type individually without external dependencies.
Only ADD and AND are fully implemented; others are placeholders.

RISC-V ISA reference:
https://ww1.microchip.com/downloads/aemDocuments/documents/FPGA/ProductDocuments/UserGuides/ip_cores/directcores/riscvspec.pdf
"""

from . import rv32i_encode as rv32i
from . import rv32c_encode as rv32c

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from numpy import random


async def setup_decoder(dut):
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.instr.value = 0
    dut.imm.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


# ============================================================================
# INTEGRATION TESTS - Multiple instruction sequences
# ============================================================================


@cocotb.test()
async def test_integration_alu_sequence_placeholder(dut):
    """Test sequence of ALU operations - PLACEHOLDER"""
    # TODO: Test decoding sequence: ADD, AND, OR, XOR
    pass


@cocotb.test()
async def test_integration_load_store_placeholder(dut):
    """Test sequence of load/store operations - PLACEHOLDER"""
    # TODO: Test decoding sequence: LW, SW, LH, SH
    pass


@cocotb.test()
async def test_integration_branch_jump_placeholder(dut):
    """Test sequence of control flow operations - PLACEHOLDER"""
    # TODO: Test decoding sequence: BEQ, JAL, JALR
    pass


@cocotb.test()
async def test_integration_mixed_32bit_16bit_placeholder(dut):
    """Test sequence mixing 32-bit and 16-bit instructions - PLACEHOLDER"""
    # TODO: Test decoding sequence: ADD (32-bit), C.ADD (16-bit), ADDI (32-bit), C.ADDI (16-bit)
    pass
