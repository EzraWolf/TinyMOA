"""RV32I Instruction Decoder Verification Tests for TinyMOA

Comprehensive test suite for decoder.v implementing RV32I base ISA.
Tests all instruction formats: R, I, S, B, U, J, and system instructions.

Reference: RISC-V Unprivileged ISA v20191213
https://github.com/riscv/riscv-isa-manual/releases/download/Ratified-IMAFDQC/riscv-spec-20191213.pdf
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from numpy import random

import rv32i_encode as rv32i

# === Test Setup ===


async def setup_decoder(dut):
    """Initialize decoder with clock and reset"""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.instr.value = 0
    dut.imm.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


# === Verification Helper Functions ===


def _verify_control_flags(
    dut,
    *,
    is_alu_reg=0,
    is_alu_imm=0,
    is_load=0,
    is_store=0,
    is_branch=0,
    is_jal=0,
    is_jalr=0,
    is_lui=0,
    is_auipc=0,
    is_system=0,
):
    """Verify instruction control decode flags"""
    assert dut.instr_len.value == 4, "Expected 32-bit instruction"
    assert dut.is_alu_reg.value == is_alu_reg
    assert dut.is_alu_imm.value == is_alu_imm
    assert dut.is_load.value == is_load
    assert dut.is_store.value == is_store
    assert dut.is_branch.value == is_branch
    assert dut.is_jal.value == is_jal
    assert dut.is_jalr.value == is_jalr
    assert dut.is_lui.value == is_lui
    assert dut.is_auipc.value == is_auipc
    assert dut.is_system.value == is_system


def verify_r_type(dut, alu_opcode, rd, rs1, rs2):
    """Verify R-type instruction decode (OP opcode 0x33)"""
    assert dut.alu_opcode.value == alu_opcode, (
        f"ALU opcode mismatch: expected {alu_opcode:#06b}, got {dut.alu_opcode.value:#06b}"
    )
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert dut.rs2.value == rs2, f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
    _verify_control_flags(dut, is_alu_reg=1)


def verify_i_type_alu(dut, alu_opcode, rd, rs1, imm):
    """Verify I-type ALU immediate instruction decode (OP-IMM opcode 0x13)"""
    assert dut.alu_opcode.value == alu_opcode, (
        f"ALU opcode mismatch: expected {alu_opcode:#06b}, got {dut.alu_opcode.value:#06b}"
    )
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert dut.imm.value.to_signed() == imm, (
        f"Immediate mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
    )
    _verify_control_flags(dut, is_alu_imm=1)


def verify_i_type_shift(dut, alu_opcode, rd, rs1, shamt):
    """Verify I-type shift immediate instruction decode (OP-IMM opcode 0x13)"""
    assert dut.alu_opcode.value == alu_opcode, (
        f"ALU opcode mismatch: expected {alu_opcode:#06b}, got {dut.alu_opcode.value:#06b}"
    )
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert (dut.imm.value.integer & 0x1F) == shamt, (
        f"Shift amount mismatch: expected {shamt}, got {dut.imm.value.integer & 0x1F}"
    )
    _verify_control_flags(dut, is_alu_imm=1)


def verify_i_type_load(dut, mem_opcode, rd, rs1, imm):
    """Verify I-type load instruction decode (LOAD opcode 0x03)"""
    assert dut.mem_opcode.value == mem_opcode, (
        f"Memory opcode mismatch: expected {mem_opcode:#05b}, got {dut.mem_opcode.value:#05b}"
    )
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert dut.imm.value.to_signed() == imm, (
        f"Immediate mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
    )
    _verify_control_flags(dut, is_load=1)


def verify_s_type(dut, mem_opcode, rs1, rs2, imm):
    """Verify S-type store instruction decode (STORE opcode 0x23)"""
    assert dut.mem_opcode.value == mem_opcode, (
        f"Memory opcode mismatch: expected {mem_opcode:#05b}, got {dut.mem_opcode.value:#05b}"
    )
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert dut.rs2.value == rs2, f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
    assert dut.imm.value.to_signed() == imm, (
        f"Immediate mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
    )
    _verify_control_flags(dut, is_store=1)


def verify_u_type(dut, rd, imm, is_lui=False, is_auipc=False):
    """Verify U-type instruction decode (LUI 0x37 or AUIPC 0x17)"""
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.imm.value.integer == imm, (
        f"Immediate mismatch: expected {imm:#x}, got {int(dut.imm.value):#x}"
    )
    _verify_control_flags(
        dut, is_lui=(1 if is_lui else 0), is_auipc=(1 if is_auipc else 0)
    )


def verify_b_type(dut, alu_opcode, rs1, rs2, imm):
    """Verify B-type branch instruction decode (BRANCH opcode 0x63)"""
    assert dut.alu_opcode.value == alu_opcode, (
        f"ALU opcode mismatch: expected {alu_opcode:#06b}, got {dut.alu_opcode.value:#06b}"
    )
    assert dut.rs1.value == rs1, f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
    assert dut.rs2.value == rs2, f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
    assert dut.imm.value.to_signed() == imm, (
        f"Immediate mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
    )
    _verify_control_flags(dut, is_branch=1)


def verify_j_type(dut, rd, imm, is_jal=False, is_jalr=False):
    """Verify J-type jump instruction decode (JAL 0x6F or JALR 0x67)"""
    assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
    assert dut.imm.value.to_signed() == imm, (
        f"Immediate mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
    )
    assert dut.alu_opcode.value == 0b0000, "Jump uses ADD for address calculation"
    _verify_control_flags(
        dut, is_jal=(1 if is_jal else 0), is_jalr=(1 if is_jalr else 0)
    )


def verify_system_type(dut):
    """Verify system instruction decode (SYSTEM opcode 0x73)"""
    _verify_control_flags(dut, is_system=1)


# === RV32I Decoder Tests ===
# Tests are organized by instruction format and opcode family.


# === Register-Register ALU Operations (R-Type) ===


@cocotb.test()
async def test_add(dut):
    """ADD rd, rs1, rs2 - Integer addition (funct7=0x00, funct3=0)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_add(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0000, rd, rs1, rs2)


@cocotb.test()
async def test_and(dut):
    """AND rd, rs1, rs2 - Bitwise AND (funct7=0x00, funct3=7)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_and(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0111, rd, rs1, rs2)


@cocotb.test()
async def test_sub(dut):
    """SUB rd, rs1, rs2 - Integer subtraction (funct7=0x20, funct3=0)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_sub(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b1000, rd, rs1, rs2)


@cocotb.test()
async def test_or(dut):
    """OR rd, rs1, rs2 - Bitwise OR (funct7=0x00, funct3=6)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_or(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0110, rd, rs1, rs2)


@cocotb.test()
async def test_xor(dut):
    """XOR rd, rs1, rs2 - Bitwise XOR (funct7=0x00, funct3=4)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_xor(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0100, rd, rs1, rs2)


@cocotb.test()
async def test_slt(dut):
    """SLT rd, rs1, rs2 - Set less than signed (funct7=0x00, funct3=2)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_slt(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0010, rd, rs1, rs2)


@cocotb.test()
async def test_sltu(dut):
    """SLTU rd, rs1, rs2 - Set less than unsigned (funct7=0x00, funct3=3)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_sltu(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0011, rd, rs1, rs2)


@cocotb.test()
async def test_addi(dut):
    """ADDI rd, rs1, imm - Add immediate (funct3=0)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_addi(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0000, rd, rs1, imm)


@cocotb.test()
async def test_andi(dut):
    """ANDI rd, rs1, imm - AND immediate (funct3=7)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_andi(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0111, rd, rs1, imm)


@cocotb.test()
async def test_ori(dut):
    """ORI rd, rs1, imm - OR immediate (funct3=6)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_ori(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0110, rd, rs1, imm)


@cocotb.test()
async def test_xori(dut):
    """XORI rd, rs1, imm - XOR immediate (funct3=4)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_xori(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0100, rd, rs1, imm)


@cocotb.test()
async def test_sll(dut):
    """SLL rd, rs1, rs2 - Shift left logical (funct7=0x00, funct3=1)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_sll(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0001, rd, rs1, rs2)


@cocotb.test()
async def test_srl(dut):
    """SRL rd, rs1, rs2 - Shift right logical (funct7=0x00, funct3=5)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_srl(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b0101, rd, rs1, rs2)


@cocotb.test()
async def test_sra(dut):
    """SRA rd, rs1, rs2 - Shift right arithmetic (funct7=0x20, funct3=5)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32i.encode_sra(rd, rs1, rs2)
        await ClockCycles(dut.clk, 1)
        verify_r_type(dut, 0b1101, rd, rs1, rs2)


@cocotb.test()
async def test_slli(dut):
    """SLLI rd, rs1, shamt - Shift left logical immediate (funct3=1)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        shamt = random.randint(0, 31)
        dut.instr.value = rv32i.encode_slli(rd, rs1, shamt)
        await ClockCycles(dut.clk, 1)
        verify_i_type_shift(dut, 0b0001, rd, rs1, shamt)


@cocotb.test()
async def test_srli(dut):
    """SRLI rd, rs1, shamt - Shift right logical immediate (funct3=5)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        shamt = random.randint(0, 31)
        dut.instr.value = rv32i.encode_srli(rd, rs1, shamt)
        await ClockCycles(dut.clk, 1)
        verify_i_type_shift(dut, 0b0101, rd, rs1, shamt)


@cocotb.test()
async def test_srai(dut):
    """SRAI rd, rs1, shamt - Shift right arithmetic immediate (funct3=5)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        shamt = random.randint(0, 31)
        dut.instr.value = rv32i.encode_srai(rd, rs1, shamt)
        await ClockCycles(dut.clk, 1)
        verify_i_type_shift(dut, 0b1101, rd, rs1, shamt)


@cocotb.test()
async def test_lui(dut):
    """LUI rd, imm - Load upper immediate (opcode 0x37)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        imm_20bit = random.randint(0, 0xFFFFF)
        imm_expected = imm_20bit << 12
        dut.instr.value = rv32i.encode_lui(rd, imm_20bit)
        await ClockCycles(dut.clk, 1)
        verify_u_type(dut, rd, imm_expected, is_lui=True)


@cocotb.test()
async def test_auipc(dut):
    """AUIPC rd, imm - Add upper immediate to PC (opcode 0x17)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        imm_20bit = random.randint(0, 0xFFFFF)
        imm_expected = imm_20bit << 12
        dut.instr.value = rv32i.encode_auipc(rd, imm_20bit)
        await ClockCycles(dut.clk, 1)
        verify_u_type(dut, rd, imm_expected, is_auipc=True)


# === Load Operations (I-Type) ===


@cocotb.test()
async def test_lw(dut):
    """LW rd, offset(rs1) - Load word (funct3=2)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_lw(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_load(dut, 0b010, rd, rs1, imm)


@cocotb.test()
async def test_lh(dut):
    """LH rd, offset(rs1) - Load halfword signed (funct3=1)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_lh(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_load(dut, 0b001, rd, rs1, imm)


@cocotb.test()
async def test_lb(dut):
    """LB rd, offset(rs1) - Load byte signed (funct3=0)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_lb(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_load(dut, 0b000, rd, rs1, imm)


@cocotb.test()
async def test_lbu(dut):
    """LBU rd, offset(rs1) - Load byte unsigned (funct3=4)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_lbu(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_load(dut, 0b100, rd, rs1, imm)


@cocotb.test()
async def test_lhu(dut):
    """LHU rd, offset(rs1) - Load halfword unsigned (funct3=5)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_lhu(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_load(dut, 0b101, rd, rs1, imm)


# === Store Operations (S-Type) ===


@cocotb.test()
async def test_sw(dut):
    """SW rs2, offset(rs1) - Store word (funct3=2)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_sw(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_s_type(dut, 0b010, rs1, rs2, imm)


@cocotb.test()
async def test_sh(dut):
    """SH rs2, offset(rs1) - Store halfword (funct3=1)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_sh(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_s_type(dut, 0b001, rs1, rs2, imm)


@cocotb.test()
async def test_sb(dut):
    """SB rs2, offset(rs1) - Store byte (funct3=0)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_sb(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_s_type(dut, 0b000, rs1, rs2, imm)


# === Comparison Operations (I-Type) ===


@cocotb.test()
async def test_slti(dut):
    """SLTI rd, rs1, imm - Set less than immediate signed (funct3=2)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_slti(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0010, rd, rs1, imm)


@cocotb.test()
async def test_sltiu(dut):
    """SLTIU rd, rs1, imm - Set less than immediate unsigned (funct3=3)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_sltiu(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        verify_i_type_alu(dut, 0b0011, rd, rs1, imm)


# === Branch Operations (B-Type) ===


@cocotb.test()
async def test_beq(dut):
    """BEQ rs1, rs2, offset - Branch if equal (funct3=000)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_beq(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0100, rs1, rs2, imm)


@cocotb.test()
async def test_bne(dut):
    """BNE rs1, rs2, offset - Branch if not equal (funct3=001)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_bne(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0100, rs1, rs2, imm)


@cocotb.test()
async def test_blt(dut):
    """BLT rs1, rs2, offset - Branch if less than signed (funct3=100)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_blt(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0010, rs1, rs2, imm)


@cocotb.test()
async def test_bge(dut):
    """BGE rs1, rs2, offset - Branch if greater/equal signed (funct3=101)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_bge(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0010, rs1, rs2, imm)


@cocotb.test()
async def test_bltu(dut):
    """BLTU rs1, rs2, offset - Branch if less than unsigned (funct3=110)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_bltu(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0011, rs1, rs2, imm)


@cocotb.test()
async def test_bgeu(dut):
    """BGEU rs1, rs2, offset - Branch if greater/equal unsigned (funct3=111)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        imm = random.randint(-0x1000, 0xFFE) & ~1
        dut.instr.value = rv32i.encode_bgeu(rs1, rs2, imm)
        await ClockCycles(dut.clk, 1)
        verify_b_type(dut, 0b0011, rs1, rs2, imm)


# === Jump Operations (J-Type) ===


@cocotb.test()
async def test_jal(dut):
    """JAL rd, offset - Jump and link (opcode 0x6F)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        imm = random.randint(-0x100000, 0xFFFFE) & ~1
        dut.instr.value = rv32i.encode_jal(rd, imm)
        await ClockCycles(dut.clk, 1)
        verify_j_type(dut, rd, imm, is_jal=True)


@cocotb.test()
async def test_jalr(dut):
    """JALR rd, offset(rs1) - Jump and link register (opcode 0x67)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs1 = random.randint(0, 15)
        imm = random.randint(-0x800, 0x7FF)
        dut.instr.value = rv32i.encode_jalr(rd, rs1, imm)
        await ClockCycles(dut.clk, 1)
        assert dut.rs1.value == rs1, (
            f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
        )
        verify_j_type(dut, rd, imm, is_jalr=True)


# === System Instructions ===


@cocotb.test()
async def test_ecall(dut):
    """ECALL - Environment call (funct3=0, imm=0x000)"""
    await setup_decoder(dut)
    dut.instr.value = rv32i.encode_ecall()
    await ClockCycles(dut.clk, 1)
    verify_system_type(dut)


@cocotb.test()
async def test_ebreak(dut):
    """EBREAK - Environment breakpoint (funct3=0, imm=0x001)"""
    await setup_decoder(dut)
    dut.instr.value = rv32i.encode_ebreak()
    await ClockCycles(dut.clk, 1)
    verify_system_type(dut)


@cocotb.test()
async def test_fence(dut):
    """FENCE pred, succ - Memory ordering (opcode 0x0F, funct3=0)"""
    await setup_decoder(dut)
    dut.instr.value = rv32i.encode_fence(0xF, 0xF)
    await ClockCycles(dut.clk, 1)
    assert dut.instr_len.value == 4, "Expected 32-bit instruction"
