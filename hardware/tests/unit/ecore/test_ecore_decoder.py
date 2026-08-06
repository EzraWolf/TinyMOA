import os
import cocotb
import pytest
from random import randint
from cocotb.triggers import Timer

from tests import CHECK_DELAY_NS, N_FUZZ
from tests.common import encode_rv32i as rv32i
from tests.common.cpu_types import AluOp, FuSrc1, FuSrc2, WbSel
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
REG_NUM = int(os.environ.get("REG_NUM", 32))


async def _check(
    dut,
    i_instr=0,
    o_rf_wen=0,
    o_rf_dst=0,
    o_rf_src1=0,
    o_rf_src2=0,
    o_fu_op=AluOp.ADD,
    o_fu_src1=FuSrc1.NONE,
    o_fu_src2=FuSrc2.NONE,
    o_imm=0,
    o_mem_ren=0,
    o_mem_wen=0,
    o_wb_sel=WbSel.NONE,
    o_funct3=0,
    o_is_load=0,
    o_is_store=0,
    o_is_jump=0,
    o_is_branch=0,
    o_is_fence=0,
    o_is_ecall=0,
    o_is_ebreak=0,
    o_is_illegal=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.i_instr.value == i_instr
    assert dut.o_rf_wen.value == o_rf_wen
    assert dut.o_rf_dst.value == o_rf_dst
    assert dut.o_rf_src1.value == o_rf_src1
    assert dut.o_rf_src2.value == o_rf_src2
    assert dut.o_fu_op.value == o_fu_op
    assert dut.o_fu_src1.value == o_fu_src1
    assert dut.o_fu_src2.value == o_fu_src2
    assert dut.o_imm.value == o_imm
    assert dut.o_mem_ren.value == o_mem_ren
    assert dut.o_mem_wen.value == o_mem_wen
    assert dut.o_wb_sel.value == o_wb_sel
    assert dut.o_funct3.value == o_funct3
    assert dut.o_is_load.value == o_is_load
    assert dut.o_is_store.value == o_is_store
    assert dut.o_is_jump.value == o_is_jump
    assert dut.o_is_branch.value == o_is_branch
    assert dut.o_is_fence.value == o_is_fence
    assert dut.o_is_ecall.value == o_is_ecall
    assert dut.o_is_ebreak.value == o_is_ebreak
    assert dut.o_is_illegal.value == o_is_illegal


async def _r_type(dut, encode, fu_op):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        rs1 = randint(0, REG_NUM - 1)
        rs2 = randint(0, REG_NUM - 1)
        instr = encode(rd, rs1, rs2)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_rf_src2=rs2,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.REG,
            o_wb_sel=WbSel.FU,
            o_funct3=(instr >> 12) & 0b111,
        )


async def _i_type(dut, encode, fu_op, funct3):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        rs1 = randint(0, REG_NUM - 1)
        imm = randint(-2048, 2047)
        instr = encode(rd, rs1, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_wb_sel=WbSel.FU,
            o_funct3=funct3,
        )


async def _shift_type(dut, encode, fu_op, funct3, upper=0):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        rs1 = randint(0, REG_NUM - 1)
        shamt = randint(0, 31)
        instr = encode(rd, rs1, shamt)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=upper | shamt,
            o_wb_sel=WbSel.FU,
            o_funct3=funct3,
        )


async def _load(dut, encode, funct3):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        rs1 = randint(0, REG_NUM - 1)
        imm = randint(-2048, 2047)
        instr = encode(rd, rs1, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_mem_ren=1,
            o_wb_sel=WbSel.MEM,
            o_funct3=funct3,
            o_is_load=1,
        )


async def _store(dut, encode, funct3):
    for _ in range(N_FUZZ):
        rs1 = randint(0, REG_NUM - 1)
        rs2 = randint(0, REG_NUM - 1)
        imm = randint(-2048, 2047)
        instr = encode(rs1, rs2, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_src1=rs1,
            o_rf_src2=rs2,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_mem_wen=1,
            o_funct3=funct3,
            o_is_store=1,
        )


async def _branch(dut, encode, funct3):
    for _ in range(N_FUZZ):
        rs1 = randint(0, REG_NUM - 1)
        rs2 = randint(0, REG_NUM - 1)
        imm = randint(-2048, 2047) * 2
        instr = encode(rs1, rs2, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_src1=rs1,
            o_rf_src2=rs2,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.REG,
            o_imm=imm & 0xFFFF_FFFF,
            o_funct3=funct3,
            o_is_branch=1,
        )


async def _u_type(dut, encode, fu_src1):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        imm = randint(0, 0xF_FFFF)
        instr = encode(rd, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_fu_src1=fu_src1,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm << 12,
            o_wb_sel=WbSel.FU,
            o_funct3=imm & 0b111,
        )


@cocotb.test()
async def add(dut):
    await _r_type(dut, rv32i.encode_add, AluOp.ADD)


@cocotb.test()
async def sub(dut):
    await _r_type(dut, rv32i.encode_sub, AluOp.SUB)


@cocotb.test()
async def and_(dut):
    await _r_type(dut, rv32i.encode_and, AluOp.AND)


@cocotb.test()
async def or_(dut):
    await _r_type(dut, rv32i.encode_or, AluOp.OR)


@cocotb.test()
async def xor(dut):
    await _r_type(dut, rv32i.encode_xor, AluOp.XOR)


@cocotb.test()
async def slt(dut):
    await _r_type(dut, rv32i.encode_slt, AluOp.SLT)


@cocotb.test()
async def sltu(dut):
    await _r_type(dut, rv32i.encode_sltu, AluOp.SLTU)


@cocotb.test()
async def sll(dut):
    await _r_type(dut, rv32i.encode_sll, AluOp.SLL)


@cocotb.test()
async def srl(dut):
    await _r_type(dut, rv32i.encode_srl, AluOp.SRL)


@cocotb.test()
async def sra(dut):
    await _r_type(dut, rv32i.encode_sra, AluOp.SRA)


@cocotb.test()
async def addi(dut):
    await _i_type(dut, rv32i.encode_addi, AluOp.ADD, 0b000)


@cocotb.test()
async def andi(dut):
    await _i_type(dut, rv32i.encode_andi, AluOp.AND, 0b111)


@cocotb.test()
async def ori(dut):
    await _i_type(dut, rv32i.encode_ori, AluOp.OR, 0b110)


@cocotb.test()
async def xori(dut):
    await _i_type(dut, rv32i.encode_xori, AluOp.XOR, 0b100)


@cocotb.test()
async def slti(dut):
    await _i_type(dut, rv32i.encode_slti, AluOp.SLT, 0b010)


@cocotb.test()
async def sltiu(dut):
    await _i_type(dut, rv32i.encode_sltiu, AluOp.SLTU, 0b011)


@cocotb.test()
async def slli(dut):
    await _shift_type(dut, rv32i.encode_slli, AluOp.SLL, 0b001)


@cocotb.test()
async def srli(dut):
    await _shift_type(dut, rv32i.encode_srli, AluOp.SRL, 0b101)


@cocotb.test()
async def srai(dut):
    await _shift_type(dut, rv32i.encode_srai, AluOp.SRA, 0b101, 0x400)


@cocotb.test(skip=(WIDTH < 64))
async def rv64_shift_immediates_use_six_bit_shamt(dut):
    for funct3, upper, fu_op in (
        (0b001, 0x000, AluOp.SLL),
        (0b101, 0x000, AluOp.SRL),
        (0b101, 0x400, AluOp.SRA),
    ):
        instr = rv32i.encode_i_type(upper | 40, 1, funct3, 2, 0x13)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=2,
            o_rf_src1=1,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=upper | 40,
            o_wb_sel=WbSel.FU,
            o_funct3=funct3,
        )


@cocotb.test(skip=(WIDTH < 64))
async def op_imm_32(dut):
    cases = (
        (0b000, -1, AluOp.ADDW),
        (0b001, 31, AluOp.SLLW),
        (0b101, 31, AluOp.SRLW),
        (0b101, 0x400 | 31, AluOp.SRAW),
    )
    for funct3, imm, fu_op in cases:
        instr = rv32i.encode_i_type(imm, 1, funct3, 2, 0x1B)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=2,
            o_rf_src1=1,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_wb_sel=WbSel.FU,
            o_funct3=funct3,
        )


@cocotb.test(skip=(WIDTH < 64))
async def op_32(dut):
    cases = (
        (0x00, 0b000, AluOp.ADDW),
        (0x20, 0b000, AluOp.SUBW),
        (0x00, 0b001, AluOp.SLLW),
        (0x00, 0b101, AluOp.SRLW),
        (0x20, 0b101, AluOp.SRAW),
    )
    for funct7, funct3, fu_op in cases:
        instr = rv32i.encode_r_type(funct7, 3, 1, funct3, 2, 0x3B)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=2,
            o_rf_src1=1,
            o_rf_src2=3,
            o_fu_op=fu_op,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.REG,
            o_wb_sel=WbSel.FU,
            o_funct3=funct3,
        )


@cocotb.test()
async def lb(dut):
    await _load(dut, rv32i.encode_lb, 0b000)


@cocotb.test()
async def lh(dut):
    await _load(dut, rv32i.encode_lh, 0b001)


@cocotb.test()
async def lw(dut):
    await _load(dut, rv32i.encode_lw, 0b010)


@cocotb.test()
async def lbu(dut):
    await _load(dut, rv32i.encode_lbu, 0b100)


@cocotb.test()
async def lhu(dut):
    await _load(dut, rv32i.encode_lhu, 0b101)


@cocotb.test(skip=(WIDTH < 64))
async def ld(dut):
    await _load(
        dut, lambda rd, rs1, imm: rv32i.encode_i_type(imm, rs1, 0b011, rd, 0x03), 0b011
    )


@cocotb.test(skip=(WIDTH < 64))
async def lwu(dut):
    await _load(
        dut, lambda rd, rs1, imm: rv32i.encode_i_type(imm, rs1, 0b110, rd, 0x03), 0b110
    )


@cocotb.test()
async def sb(dut):
    await _store(dut, rv32i.encode_sb, 0b000)


@cocotb.test()
async def sh(dut):
    await _store(dut, rv32i.encode_sh, 0b001)


@cocotb.test()
async def sw(dut):
    await _store(dut, rv32i.encode_sw, 0b010)


@cocotb.test(skip=(WIDTH < 64))
async def sd(dut):
    await _store(
        dut,
        lambda rs1, rs2, imm: rv32i.encode_s_type(imm, rs2, rs1, 0b011, 0x23),
        0b011,
    )


@cocotb.test()
async def beq(dut):
    await _branch(dut, rv32i.encode_beq, 0b000)


@cocotb.test()
async def bne(dut):
    await _branch(dut, rv32i.encode_bne, 0b001)


@cocotb.test()
async def blt(dut):
    await _branch(dut, rv32i.encode_blt, 0b100)


@cocotb.test()
async def bge(dut):
    await _branch(dut, rv32i.encode_bge, 0b101)


@cocotb.test()
async def bltu(dut):
    await _branch(dut, rv32i.encode_bltu, 0b110)


@cocotb.test()
async def bgeu(dut):
    await _branch(dut, rv32i.encode_bgeu, 0b111)


@cocotb.test()
async def lui(dut):
    await _u_type(dut, rv32i.encode_lui, FuSrc1.NONE)


@cocotb.test()
async def auipc(dut):
    await _u_type(dut, rv32i.encode_auipc, FuSrc1.PC)


@cocotb.test()
async def jal(dut):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        imm = randint(-(1 << 19), (1 << 19) - 1) * 2
        instr = rv32i.encode_jal(rd, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_fu_src1=FuSrc1.PC,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_wb_sel=WbSel.PC,
            o_funct3=(instr >> 12) & 0b111,
            o_is_jump=1,
        )


@cocotb.test()
async def jalr(dut):
    for _ in range(N_FUZZ):
        rd = randint(0, REG_NUM - 1)
        rs1 = randint(0, REG_NUM - 1)
        imm = randint(-2048, 2047)
        instr = rv32i.encode_jalr(rd, rs1, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_fu_src1=FuSrc1.REG,
            o_fu_src2=FuSrc2.IMM,
            o_imm=imm & 0xFFFF_FFFF,
            o_wb_sel=WbSel.PC,
            o_is_jump=1,
        )


@cocotb.test()
async def fence(dut):
    for _ in range(N_FUZZ):
        instr = rv32i.encode_i_type(
            randint(0, 0xFFF), randint(0, 31), 0, randint(0, 31), 0x0F
        )
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_is_fence=1)


@cocotb.test()
async def ecall(dut):
    instr = rv32i.encode_ecall()
    dut.i_instr.value = instr
    await _check(dut, i_instr=instr, o_is_ecall=1)


@cocotb.test()
async def ebreak(dut):
    instr = rv32i.encode_ebreak()
    dut.i_instr.value = instr
    await _check(dut, i_instr=instr, o_is_ebreak=1)


@cocotb.test()
async def illegal_quadrant(dut):
    for _ in range(N_FUZZ):
        instr = (randint(0, (1 << 30) - 1) << 2) | randint(0, 2)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_is_illegal=1)


@cocotb.test()
async def illegal_opcode(dut):
    valid = {0x00, 0x03, 0x04, 0x05, 0x08, 0x0C, 0x0D, 0x18, 0x19, 0x1B, 0x1C}
    if WIDTH >= 64:
        valid |= {0x06, 0x0E}
    for op in set(range(32)) - valid:
        instr = (randint(0, (1 << 25) - 1) << 7) | (op << 2) | 0b11
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_funct3=(instr >> 12) & 0b111,
            o_is_illegal=1,
        )


@cocotb.test()
async def illegal_r_type(dut):
    legal = {
        (0b000, 0x00),
        (0b000, 0x20),
        (0b111, 0x00),
        (0b110, 0x00),
        (0b100, 0x00),
        (0b001, 0x00),
        (0b101, 0x00),
        (0b101, 0x20),
        (0b010, 0x00),
        (0b011, 0x00),
    }
    for _ in range(N_FUZZ):
        funct3 = randint(0, 7)
        funct7 = randint(0, 127)
        if (funct3, funct7) in legal:
            funct7 = 0x01
        instr = rv32i.encode_r_type(funct7, 1, 2, funct3, 3, 0x33)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_shift(dut):
    legal_sll = {0x00, 0x01} if WIDTH >= 64 else {0x00}
    legal_sr = {0x00, 0x01, 0x20, 0x21} if WIDTH >= 64 else {0x00, 0x20}
    for funct3, legal in ((0b001, legal_sll), (0b101, legal_sr)):
        for funct7 in set(range(128)) - legal:
            instr = rv32i.encode_i_type(funct7 << 5, 1, funct3, 2, 0x13)
            dut.i_instr.value = instr
            await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_load(dut):
    illegal = (0b111,) if WIDTH >= 64 else (0b011, 0b110, 0b111)
    for funct3 in illegal:
        instr = rv32i.encode_i_type(0, 1, funct3, 2, 0x03)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_store(dut):
    first_illegal = 0b100 if WIDTH >= 64 else 0b011
    for funct3 in range(first_illegal, 0b1000):
        instr = rv32i.encode_s_type(0, 2, 1, funct3, 0x23)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_branch(dut):
    for funct3 in (0b010, 0b011):
        instr = rv32i.encode_b_type(0, 2, 1, funct3, 0x63)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_jalr(dut):
    for funct3 in range(1, 8):
        instr = rv32i.encode_i_type(0, 1, funct3, 2, 0x67)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_fence(dut):
    for funct3 in range(1, 8):
        instr = rv32i.encode_i_type(0, 0, funct3, 0, 0x0F)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def illegal_system(dut):
    for funct3 in range(8):
        instr = rv32i.encode_i_type(2, 1, funct3, 1, 0x73)
        dut.i_instr.value = instr
        await _check(dut, i_instr=instr, o_funct3=funct3, o_is_illegal=1)


@cocotb.test()
async def highest_architectural_register_is_legal(dut):
    reg = REG_NUM - 1
    legal = rv32i.encode_add(reg, reg, reg)
    dut.i_instr.value = legal
    await _check(
        dut,
        i_instr=legal,
        o_rf_wen=1,
        o_rf_dst=reg,
        o_rf_src1=reg,
        o_rf_src2=reg,
        o_fu_src1=FuSrc1.REG,
        o_fu_src2=FuSrc2.REG,
        o_wb_sel=WbSel.FU,
    )


@cocotb.test(skip=(REG_NUM > 16))
async def registers_above_x15_are_illegal(dut):
    illegal = (
        (rv32i.encode_add(16, 1, 2), 0b000),
        (rv32i.encode_add(1, 16, 2), 0b000),
        (rv32i.encode_add(1, 2, 16), 0b000),
        (rv32i.encode_sw(1, 16, 0), 0b010),
    )
    for instr, funct3 in illegal:
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_funct3=funct3,
            o_is_illegal=1,
        )


@pytest.mark.parametrize(
    "p",
    [
        pytest.param({"WIDTH": 32, "REG_NUM": 32}, id="rv32i"),
        pytest.param({"WIDTH": 32, "REG_NUM": 16}, id="rv32e"),
        pytest.param({"WIDTH": 64, "REG_NUM": 32}, id="rv64i"),
        pytest.param({"WIDTH": 64, "REG_NUM": 16}, id="rv64e"),
    ],
)
def test_ecore_decoder(p):
    run(
        "ecore",
        "decoder",
        [
            "~ecore/pkgs/ecore_pkg_cfg.sv",
            "~ecore/pkgs/ecore_pkg_alu.sv",
            "~ecore/ecore_decoder.sv",
        ],
        params=p,
    )
