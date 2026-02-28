"""RV32C Compressed Instruction Decoder Tests for TinyMOA

Test suite for compressed instruction decoding in decoder.v.
Tests RV32C instruction formats: CR, CI, CSS, CIW, CL, CS, CA, CB, CJ.

Reference: RISC-V Compressed ISA Specification v2.0
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles
from numpy import random

from . import rv32c_encode as rv32c

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
    assert dut.instr_len.value == 2, "Expected 16-bit compressed instruction"
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


# === RV32C Decoder Tests ===


# === Quadrant 0: Loads, Stores, Stack Operations ===


@cocotb.test()
async def test_c_addi4spn(dut):
    """C.ADDI4SPN rd', imm - Add scaled immediate to SP (CIW format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        imm = random.randint(1, 255) << 2
        dut.instr.value = rv32c.encode_c_addi4spn(rd, imm)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd

        assert dut.alu_opcode.value == 0b0000, "C.ADDI4SPN uses ADD opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == 2, "C.ADDI4SPN uses x2 (SP) as rs1"
        assert dut.imm.value.to_unsigned() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_lw(dut):
    """C.LW rd', offset(rs1') - Load word (CL format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs1 = random.randint(0, 7)
        offset = random.randint(0, 124) & ~3
        dut.instr.value = rv32c.encode_c_lw(rd, rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b010, "C.LW uses LW memory opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_load=1)


@cocotb.test()
async def test_c_lbu(dut):
    """C.LBU rd', offset(rs1') - Load byte unsigned"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs1 = random.randint(0, 7)
        offset = random.randint(0, 3)
        dut.instr.value = rv32c.encode_c_lbu(rd, rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b100, "C.LBU uses LBU memory opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_load=1)


@cocotb.test()
async def test_c_lhu(dut):
    """C.LHU rd', offset(rs1') - Load halfword unsigned"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs1 = random.randint(0, 7)
        offset = random.randint(0, 1) << 1
        dut.instr.value = rv32c.encode_c_lhu(rd, rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b101, "C.LHU uses LHU memory opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_load=1)


@cocotb.test()
async def test_c_lh(dut):
    """C.LH rd', offset(rs1') - Load halfword signed"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs1 = random.randint(0, 7)
        offset = random.randint(0, 1) << 1
        dut.instr.value = rv32c.encode_c_lh(rd, rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b001, "C.LH uses LH memory opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_load=1)


@cocotb.test()
async def test_c_sw(dut):
    """C.SW rs2', offset(rs1') - Store word (CS format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        offset = random.randint(0, 124) & ~3
        dut.instr.value = rv32c.encode_c_sw(rs1, rs2, offset)
        await ClockCycles(dut.clk, 1)

        expected_rs1 = 8 + rs1
        expected_rs2 = 8 + rs2

        assert dut.mem_opcode.value == 0b010, "C.SW uses SW memory opcode"
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_store=1)


@cocotb.test()
async def test_c_sb(dut):
    """C.SB rs2', offset(rs1') - Store byte"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        offset = random.randint(0, 3)
        dut.instr.value = rv32c.encode_c_sb(rs1, rs2, offset)
        await ClockCycles(dut.clk, 1)

        expected_rs1 = 8 + rs1
        expected_rs2 = 8 + rs2

        assert dut.mem_opcode.value == 0b000, "C.SB uses SB memory opcode"
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_store=1)


@cocotb.test()
async def test_c_sh(dut):
    """C.SH rs2', offset(rs1') - Store halfword"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        offset = random.randint(0, 1) << 1
        dut.instr.value = rv32c.encode_c_sh(rs1, rs2, offset)
        await ClockCycles(dut.clk, 1)

        expected_rs1 = 8 + rs1
        expected_rs2 = 8 + rs2

        assert dut.mem_opcode.value == 0b001, "C.SH uses SH memory opcode"
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_store=1)


# === Quadrant 1: ALU, Branches, Jumps ===


# === Quadrant 2: Stack Operations, Register Ops, Jumps ===


@cocotb.test()
async def test_c_slli(dut):
    """C.SLLI rd, shamt - Shift left logical immediate (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        shamt = random.randint(1, 31)
        dut.instr.value = rv32c.encode_c_slli(rd, shamt)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0001, "C.SLLI uses SLL opcode"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == rd, (
            f"rs1 mismatch: expected x{rd}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == shamt, (
            f"shamt mismatch: expected {shamt}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_lwsp(dut):
    """C.LWSP rd, offset(sp) - Load word from stack pointer (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        offset = random.randint(0, 252) & ~3
        dut.instr.value = rv32c.encode_c_lwsp(rd, offset)
        await ClockCycles(dut.clk, 1)

        assert dut.mem_opcode.value == 0b010, "C.LWSP uses LW memory opcode"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == 2, "C.LWSP uses x2 (SP) as base"
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_load=1)


@cocotb.test()
async def test_c_swsp(dut):
    """C.SWSP rs2, offset(sp) - Store word to stack pointer (CSS format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs2 = random.randint(0, 15)
        offset = random.randint(0, 252) & ~3
        dut.instr.value = rv32c.encode_c_swsp(rs2, offset)
        await ClockCycles(dut.clk, 1)

        assert dut.mem_opcode.value == 0b010, "C.SWSP uses SW memory opcode"
        assert dut.rs1.value == 2, "C.SWSP uses x2 (SP) as base"
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        assert dut.imm.value.to_unsigned() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_store=1)


@cocotb.test()
async def test_c_jr(dut):
    """C.JR rs1 - Jump register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(1, 15)
        dut.instr.value = rv32c.encode_c_jr(rs1)
        await ClockCycles(dut.clk, 1)

        assert dut.rs1.value == rs1, (
            f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
        )
        assert dut.rd.value == 1, "C.JR sets rd=x1 (ra)"
        assert dut.imm.value.to_unsigned() == 0, "C.JR has zero offset"
        _verify_control_flags(dut, is_jalr=1)


@cocotb.test()
async def test_c_jalr(dut):
    """C.JALR rs1 - Jump and link register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(1, 15)
        dut.instr.value = rv32c.encode_c_jalr(rs1)
        await ClockCycles(dut.clk, 1)

        assert dut.rs1.value == rs1, (
            f"rs1 mismatch: expected x{rs1}, got x{dut.rs1.value}"
        )
        assert dut.rd.value == 1, "C.JALR sets rd=x1 (ra)"
        assert dut.imm.value.to_unsigned() == 0, "C.JALR has zero offset"
        _verify_control_flags(dut, is_jalr=1)


@cocotb.test()
async def test_c_ebreak(dut):
    """C.EBREAK - Breakpoint (CR format)"""
    await setup_decoder(dut)

    dut.instr.value = rv32c.encode_c_ebreak()
    await ClockCycles(dut.clk, 1)

    assert dut.imm.value.to_unsigned() == 1, "C.EBREAK sets imm=1"
    _verify_control_flags(dut, is_system=1)


# === Compressed ALU Operations ===


@cocotb.test()
async def test_c_add(dut):
    """C.ADD rd, rs2 - Add register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        rs2 = random.randint(1, 15)  # rs2=0 is illegal for C.ADD (would be C.JALR)
        dut.instr.value = rv32c.encode_c_add(rd, rs2)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.ADD uses ADD opcode"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == rd, (
            f"rs1 mismatch: expected x{rd}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_and(dut):
    """C.AND rd', rs2' - Bitwise AND (CA format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        dut.instr.value = rv32c.encode_c_and(rd, rs2)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs2 = 8 + rs2

        assert dut.alu_opcode.value == 0b0111, "C.AND uses AND opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_mv(dut):
    """C.MV rd, rs2 - Copy register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        # rs2=0 is illegal for C.MV
        rd = random.randint(1, 15)
        rs2 = random.randint(1, 15)
        dut.instr.value = rv32c.encode_c_mv(rd, rs2)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.MV uses ADD opcode (rd = x0 + rs2)"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == 0, "C.MV uses x0 as rs1"
        assert dut.rs2.value == rs2, (
            f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_li(dut):
    """C.LI rd, imm - Load immediate (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        imm = random.randint(-32, 31)
        dut.instr.value = rv32c.encode_c_li(rd, imm)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.LI uses ADDI opcode (rd = x0 + imm)"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == 0, "C.LI uses x0 as rs1"
        assert dut.imm.value.to_signed() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_addi(dut):
    """C.ADDI rd, imm - Add immediate (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        imm = random.randint(-32, 31)
        dut.instr.value = rv32c.encode_c_addi(rd, imm)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.ADDI uses ADDI opcode"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == rd, (
            f"rs1 mismatch: expected x{rd}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_signed() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_nop(dut):
    """C.NOP - No operation (CI format)"""
    await setup_decoder(dut)

    dut.instr.value = rv32c.encode_c_nop()
    await ClockCycles(dut.clk, 1)

    assert dut.alu_opcode.value == 0b0000, "C.NOP uses ADDI opcode"
    assert dut.rd.value == 0, "C.NOP writes to x0"
    assert dut.rs1.value == 0, "C.NOP uses x0 as rs1"
    assert dut.imm.value.to_unsigned() == 0, "C.NOP has zero immediate"
    _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_jal(dut):
    """C.JAL offset - Jump and link (CJ format, RV32 only)"""
    await setup_decoder(dut)

    for _ in range(20):
        # Remember...
        # CJ-type: 11-bit signed scaled by 2 = 12-bit signed immediate.
        offset = random.randint(-1024, 1023) << 1
        dut.instr.value = rv32c.encode_c_jal(offset)
        await ClockCycles(dut.clk, 1)

        assert dut.rd.value == 1, "C.JAL sets rd=x1 (ra)"
        assert dut.imm.value.to_signed() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_jal=1)


@cocotb.test()
async def test_c_addi16sp(dut):
    """C.ADDI16SP imm - Add immediate to SP scaled by 16 (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        imm = random.randint(-512, 496) & ~15
        if imm == 0:
            imm = 16
        dut.instr.value = rv32c.encode_c_addi16sp(imm)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.ADDI16SP uses ADDI opcode"
        assert dut.rd.value == 2, "C.ADDI16SP sets rd=x2 (sp)"
        assert dut.rs1.value == 2, "C.ADDI16SP uses x2 (sp) as rs1"
        assert dut.imm.value.to_signed() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_lui(dut):
    """C.LUI rd, imm - Load upper immediate (CI format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(3, 15)  # Skip x0, x1, x2
        imm = random.randint(-32, 31) << 12
        if imm == 0:
            imm = 0x1000
        dut.instr.value = rv32c.encode_c_lui(rd, imm)
        await ClockCycles(dut.clk, 1)

        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.imm.value.to_signed() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_lui=1)


@cocotb.test()
async def test_c_srli(dut):
    """C.SRLI rd', shamt - Shift right logical immediate (CB format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        shamt = random.randint(1, 31)
        dut.instr.value = rv32c.encode_c_srli(rd, shamt)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd

        assert dut.alu_opcode.value == 0b0101, "C.SRLI uses SRL opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == shamt, (
            f"shamt mismatch: expected {shamt}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_srai(dut):
    """C.SRAI rd', shamt - Shift right arithmetic immediate (CB format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        shamt = random.randint(1, 31)
        dut.instr.value = rv32c.encode_c_srai(rd, shamt)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd

        assert dut.alu_opcode.value == 0b1101, "C.SRAI uses SRA opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_unsigned() == shamt, (
            f"shamt mismatch: expected {shamt}, got {dut.imm.value.to_unsigned()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_andi(dut):
    """C.ANDI rd', imm - AND immediate (CB format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        imm = random.randint(-32, 31)
        dut.instr.value = rv32c.encode_c_andi(rd, imm)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd

        assert dut.alu_opcode.value == 0b0111, "C.ANDI uses ANDI opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.imm.value.to_signed() == imm, (
            f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_alu_imm=1)


@cocotb.test()
async def test_c_sub(dut):
    """C.SUB rd', rs2' - Subtract (CA format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        dut.instr.value = rv32c.encode_c_sub(rd, rs2)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs2 = 8 + rs2

        assert dut.alu_opcode.value == 0b1000, "C.SUB uses SUB opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_xor(dut):
    """C.XOR rd', rs2' - Bitwise XOR (CA format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        dut.instr.value = rv32c.encode_c_xor(rd, rs2)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs2 = 8 + rs2

        assert dut.alu_opcode.value == 0b0100, "C.XOR uses XOR opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_or(dut):
    """C.OR rd', rs2' - Bitwise OR (CA format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 7)
        rs2 = random.randint(0, 7)
        dut.instr.value = rv32c.encode_c_or(rd, rs2)
        await ClockCycles(dut.clk, 1)

        expected_rd = 8 + rd
        expected_rs2 = 8 + rs2

        assert dut.alu_opcode.value == 0b0110, "C.OR uses OR opcode"
        assert dut.rd.value == expected_rd, (
            f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        )
        assert dut.rs1.value == expected_rd, (
            f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == expected_rs2, (
            f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        )
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_j(dut):
    """C.J offset - Unconditional jump (CJ format)"""
    await setup_decoder(dut)

    for _ in range(20):
        offset = (
            random.randint(-1024, 1023) << 1
        )  # CJ-type: 12-bit signed (-2048 to +2046)
        dut.instr.value = rv32c.encode_c_j(offset)
        await ClockCycles(dut.clk, 1)

        assert dut.rd.value == 0, "C.J sets rd=x0 (no link)"
        assert dut.imm.value.to_signed() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_jal=1)


@cocotb.test()
async def test_c_beqz(dut):
    """C.BEQZ rs1', offset - Branch if equal to zero (CB format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 7)
        offset = random.randint(-128, 127) << 1  # CB-type: 9-bit signed (-256 to +254)
        dut.instr.value = rv32c.encode_c_beqz(rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b000, "C.BEQZ uses BEQ (mem_opcode=000)"
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == 0, "C.BEQZ compares against x0"
        assert dut.imm.value.to_signed() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_branch=1)


@cocotb.test()
async def test_c_bnez(dut):
    """C.BNEZ rs1', offset - Branch if not equal to zero (CB format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rs1 = random.randint(0, 7)
        offset = random.randint(-128, 127) << 1  # CB-type: 9-bit signed (-256 to +254)
        dut.instr.value = rv32c.encode_c_bnez(rs1, offset)
        await ClockCycles(dut.clk, 1)

        expected_rs1 = 8 + rs1

        assert dut.mem_opcode.value == 0b001, "C.BNEZ uses BNE (mem_opcode=001)"
        assert dut.rs1.value == expected_rs1, (
            f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        )
        assert dut.rs2.value == 0, "C.BNEZ compares against x0"
        assert dut.imm.value.to_signed() == offset, (
            f"offset mismatch: expected {offset}, got {dut.imm.value.to_signed()}"
        )
        _verify_control_flags(dut, is_branch=1)
