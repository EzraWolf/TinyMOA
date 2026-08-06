import os
import cocotb
import pytest
from random import randint
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS, N_FUZZ
from tests.common.cpu_types import AluOp, WbSel
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
    dut.i_fu_op.value = AluOp.ADD
    dut.i_fu_data1.value = 0
    dut.i_fu_data2.value = 0
    dut.i_imm.value = 0
    dut.i_funct3.value = 0
    dut.i_is_branch.value = 0
    dut.i_is_jump.value = 0
    dut.i_is_fence.value = 0
    dut.i_is_ecall.value = 0
    dut.i_is_ebreak.value = 0
    dut.i_is_illegal.value = 0
    dut.i_mem_ren.value = 0
    dut.i_mem_wen.value = 0
    dut.i_store_data.value = 0
    dut.i_wb_sel.value = WbSel.NONE
    dut.i_rf_wen.value = 0
    dut.i_rf_dst.value = 0
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
    i_fu_op=AluOp.ADD,
    i_fu_data1=0,
    i_fu_data2=0,
    i_imm=0,
    i_funct3=0,
    i_is_branch=0,
    i_is_jump=0,
    i_is_fence=0,
    i_is_ecall=0,
    i_is_ebreak=0,
    i_is_illegal=0,
    i_mem_ren=0,
    i_mem_wen=0,
    i_store_data=0,
    i_wb_sel=WbSel.NONE,
    i_rf_wen=0,
    i_rf_dst=0,
    o_valid=0,
    o_pc=0,
    o_fu_data=0,
    o_funct3=0,
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
    o_redirect_valid=0,
    o_redirect_pc=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.rst.value == rst
    assert dut.i_flush.value == i_flush
    assert dut.i_valid.value == i_valid
    assert dut.i_ready.value == i_ready
    assert dut.o_ready.value == o_ready
    assert dut.i_pc.value == i_pc
    assert dut.i_fu_op.value == i_fu_op
    assert dut.i_fu_data1.value == i_fu_data1
    assert dut.i_fu_data2.value == i_fu_data2
    assert dut.i_imm.value == i_imm
    assert dut.i_funct3.value == i_funct3
    assert dut.i_is_branch.value == i_is_branch
    assert dut.i_is_jump.value == i_is_jump
    assert dut.i_is_fence.value == i_is_fence
    assert dut.i_is_ecall.value == i_is_ecall
    assert dut.i_is_ebreak.value == i_is_ebreak
    assert dut.i_is_illegal.value == i_is_illegal
    assert dut.i_mem_ren.value == i_mem_ren
    assert dut.i_mem_wen.value == i_mem_wen
    assert dut.i_store_data.value == i_store_data
    assert dut.i_wb_sel.value == i_wb_sel
    assert dut.i_rf_wen.value == i_rf_wen
    assert dut.i_rf_dst.value == i_rf_dst
    assert dut.o_valid.value == o_valid
    assert dut.o_pc.value == o_pc
    assert dut.o_fu_data.value == o_fu_data
    assert dut.o_funct3.value == o_funct3
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
    assert dut.o_redirect_valid.value == o_redirect_valid
    assert dut.o_redirect_pc.value == o_redirect_pc


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    addr_width = (DEPTH - 1).bit_length()
    assert WIDTH == len(dut.i_pc)
    assert WIDTH == len(dut.i_fu_data1)
    assert WIDTH == len(dut.i_fu_data2)
    assert WIDTH == len(dut.i_imm)
    assert WIDTH == len(dut.i_store_data)
    assert addr_width == len(dut.i_rf_dst)
    assert WIDTH == len(dut.o_pc)
    assert WIDTH == len(dut.o_fu_data)
    assert WIDTH == len(dut.o_store_data)
    assert addr_width == len(dut.o_rf_dst)
    assert WIDTH == len(dut.o_redirect_pc)


@cocotb.test()
async def reset_clears_outputs(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_fu_data1.value = 1
    dut.i_fu_data2.value = 2
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_fu_data1=1,
        i_fu_data2=2,
        o_valid=1,
        o_fu_data=3,
    )

    dut.rst.value = 0
    await _check(
        dut,
        rst=0,
        i_valid=1,
        i_ready=1,
        i_fu_data1=1,
        i_fu_data2=2,
    )


@cocotb.test()
async def execute_add_sub(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    for i in range(N_FUZZ):
        a = randint(0, XLEN_MASK)
        b = randint(0, XLEN_MASK)
        op = AluOp.ADD if i % 2 == 0 else AluOp.SUB
        expect = (a + b) & XLEN_MASK if op == AluOp.ADD else (a - b) & XLEN_MASK
        dut.i_fu_op.value = op
        dut.i_fu_data1.value = a
        dut.i_fu_data2.value = b
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            i_ready=1,
            i_fu_op=op,
            i_fu_data1=a,
            i_fu_data2=b,
            o_valid=1,
            o_fu_data=expect,
        )


@cocotb.test()
async def resolve_branch_jump_redirects(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_pc.value = 0x100
    dut.i_imm.value = 8
    dut.i_is_branch.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_imm=8,
        i_is_branch=1,
        o_valid=1,
        o_pc=0x100,
        o_redirect_valid=1,
        o_redirect_pc=0x108,
    )

    dut.i_funct3.value = 1
    dut.i_fu_data1.value = 1
    dut.i_fu_data2.value = 2
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_fu_data1=1,
        i_fu_data2=2,
        i_imm=8,
        i_funct3=1,
        i_is_branch=1,
        o_valid=1,
        o_pc=0x100,
        o_fu_data=3,
        o_funct3=1,
        o_redirect_valid=1,
        o_redirect_pc=0x108,
    )

    dut.i_funct3.value = 0
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_fu_data1=1,
        i_fu_data2=2,
        i_imm=8,
        i_is_branch=1,
        o_valid=1,
        o_pc=0x100,
        o_fu_data=3,
    )

    dut.i_is_branch.value = 0
    dut.i_is_jump.value = 1
    dut.i_fu_data1.value = 0x101
    dut.i_fu_data2.value = 8
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_pc=0x100,
        i_fu_data1=0x101,
        i_fu_data2=8,
        i_imm=8,
        i_is_jump=1,
        o_valid=1,
        o_pc=0x100,
        o_fu_data=0x109,
        o_redirect_valid=1,
        o_redirect_pc=0x108,
    )


@cocotb.test()
async def route_memory_controls(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_funct3.value = 2
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 3
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_funct3=2,
        i_mem_ren=1,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        i_rf_dst=3,
        o_valid=1,
        o_funct3=2,
        o_mem_ren=1,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
        o_rf_dst=3,
    )

    dut.i_funct3.value = 1
    dut.i_mem_ren.value = 0
    dut.i_mem_wen.value = 1
    dut.i_store_data.value = 0x1234
    dut.i_wb_sel.value = WbSel.NONE
    dut.i_rf_wen.value = 0
    dut.i_rf_dst.value = 0
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_funct3=1,
        i_mem_wen=1,
        i_store_data=0x1234,
        o_valid=1,
        o_funct3=1,
        o_mem_wen=1,
        o_store_data=0x1234,
    )


@cocotb.test()
async def route_status_flags(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_is_fence.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, i_is_fence=1, o_valid=1, o_is_fence=1)

    dut.i_is_fence.value = 0
    dut.i_is_ecall.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, i_is_ecall=1, o_valid=1, o_is_ecall=1)

    dut.i_is_ecall.value = 0
    dut.i_is_ebreak.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_is_ebreak=1,
        o_valid=1,
        o_is_ebreak=1,
    )

    dut.i_is_ebreak.value = 0
    dut.i_is_illegal.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_is_illegal=1,
        o_valid=1,
        o_is_illegal=1,
    )


@cocotb.test()
async def one_ipc(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    for i in range(N_FUZZ):
        dut.i_pc.value = i * 4
        dut.i_fu_data1.value = i
        dut.i_fu_data2.value = 1
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            i_ready=1,
            i_pc=i * 4,
            i_fu_data1=i,
            i_fu_data2=1,
            o_valid=1,
            o_pc=i * 4,
            o_fu_data=i + 1,
        )


@cocotb.test()
async def hold_on_backpressure(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data1.value = 1
    dut.i_fu_data2.value = 2
    await FallingEdge(dut.clk)

    dut.i_fu_data1.value = 3
    dut.i_fu_data2.value = 4
    for _ in range(50):
        await _check(
            dut,
            i_valid=1,
            o_ready=0,
            i_fu_data1=3,
            i_fu_data2=4,
            o_valid=1,
            o_fu_data=3,
        )
        await FallingEdge(dut.clk)

    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_fu_data1=3,
        i_fu_data2=4,
        o_valid=1,
        o_fu_data=7,
    )


@cocotb.test()
async def redirect_held_on_backpressure(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = 0x100
    dut.i_imm.value = 8
    dut.i_is_branch.value = 1
    await FallingEdge(dut.clk)

    dut.i_pc.value = 0
    dut.i_imm.value = 0
    dut.i_is_branch.value = 0
    for _ in range(50):
        await _check(
            dut,
            i_valid=1,
            o_ready=0,
            o_valid=1,
            o_pc=0x100,
            o_redirect_valid=1,
            o_redirect_pc=0x108,
        )
        await FallingEdge(dut.clk)

    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, o_valid=1)


@cocotb.test()
async def redirect_cleared_on_flush(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = 0x100
    dut.i_imm.value = 8
    dut.i_is_branch.value = 1
    await FallingEdge(dut.clk)

    dut.i_flush.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_pc=0x100,
        i_imm=8,
        i_is_branch=1,
        o_pc=0x100,
        o_redirect_pc=0x108,
    )


@cocotb.test()
async def flush_drops_output(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data1.value = 1
    dut.i_fu_data2.value = 2
    await FallingEdge(dut.clk)

    dut.i_flush.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_fu_data1=1,
        i_fu_data2=2,
        o_fu_data=3,
    )


@pytest.mark.parametrize(
    "p",
    [
        pytest.param({"WIDTH": 32, "DEPTH": 32}, id="rv32i"),
        pytest.param({"WIDTH": 32, "DEPTH": 16}, id="rv32e"),
        pytest.param({"WIDTH": 64, "DEPTH": 32}, id="rv64i"),
        pytest.param({"WIDTH": 64, "DEPTH": 16}, id="rv64e"),
    ],
)
def test_ecore_stage_execute(p):
    run(
        "ecore",
        "stage_execute",
        [
            "~ecore/pkgs/ecore_pkg_cfg.sv",
            "~ecore/pkgs/ecore_pkg_alu.sv",
            "~ecore/ecore_alu.sv",
            "~ecore/ecore_bru.sv",
            "~ecore/stages/ecore_stage_execute.sv",
        ],
        params=p,
    )
