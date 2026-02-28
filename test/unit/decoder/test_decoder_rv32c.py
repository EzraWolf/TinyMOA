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


# === Compressed ALU Operations ===


@cocotb.test()
async def test_c_add(dut):
    """C.ADD rd, rs2 - Add register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(1, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32c.encode_c_add(rd, rs2)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.ADD uses ADD opcode"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert (
            dut.rs1.value == rd
        ), f"rs1 mismatch: expected x{rd}, got x{dut.rs1.value}"
        assert (
            dut.rs2.value == rs2
        ), f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
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
        assert (
            dut.rd.value == expected_rd
        ), f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        assert (
            dut.rs1.value == expected_rd
        ), f"rs1 mismatch: expected x{expected_rd}, got x{dut.rs1.value}"
        assert (
            dut.rs2.value == expected_rs2
        ), f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        _verify_control_flags(dut, is_alu_reg=1)


@cocotb.test()
async def test_c_mv(dut):
    """C.MV rd, rs2 - Copy register (CR format)"""
    await setup_decoder(dut)

    for _ in range(20):
        rd = random.randint(0, 15)
        rs2 = random.randint(0, 15)
        dut.instr.value = rv32c.encode_c_mv(rd, rs2)
        await ClockCycles(dut.clk, 1)

        assert dut.alu_opcode.value == 0b0000, "C.MV uses ADD opcode (rd = x0 + rs2)"
        assert dut.rd.value == rd, f"rd mismatch: expected x{rd}, got x{dut.rd.value}"
        assert dut.rs1.value == 0, "C.MV uses x0 as rs1"
        assert (
            dut.rs2.value == rs2
        ), f"rs2 mismatch: expected x{rs2}, got x{dut.rs2.value}"
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
        assert (
            dut.imm.value.to_signed() == imm
        ), f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
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
        assert (
            dut.rs1.value == rd
        ), f"rs1 mismatch: expected x{rd}, got x{dut.rs1.value}"
        assert (
            dut.imm.value.to_signed() == imm
        ), f"imm mismatch: expected {imm}, got {dut.imm.value.to_signed()}"
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
        assert (
            dut.rd.value == expected_rd
        ), f"rd mismatch: expected x{expected_rd}, got x{dut.rd.value}"
        assert (
            dut.rs1.value == expected_rs1
        ), f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        assert (
            dut.imm.value.to_unsigned() == offset
        ), f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
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
        assert (
            dut.rs1.value == expected_rs1
        ), f"rs1 mismatch: expected x{expected_rs1}, got x{dut.rs1.value}"
        assert (
            dut.rs2.value == expected_rs2
        ), f"rs2 mismatch: expected x{expected_rs2}, got x{dut.rs2.value}"
        assert (
            dut.imm.value.to_unsigned() == offset
        ), f"offset mismatch: expected {offset}, got {dut.imm.value.to_unsigned()}"
        _verify_control_flags(dut, is_store=1)
