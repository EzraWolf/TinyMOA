import cocotb
from random import randint
from cocotb.triggers import Timer

from tests.common import encode_rv32i as rv32i
from tests.common.cpu_types import AluOp
from tests.runner import run


async def _check(
    dut,
    i_instr=0,
    o_rf_wen=0,
    o_rf_dst=0,
    o_rf_src1=0,
    o_rf_src2=0,
    o_fu_op=AluOp.ADD,
    o_imm=0,
    o_mem_ren=0,
    o_mem_wen=0,
    o_funct3=0,
    o_is_load=0,
    o_is_store=0,
    o_is_jump=0,
    o_is_branch=0,
    o_is_illegal=0,
):
    await Timer(1, unit="ns")
    assert dut.i_instr.value == i_instr
    assert dut.o_rf_wen.value == o_rf_wen
    assert dut.o_rf_dst.value == o_rf_dst
    assert dut.o_rf_src1.value == o_rf_src1
    assert dut.o_rf_src2.value == o_rf_src2
    assert dut.o_fu_op.value == o_fu_op
    assert dut.o_imm.value == o_imm
    assert dut.o_mem_ren.value == o_mem_ren
    assert dut.o_mem_wen.value == o_mem_wen
    assert dut.o_funct3.value == o_funct3
    assert dut.o_is_load.value == o_is_load
    assert dut.o_is_store.value == o_is_store
    assert dut.o_is_jump.value == o_is_jump
    assert dut.o_is_branch.value == o_is_branch
    assert dut.o_is_illegal.value == o_is_illegal


async def _r_type(dut, encode, fu_op):
    for _ in range(100):
        rd = randint(0, 31)
        rs1 = randint(0, 31)
        rs2 = randint(0, 31)
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
            o_funct3=(instr >> 12) & 0b111,
        )


async def _i_type(dut, encode, fu_op, funct3):
    for _ in range(100):
        rd = randint(0, 31)
        rs1 = randint(0, 31)
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
            o_imm=imm & 0xFFFF_FFFF,
            o_funct3=funct3,
        )


async def _shift_type(dut, encode, fu_op, funct3, upper=0):
    for _ in range(100):
        rd = randint(0, 31)
        rs1 = randint(0, 31)
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
            o_imm=upper | shamt,
            o_funct3=funct3,
        )


async def _load(dut, encode, funct3):
    for _ in range(100):
        rd = randint(0, 31)
        rs1 = randint(0, 31)
        imm = randint(-2048, 2047)
        instr = encode(rd, rs1, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_imm=imm & 0xFFFF_FFFF,
            o_mem_ren=1,
            o_funct3=funct3,
            o_is_load=1,
        )


async def _store(dut, encode, funct3):
    for _ in range(100):
        rs1 = randint(0, 31)
        rs2 = randint(0, 31)
        imm = randint(-2048, 2047)
        instr = encode(rs1, rs2, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_src1=rs1,
            o_rf_src2=rs2,
            o_imm=imm & 0xFFFF_FFFF,
            o_mem_wen=1,
            o_funct3=funct3,
            o_is_store=1,
        )


async def _branch(dut, encode, funct3):
    for _ in range(100):
        rs1 = randint(0, 31)
        rs2 = randint(0, 31)
        imm = randint(-2048, 2047) * 2
        instr = encode(rs1, rs2, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_src1=rs1,
            o_rf_src2=rs2,
            o_imm=imm & 0xFFFF_FFFF,
            o_funct3=funct3,
            o_is_branch=1,
        )


async def _u_type(dut, encode):
    for _ in range(100):
        rd = randint(0, 31)
        imm = randint(0, 0xF_FFFF)
        instr = encode(rd, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_imm=imm << 12,
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


@cocotb.test()
async def sb(dut):
    await _store(dut, rv32i.encode_sb, 0b000)


@cocotb.test()
async def sh(dut):
    await _store(dut, rv32i.encode_sh, 0b001)


@cocotb.test()
async def sw(dut):
    await _store(dut, rv32i.encode_sw, 0b010)


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
    await _u_type(dut, rv32i.encode_lui)


@cocotb.test()
async def auipc(dut):
    await _u_type(dut, rv32i.encode_auipc)


@cocotb.test()
async def jal(dut):
    for _ in range(100):
        rd = randint(0, 31)
        imm = randint(-(1 << 19), (1 << 19) - 1) * 2
        instr = rv32i.encode_jal(rd, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_imm=imm & 0xFFFF_FFFF,
            o_funct3=(instr >> 12) & 0b111,
            o_is_jump=1,
        )


@cocotb.test()
async def jalr(dut):
    for _ in range(100):
        rd = randint(0, 31)
        rs1 = randint(0, 31)
        imm = randint(-2048, 2047)
        instr = rv32i.encode_jalr(rd, rs1, imm)
        dut.i_instr.value = instr
        await _check(
            dut,
            i_instr=instr,
            o_rf_wen=1,
            o_rf_dst=rd,
            o_rf_src1=rs1,
            o_imm=imm & 0xFFFF_FFFF,
            o_is_jump=1,
        )


def test_cpu_decoder_rv32i():
    run(
        "cpu",
        "decoder",
        ["~pkg_config.sv", "~cpu/pkgs/pkg_cpu_alu.sv", "~cpu/cpu_decoder.sv"],
        test_name="rv32i",
    )
