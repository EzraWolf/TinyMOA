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

# ============================================================================
# R-Type ALU Register Operations
# ============================================================================


async def setup_decoder(dut):
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.instr.value = 0
    dut.imm.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


@cocotb.test()
async def test_add(dut):
    """Test ADD instruction decode"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)

        dut.instr.value = rv32i.encode_add(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)

        # Operation and port values
        assert dut.alu_opcode.value == 0b0000, "ADD opcode should be 0b0000"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"

        assert dut.rs1.value == rs1, (
            f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        assert dut.instr_len.value == 4, "32-bit instruction"

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
async def test_and(dut):
    """Test AND instruction decode"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)

        dut.instr.value = rv32i.encode_and(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)

        # Operation and port values
        assert dut.alu_opcode.value == 0b0111, "AND opcode should be 0b0111"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == rs1, (
            f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        assert dut.instr_len.value == 4, "32-bit instruction"

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
async def test_sub_placeholder(dut):
    """Test SUB instruction decode - PLACEHOLDER"""
    # TODO: Implement SUB test
    pass


@cocotb.test()
async def test_or_placeholder(dut):
    """Test OR instruction decode - PLACEHOLDER"""
    # TODO: Implement OR test
    pass


@cocotb.test()
async def test_xor_placeholder(dut):
    """Test XOR instruction decode - PLACEHOLDER"""
    # TODO: Implement XOR test
    pass


@cocotb.test()
async def test_sll_placeholder(dut):
    """Test SLL instruction decode - PLACEHOLDER"""
    # TODO: Implement SLL test
    pass


@cocotb.test()
async def test_srl_placeholder(dut):
    """Test SRL instruction decode - PLACEHOLDER"""
    # TODO: Implement SRL test
    pass


@cocotb.test()
async def test_sra_placeholder(dut):
    """Test SRA instruction decode - PLACEHOLDER"""
    # TODO: Implement SRA test
    pass


@cocotb.test()
async def test_slt_placeholder(dut):
    """Test SLT instruction decode - PLACEHOLDER"""
    # TODO: Implement SLT test
    pass


@cocotb.test()
async def test_sltu_placeholder(dut):
    """Test SLTU instruction decode - PLACEHOLDER"""
    # TODO: Implement SLTU test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - I-Type ALU Immediate Operations
# ============================================================================


@cocotb.test()
async def test_addi_placeholder(dut):
    """Test ADDI instruction decode - PLACEHOLDER"""
    # TODO: Implement ADDI test
    pass


@cocotb.test()
async def test_andi_placeholder(dut):
    """Test ANDI instruction decode - PLACEHOLDER"""
    # TODO: Implement ANDI test
    pass


@cocotb.test()
async def test_ori_placeholder(dut):
    """Test ORI instruction decode - PLACEHOLDER"""
    # TODO: Implement ORI test
    pass


@cocotb.test()
async def test_xori_placeholder(dut):
    """Test XORI instruction decode - PLACEHOLDER"""
    # TODO: Implement XORI test
    pass


@cocotb.test()
async def test_slti_placeholder(dut):
    """Test SLTI instruction decode - PLACEHOLDER"""
    # TODO: Implement SLTI test
    pass


@cocotb.test()
async def test_sltiu_placeholder(dut):
    """Test SLTIU instruction decode - PLACEHOLDER"""
    # TODO: Implement SLTIU test
    pass


@cocotb.test()
async def test_slli_placeholder(dut):
    """Test SLLI instruction decode - PLACEHOLDER"""
    # TODO: Implement SLLI test
    pass


@cocotb.test()
async def test_srli_placeholder(dut):
    """Test SRLI instruction decode - PLACEHOLDER"""
    # TODO: Implement SRLI test
    pass


@cocotb.test()
async def test_srai_placeholder(dut):
    """Test SRAI instruction decode - PLACEHOLDER"""
    # TODO: Implement SRAI test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - Load Operations
# ============================================================================


@cocotb.test()
async def test_lw_placeholder(dut):
    """Test LW instruction decode - PLACEHOLDER"""
    # TODO: Implement LW test
    pass


@cocotb.test()
async def test_lh_placeholder(dut):
    """Test LH instruction decode - PLACEHOLDER"""
    # TODO: Implement LH test
    pass


@cocotb.test()
async def test_lb_placeholder(dut):
    """Test LB instruction decode - PLACEHOLDER"""
    # TODO: Implement LB test
    pass


@cocotb.test()
async def test_lbu_placeholder(dut):
    """Test LBU instruction decode - PLACEHOLDER"""
    # TODO: Implement LBU test
    pass


@cocotb.test()
async def test_lhu_placeholder(dut):
    """Test LHU instruction decode - PLACEHOLDER"""
    # TODO: Implement LHU test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - Store Operations
# ============================================================================


@cocotb.test()
async def test_sw_placeholder(dut):
    """Test SW instruction decode - PLACEHOLDER"""
    # TODO: Implement SW test
    pass


@cocotb.test()
async def test_sh_placeholder(dut):
    """Test SH instruction decode - PLACEHOLDER"""
    # TODO: Implement SH test
    pass


@cocotb.test()
async def test_sb_placeholder(dut):
    """Test SB instruction decode - PLACEHOLDER"""
    # TODO: Implement SB test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - Branch Operations
# ============================================================================


@cocotb.test()
async def test_beq_placeholder(dut):
    """Test BEQ instruction decode - PLACEHOLDER"""
    # TODO: Implement BEQ test
    pass


@cocotb.test()
async def test_bne_placeholder(dut):
    """Test BNE instruction decode - PLACEHOLDER"""
    # TODO: Implement BNE test
    pass


@cocotb.test()
async def test_blt_placeholder(dut):
    """Test BLT instruction decode - PLACEHOLDER"""
    # TODO: Implement BLT test
    pass


@cocotb.test()
async def test_bge_placeholder(dut):
    """Test BGE instruction decode - PLACEHOLDER"""
    # TODO: Implement BGE test
    pass


@cocotb.test()
async def test_bltu_placeholder(dut):
    """Test BLTU instruction decode - PLACEHOLDER"""
    # TODO: Implement BLTU test
    pass


@cocotb.test()
async def test_bgeu_placeholder(dut):
    """Test BGEU instruction decode - PLACEHOLDER"""
    # TODO: Implement BGEU test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - Jump Operations
# ============================================================================


@cocotb.test()
async def test_jal_placeholder(dut):
    """Test JAL instruction decode - PLACEHOLDER"""
    # TODO: Implement JAL test
    pass


@cocotb.test()
async def test_jalr_placeholder(dut):
    """Test JALR instruction decode - PLACEHOLDER"""
    # TODO: Implement JALR test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - Upper Immediate Operations
# ============================================================================


@cocotb.test()
async def test_lui_placeholder(dut):
    """Test LUI instruction decode - PLACEHOLDER"""
    # TODO: Implement LUI test
    pass


@cocotb.test()
async def test_auipc_placeholder(dut):
    """Test AUIPC instruction decode - PLACEHOLDER"""
    # TODO: Implement AUIPC test
    pass


# ============================================================================
# INDIVIDUAL INSTRUCTION TESTS - System Operations
# ============================================================================


@cocotb.test()
async def test_ecall_placeholder(dut):
    """Test ECALL instruction decode - PLACEHOLDER"""
    # TODO: Implement ECALL test
    pass


@cocotb.test()
async def test_ebreak_placeholder(dut):
    """Test EBREAK instruction decode - PLACEHOLDER"""
    # TODO: Implement EBREAK test
    pass


# ============================================================================
# COMPRESSED INSTRUCTION TESTS - RV32C
# ============================================================================


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
'''
