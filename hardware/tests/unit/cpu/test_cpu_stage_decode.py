import os
import cocotb
import pytest
from random import randint
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.common.cpu_types import AluOp, WbSel
from tests.common import encode_rv32i as rv32i
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
DEPTH = int(os.environ.get("DEPTH", 32))
XLEN_MASK = (1 << WIDTH) - 1


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    dut.rst.value = 0
    dut.i_flush.value = 0
    dut.i_valid.value = 0
    dut.i_pc.value = 0
    dut.i_instr.value = 0
    dut.i_ex_rf_wen.value = 0
    dut.i_ex_rf_dst.value = 0
    dut.i_mem_rf_wen.value = 0
    dut.i_mem_rf_dst.value = 0
    dut.i_wb_wen.value = 0
    dut.i_wb_dst.value = 0
    dut.i_wb_data.value = 0
    dut.i_ready.value = 0

    await FallingEdge(dut.clk)
    dut.rst.value = 1

    await _check(dut)


async def _check(
    dut,
    rst=1,
    i_flush=0,
    i_valid=0,
    i_ready=0,
    o_ready=1,
    i_pc=0,
    i_instr=0,
    i_ex_rf_wen=0,
    i_ex_rf_dst=0,
    i_mem_rf_wen=0,
    i_mem_rf_dst=0,
    i_wb_wen=0,
    i_wb_dst=0,
    i_wb_data=0,
    o_valid=0,
    o_pc=0,
    o_fu_op=AluOp.ADD,
    o_fu_data1=0,
    o_fu_data2=0,
    o_imm=0,
    o_funct3=0,
    o_is_branch=0,
    o_is_jump=0,
    o_is_fence=0,
    o_is_ecall=0,
    o_is_ebreak=0,
    o_is_illegal=0,
    o_mem_ren=0,
    o_mem_wen=0,
    o_store_data=0,
    o_wb_sel=WbSel.NONE,
    o_rf_wen=0,
    o_rf_dst=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.rst.value == rst
    assert dut.i_flush.value == i_flush
    assert dut.i_valid.value == i_valid
    assert dut.o_ready.value == o_ready
    assert dut.i_pc.value == i_pc
    assert dut.i_instr.value == i_instr
    assert dut.i_ex_rf_wen.value == i_ex_rf_wen
    assert dut.i_ex_rf_dst.value == i_ex_rf_dst
    assert dut.i_mem_rf_wen.value == i_mem_rf_wen
    assert dut.i_mem_rf_dst.value == i_mem_rf_dst
    assert dut.i_wb_wen.value == i_wb_wen
    assert dut.i_wb_dst.value == i_wb_dst
    assert dut.i_wb_data.value == i_wb_data
    assert dut.o_valid.value == o_valid
    assert dut.i_ready.value == i_ready
    assert dut.o_pc.value == o_pc
    assert dut.o_fu_op.value == o_fu_op
    assert dut.o_fu_data1.value == o_fu_data1
    assert dut.o_fu_data2.value == o_fu_data2
    assert dut.o_imm.value == o_imm
    assert dut.o_funct3.value == o_funct3
    assert dut.o_is_branch.value == o_is_branch
    assert dut.o_is_jump.value == o_is_jump
    assert dut.o_is_fence.value == o_is_fence
    assert dut.o_is_ecall.value == o_is_ecall
    assert dut.o_is_ebreak.value == o_is_ebreak
    assert dut.o_is_illegal.value == o_is_illegal
    assert dut.o_mem_ren.value == o_mem_ren
    assert dut.o_mem_wen.value == o_mem_wen
    assert dut.o_store_data.value == o_store_data
    assert dut.o_wb_sel.value == o_wb_sel
    assert dut.o_rf_wen.value == o_rf_wen
    assert dut.o_rf_dst.value == o_rf_dst


async def _write(dut, dst, data):
    dut.i_wb_wen.value = 1
    dut.i_wb_dst.value = dst
    dut.i_wb_data.value = data

    await FallingEdge(dut.clk)
    dut.i_wb_wen.value = 0
    dut.i_wb_dst.value = 0
    dut.i_wb_data.value = 0


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    addr_width = (DEPTH - 1).bit_length()
    assert WIDTH == len(dut.i_pc)
    assert addr_width == len(dut.i_ex_rf_dst)
    assert addr_width == len(dut.i_mem_rf_dst)
    assert addr_width == len(dut.i_wb_dst)
    assert WIDTH == len(dut.i_wb_data)
    assert WIDTH == len(dut.o_pc)
    assert WIDTH == len(dut.o_fu_data1)
    assert WIDTH == len(dut.o_fu_data2)
    assert WIDTH == len(dut.o_imm)
    assert WIDTH == len(dut.o_store_data)
    assert addr_width == len(dut.o_rf_dst)


@cocotb.test()
async def reset_clears(dut):
    await setup(dut)

    data = randint(1, XLEN_MASK)
    instr = rv32i.encode_add(2, 1, 0)
    await _write(dut, 1, data)
    dut.i_valid.value = 1
    dut.i_pc.value = 4
    dut.i_instr.value = instr
    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=4,
        i_instr=instr,
        o_valid=1,
        o_pc=4,
        o_fu_data1=data,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=2,
    )

    dut.rst.value = 0
    await _check(
        dut,
        rst=0,
        i_valid=1,
        i_ready=1,
        i_pc=4,
        i_instr=instr,
        # o_fu_data1=data,
    )
    dut.rst.value = 1

    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=4,
        i_instr=instr,
        o_valid=1,
        o_pc=4,
        o_fu_data1=data,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=2,
    )


@cocotb.test()
async def route_fu_data(dut):
    await setup(dut)

    data1 = randint(0, XLEN_MASK)
    data2 = randint(0, XLEN_MASK)
    await _write(dut, 1, data1)
    await _write(dut, 2, data2)

    instr = rv32i.encode_add(3, 1, 2)
    dut.i_valid.value = 1
    dut.i_pc.value = 0x100
    dut.i_instr.value = instr
    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=data1,
        o_fu_data2=data2,
        o_store_data=data2,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=3,
    )

    imm = randint(1, 2047)
    imm_data = imm & XLEN_MASK
    instr = rv32i.encode_addi(3, 1, imm)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=data1,
        o_fu_data2=imm_data,
        o_imm=imm_data,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=3,
    )

    imm = randint(-2048, -1)
    imm_data = imm & XLEN_MASK
    instr = rv32i.encode_addi(3, 1, imm)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=data1,
        o_fu_data2=imm_data,
        o_imm=imm_data,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=3,
    )

    instr = rv32i.encode_sw(1, 2, imm)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=data1,
        o_fu_data2=imm_data,
        o_imm=imm_data,
        o_funct3=2,
        o_mem_wen=1,
        o_store_data=data2,
    )

    instr = rv32i.encode_lw(3, 1, imm)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=data1,
        o_fu_data2=imm_data,
        o_imm=imm_data,
        o_funct3=2,
        o_mem_ren=1,
        o_store_data=0,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
        o_rf_dst=3,
    )


@cocotb.test()
async def route_control(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_pc.value = 0x100

    instr = rv32i.encode_beq(0, 0, 8)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_imm=8,
        o_is_branch=1,
    )

    instr = rv32i.encode_jal(1, 8)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=0x100,
        o_fu_data2=8,
        o_imm=8,
        o_is_jump=1,
        o_wb_sel=WbSel.PC,
        o_rf_wen=1,
        o_rf_dst=1,
    )

    instr = rv32i.encode_auipc(1, 1)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_instr=instr,
        o_valid=1,
        o_pc=0x100,
        o_fu_data1=0x100,
        o_fu_data2=0x1000,
        o_imm=0x1000,
        o_funct3=1,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )


@cocotb.test()
async def route_status(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1

    instr = rv32i.encode_fence(0b1111, 0b1111)
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=instr,
        o_valid=1,
        o_is_fence=1,
    )

    instr = rv32i.encode_ecall()
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=instr,
        o_valid=1,
        o_is_ecall=1,
    )

    instr = rv32i.encode_ebreak()
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=instr,
        o_valid=1,
        o_is_ebreak=1,
    )

    dut.i_instr.value = 0
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        o_valid=1,
        o_is_illegal=1,
    )


@cocotb.test()
async def writeback(dut):
    await setup(dut)

    data = randint(1, XLEN_MASK)
    await _write(dut, 1, data)
    await _write(dut, 0, randint(1, XLEN_MASK))

    instr = rv32i.encode_add(2, 1, 0)
    dut.i_valid.value = 1
    dut.i_instr.value = instr
    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=instr,
        o_valid=1,
        o_fu_data1=data,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=2,
    )


@cocotb.test()
async def one_ipc(dut):
    await setup(dut)

    instrs = [
        (rv32i.encode_add(1, 0, 0), AluOp.ADD, 0),
        (rv32i.encode_sub(2, 0, 0), AluOp.SUB, 0),
        (rv32i.encode_xor(3, 0, 0), AluOp.XOR, 4),
    ]
    dut.i_valid.value = 1
    dut.i_ready.value = 1
    for pc, (instr, fu_op, funct3) in enumerate(instrs):
        dut.i_pc.value = pc * 4
        dut.i_instr.value = instr
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            i_ready=1,
            i_pc=pc * 4,
            i_instr=instr,
            o_valid=1,
            o_pc=pc * 4,
            o_fu_op=fu_op,
            o_funct3=funct3,
            o_wb_sel=WbSel.FU,
            o_rf_wen=1,
            o_rf_dst=pc + 1,
        )


@cocotb.test()
async def hold_on_backpressure(dut):
    await setup(dut)

    instr1 = rv32i.encode_add(1, 0, 0)
    instr2 = rv32i.encode_sub(2, 0, 0)
    dut.i_valid.value = 1
    dut.i_pc.value = 4
    dut.i_instr.value = instr1
    await FallingEdge(dut.clk)

    dut.i_pc.value = 8
    dut.i_instr.value = instr2
    for _ in range(50):
        await _check(
            dut,
            i_valid=1,
            o_ready=0,
            i_pc=8,
            i_instr=instr2,
            o_valid=1,
            o_pc=4,
            o_wb_sel=WbSel.FU,
            o_rf_wen=1,
            o_rf_dst=1,
        )
        await FallingEdge(dut.clk)

    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=8,
        i_instr=instr2,
        o_valid=1,
        o_pc=8,
        o_fu_op=AluOp.SUB,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=2,
    )


@cocotb.test()
async def stall_on_raw_hazard(dut):
    await setup(dut)
    await _write(dut, 1, 0)

    producer = rv32i.encode_addi(1, 0, 1)
    consumer = rv32i.encode_add(2, 1, 0)
    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_instr.value = producer
    await FallingEdge(dut.clk)

    dut.i_instr.value = consumer
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        o_ready=0,
        i_instr=consumer,
        o_valid=1,
        o_fu_data2=1,
        o_imm=1,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=consumer,
        o_fu_data2=1,
        o_imm=1,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )

    dut.i_ex_rf_wen.value = 1
    dut.i_ex_rf_dst.value = 1
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        o_ready=0,
        i_instr=consumer,
        i_ex_rf_wen=1,
        i_ex_rf_dst=1,
        o_fu_data2=1,
        o_imm=1,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )

    dut.i_ex_rf_wen.value = 0
    dut.i_ex_rf_dst.value = 0
    dut.i_mem_rf_wen.value = 1
    dut.i_mem_rf_dst.value = 1
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        o_ready=0,
        i_instr=consumer,
        i_mem_rf_wen=1,
        i_mem_rf_dst=1,
        o_fu_data2=1,
        o_imm=1,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )

    dut.i_mem_rf_wen.value = 0
    dut.i_mem_rf_dst.value = 0
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_instr=consumer,
        o_valid=1,
        o_fu_op=AluOp.ADD,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=2,
    )


@cocotb.test()
async def flush(dut):
    await setup(dut)

    instr = rv32i.encode_add(1, 0, 0)
    dut.i_valid.value = 1
    dut.i_pc.value = 4
    dut.i_instr.value = instr
    await FallingEdge(dut.clk)

    dut.i_flush.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_pc=4,
        i_instr=instr,
        o_pc=4,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=1,
    )


@pytest.mark.parametrize(
    "p",
    [
        {"WIDTH": 32, "DEPTH": 16},
        {"WIDTH": 32, "DEPTH": 32},
        {"WIDTH": 64, "DEPTH": 16},
        {"WIDTH": 64, "DEPTH": 32},
    ],
)
def test_cpu_stage_decode(p):
    run(
        "cpu",
        "stage_decode",
        [
            "~pkg_config.sv",
            "~cpu/pkgs/pkg_cpu_alu.sv",
            "~cpu/cpu_decoder.sv",
            "~cpu/cpu_regfile.sv",
            "~cpu/stages/cpu_stage_decode.sv",
        ],
        params=p,
    )
