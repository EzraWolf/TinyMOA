"""
Atomic RV32C instruction decode tests for TinyMOA

RISC-V ISA reference:
https://ww1.microchip.com/downloads/aemDocuments/documents/FPGA/ProductDocuments/UserGuides/ip_cores/directcores/riscvspec.pdf
"""

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
# Compressed Register Operations
# ============================================================================


@cocotb.test()
async def test_c_add(dut):
    """Test C.ADD compressed instruction decode

    C.ADD uses CR-type format with full 5-bit register encoding.
    For RV32E, registers are x0-x15.
    C.ADD rd, rs2 => rd = rd + rs2 (rd is both source and destination)
    """
    await setup_decoder(dut)

    for _ in range(20):
        # C.ADD uses full register encoding (x0-x15 for RV32E)
        rd = random.randint(1, 15)  # rd != 0 (x0 is hardwired to zero)
        rs2 = random.randint(0, 15)

        dut.instr.value = rv32c.encode_c_add(rd, rs2)
        await ClockCycles(dut.clk, 1)

        # Operation and port values
        assert dut.alu_opcode.value == 0b0000, "C.ADD opcode should be 0b0000 (ADD)"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == rd, (
            f"rs1 mismatch: expected x{rd} (C.ADD uses rd as source), got x{dut.rs1.value}"
        )
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        assert dut.instr_len.value == 2, "16-bit compressed instruction"

        # Decoder flags
        assert dut.is_alu_reg.value == 1, "Should be ALU register operation"
        assert dut.is_alu_imm.value == 0
        assert dut.is_load.value == 0
        assert dut.is_store.value == 0
        assert dut.is_branch.value == 0
        assert dut.is_jal.value == 0
        assert dut.is_jalr.value == 0
        assert dut.is_lui.value == 0
        assert dut.is_auipc.value == 0
        assert dut.is_system.value == 0


@cocotb.test()
async def test_c_and(dut):
    """Test C.AND compressed instruction decode

    C.AND uses CA-type format with compressed 3-bit register encoding.
    Registers rd' and rs2' map to x8-x15 (RV32E subset).
    C.AND rd', rs2' => rd' = rd' & rs2' (rd is both source and destination)
    """
    await setup_decoder(dut)

    for _ in range(20):
        # C.AND uses compressed register encoding (x8-x15)
        rd = random.randint(0, 7)  # Maps to x8-x15
        rs2 = random.randint(0, 7)  # Maps to x8-x15

        dut.instr.value = rv32c.encode_c_and(rd, rs2)
        await ClockCycles(dut.clk, 1)

        # C.AND uses 3-bit register encoding, so actual register is 8 + value
        expected_rd = 8 + rd
        expected_rs2 = 8 + rs2

        # Operation and port values
        assert dut.alu_opcode.value == 0b0111, "C.AND opcode should be 0b0111 (AND)"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd} (C.AND uses rd as source), got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        assert dut.instr_len.value == 2, "16-bit compressed instruction"

        # Decoder flags
        assert dut.is_alu_reg.value == 1, "Should be ALU register operation"
        assert dut.is_alu_imm.value == 0
        assert dut.is_load.value == 0
        assert dut.is_store.value == 0
        assert dut.is_branch.value == 0
        assert dut.is_jal.value == 0
        assert dut.is_jalr.value == 0
        assert dut.is_lui.value == 0
        assert dut.is_auipc.value == 0
        assert dut.is_system.value == 0


'''
@cocotb.test()
async def test_c_mv_placeholder(dut):
    """Test C.MV instruction decode - PLACEHOLDER"""
    # TODO: Implement C.MV test
    pass


@cocotb.test()
async def test_c_li_placeholder(dut):
    """Test C.LI instruction decode - PLACEHOLDER"""
    # TODO: Implement C.LI test
    pass


@cocotb.test()
async def test_c_addi_placeholder(dut):
    """Test C.ADDI instruction decode - PLACEHOLDER"""
    # TODO: Implement C.ADDI test
    pass


@cocotb.test()
async def test_c_lw_placeholder(dut):
    """Test C.LW instruction decode - PLACEHOLDER"""
    # TODO: Implement C.LW test
    pass


@cocotb.test()
async def test_c_sw_placeholder(dut):
    """Test C.SW instruction decode - PLACEHOLDER"""
    # TODO: Implement C.SW test
    pass


@cocotb.test()
async def test_c_j_placeholder(dut):
    """Test C.J instruction decode - PLACEHOLDER"""
    # TODO: Implement C.J test
    pass


@cocotb.test()
async def test_c_beqz_placeholder(dut):
    """Test C.BEQZ instruction decode - PLACEHOLDER"""
    # TODO: Implement C.BEQZ test
    pass


@cocotb.test()
async def test_c_bnez_placeholder(dut):
    """Test C.BNEZ instruction decode - PLACEHOLDER"""
    # TODO: Implement C.BNEZ test
    pass


'''
