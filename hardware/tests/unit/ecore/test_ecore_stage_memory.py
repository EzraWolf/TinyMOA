import os
import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS, N_FUZZ
from tests.common.cpu_types import MemOp, WbSel
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
DEPTH = int(os.environ.get("DEPTH", 32))
BYTES = WIDTH // 8


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    dut.rst.value = 0
    dut.i_flush.value = 0
    dut.i_valid.value = 0
    dut.i_ready.value = 0
    dut.i_pc.value = 0
    dut.i_fu_data.value = 0
    dut.i_funct3.value = MemOp.BYTE
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
    dut.i_dmem_ready.value = 0
    dut.i_dmem_rdata.value = 0

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
    i_fu_data=0,
    i_funct3=MemOp.BYTE,
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
    o_dmem_valid=0,
    i_dmem_ready=0,
    o_dmem_ren=0,
    o_dmem_wen=0,
    o_dmem_addr=0,
    o_dmem_wdata=0,
    o_dmem_wmask=0,
    i_dmem_rdata=0,
    o_valid=0,
    o_pc=0,
    o_fu_data=0,
    o_load_data=0,
    o_is_fence=0,
    o_is_ecall=0,
    o_is_ebreak=0,
    o_is_illegal=0,
    o_mem_error=0,
    o_wb_sel=WbSel.NONE,
    o_rf_wen=0,
    o_rf_dst=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.rst.value == rst
    assert dut.i_flush.value == i_flush
    assert dut.i_valid.value == i_valid
    assert dut.i_ready.value == i_ready
    assert dut.o_ready.value == o_ready
    assert dut.i_pc.value == i_pc
    assert dut.i_fu_data.value == i_fu_data
    assert dut.i_funct3.value == i_funct3
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
    assert dut.o_dmem_valid.value == o_dmem_valid
    assert dut.i_dmem_ready.value == i_dmem_ready
    assert dut.o_dmem_ren.value == o_dmem_ren
    assert dut.o_dmem_wen.value == o_dmem_wen
    assert dut.o_dmem_addr.value == o_dmem_addr
    assert dut.o_dmem_wdata.value == o_dmem_wdata
    assert dut.o_dmem_wmask.value == o_dmem_wmask
    assert dut.i_dmem_rdata.value == i_dmem_rdata
    assert dut.o_valid.value == o_valid
    assert dut.o_pc.value == o_pc
    assert dut.o_fu_data.value == o_fu_data
    assert dut.o_load_data.value == o_load_data
    assert dut.o_is_fence.value == o_is_fence
    assert dut.o_is_ecall.value == o_is_ecall
    assert dut.o_is_ebreak.value == o_is_ebreak
    assert dut.o_is_illegal.value == o_is_illegal
    assert dut.o_mem_error.value == o_mem_error
    assert dut.o_wb_sel.value == o_wb_sel
    assert dut.o_rf_wen.value == o_rf_wen
    assert dut.o_rf_dst.value == o_rf_dst


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    addr_width = (DEPTH - 1).bit_length()
    assert WIDTH == len(dut.i_pc)
    assert WIDTH == len(dut.i_fu_data)
    assert WIDTH == len(dut.i_store_data)
    assert addr_width == len(dut.i_rf_dst)
    assert WIDTH == len(dut.o_dmem_addr)
    assert WIDTH == len(dut.o_dmem_wdata)
    assert BYTES == len(dut.o_dmem_wmask)
    assert WIDTH == len(dut.i_dmem_rdata)
    assert WIDTH == len(dut.o_pc)
    assert WIDTH == len(dut.o_fu_data)
    assert WIDTH == len(dut.o_load_data)
    assert addr_width == len(dut.o_rf_dst)


@cocotb.test()
async def reset_clears_outputs(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = 1
    dut.i_fu_data.value = 2
    dut.i_is_fence.value = 1
    dut.i_is_ecall.value = 1
    dut.i_is_ebreak.value = 1
    dut.i_is_illegal.value = 1
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 1
    await FallingEdge(dut.clk)
    dut.rst.value = 0
    await FallingEdge(dut.clk)
    await _check(
        dut,
        rst=0,
        i_valid=1,
        i_pc=1,
        i_fu_data=2,
        i_is_fence=1,
        i_is_ecall=1,
        i_is_ebreak=1,
        i_is_illegal=1,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=1,
    )


@cocotb.test()
async def route_fu_result(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = 4
    dut.i_fu_data.value = 7
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 3
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    await _check(
        dut,
        i_pc=4,
        i_fu_data=7,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=3,
        o_ready=0,
        o_valid=1,
        o_pc=4,
        o_fu_data=7,
        o_wb_sel=WbSel.FU,
        o_rf_wen=1,
        o_rf_dst=3,
    )


@cocotb.test()
async def load_same_cycle(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_fu_data.value = 1
    dut.i_funct3.value = MemOp.BYTE
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 5
    dut.i_dmem_ready.value = 1
    dut.i_dmem_rdata.value = 0x0000_8000
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_fu_data=1,
        i_mem_ren=1,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        i_rf_dst=5,
        o_dmem_valid=1,
        i_dmem_ready=1,
        o_dmem_ren=1,
        i_dmem_rdata=0x0000_8000,
    )
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    dut.i_mem_ren.value = 0
    await _check(
        dut,
        i_ready=1,
        i_fu_data=1,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        i_rf_dst=5,
        i_dmem_ready=1,
        i_dmem_rdata=0x0000_8000,
        o_valid=1,
        o_fu_data=1,
        o_load_data=(1 << WIDTH) - 0x80,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
        o_rf_dst=5,
    )


@cocotb.test()
async def store_same_cycle(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_fu_data.value = 2
    dut.i_funct3.value = MemOp.HALF
    dut.i_mem_wen.value = 1
    dut.i_store_data.value = 0x1234
    dut.i_dmem_ready.value = 1
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_fu_data=2,
        i_funct3=MemOp.HALF,
        i_mem_wen=1,
        i_store_data=0x1234,
        o_dmem_valid=1,
        i_dmem_ready=1,
        o_dmem_wen=1,
        o_dmem_wdata=0x1234 << 16,
        o_dmem_wmask=0b11 << 2,
    )
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    dut.i_mem_wen.value = 0
    await _check(
        dut,
        i_ready=1,
        i_fu_data=2,
        i_funct3=MemOp.HALF,
        i_store_data=0x1234,
        i_dmem_ready=1,
        o_valid=1,
        o_fu_data=2,
    )


@cocotb.test()
async def wait_on_data_memory(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 4
    dut.i_funct3.value = MemOp.WORD
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 2
    for _ in range(3):
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            o_ready=0,
            i_fu_data=4,
            i_funct3=MemOp.WORD,
            i_mem_ren=1,
            i_wb_sel=WbSel.MEM,
            i_rf_wen=1,
            i_rf_dst=2,
            o_dmem_valid=1,
            o_dmem_ren=1,
            o_dmem_addr=4 & ~(BYTES - 1),
        )

    dut.i_dmem_ready.value = 1
    rdata = 0x1234_5678 << ((4 & (BYTES - 1)) * 8)
    dut.i_dmem_rdata.value = rdata
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    dut.i_mem_ren.value = 0
    await _check(
        dut,
        i_fu_data=4,
        i_funct3=MemOp.WORD,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        i_rf_dst=2,
        o_ready=0,
        i_dmem_ready=1,
        i_dmem_rdata=rdata,
        o_valid=1,
        o_fu_data=4,
        o_load_data=0x1234_5678,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
        o_rf_dst=2,
    )


@cocotb.test()
async def hold_on_backpressure(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 1
    await FallingEdge(dut.clk)
    dut.i_fu_data.value = 2
    dut.i_mem_ren.value = 1
    dut.i_dmem_ready.value = 1
    for _ in range(3):
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            o_ready=0,
            i_fu_data=2,
            i_mem_ren=1,
            i_dmem_ready=1,
            o_valid=1,
            o_fu_data=1,
        )


@cocotb.test()
async def one_ipc(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    for i in range(N_FUZZ):
        dut.i_pc.value = i * 4
        dut.i_fu_data.value = i
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            i_ready=1,
            i_pc=i * 4,
            i_fu_data=i,
            o_valid=1,
            o_pc=i * 4,
            o_fu_data=i,
        )


@cocotb.test()
async def memory_one_ipc(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_funct3.value = MemOp.WORD
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    dut.i_dmem_ready.value = 1
    for i in range(N_FUZZ):
        addr = (i * 4) & (BYTES - 1)
        data = i | 1
        dut.i_fu_data.value = addr
        dut.i_dmem_rdata.value = data << (addr * 8)
        await FallingEdge(dut.clk)
        await _check(
            dut,
            i_valid=1,
            i_ready=1,
            i_fu_data=addr,
            i_funct3=MemOp.WORD,
            i_mem_ren=1,
            i_wb_sel=WbSel.MEM,
            i_rf_wen=1,
            o_dmem_valid=1,
            i_dmem_ready=1,
            o_dmem_ren=1,
            i_dmem_rdata=data << (addr * 8),
            o_valid=1,
            o_fu_data=addr,
            o_load_data=data,
            o_wb_sel=WbSel.MEM,
            o_rf_wen=1,
        )


@cocotb.test()
async def load_x0_still_requests_memory(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_funct3.value = MemOp.WORD
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    await _check(
        dut,
        i_valid=1,
        o_ready=0,
        i_funct3=MemOp.WORD,
        i_mem_ren=1,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        o_dmem_valid=1,
        o_dmem_ren=1,
    )


@cocotb.test()
async def misaligned_access_reports_error(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 1
    dut.i_funct3.value = MemOp.WORD
    dut.i_mem_ren.value = 1
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    await _check(
        dut,
        i_valid=1,
        i_fu_data=1,
        i_funct3=MemOp.WORD,
        i_mem_ren=1,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
    )
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    dut.i_mem_ren.value = 0
    await _check(
        dut,
        i_fu_data=1,
        i_funct3=MemOp.WORD,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        o_ready=0,
        o_valid=1,
        o_fu_data=1,
        o_mem_error=1,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
    )

    dut.i_valid.value = 1
    dut.i_ready.value = 1
    dut.i_mem_wen.value = 1
    dut.i_store_data.value = 0x1234
    dut.i_wb_sel.value = WbSel.NONE
    dut.i_rf_wen.value = 0
    await _check(
        dut,
        i_valid=1,
        i_ready=1,
        i_fu_data=1,
        i_funct3=MemOp.WORD,
        i_mem_wen=1,
        i_store_data=0x1234,
        o_valid=1,
        o_fu_data=1,
        o_mem_error=1,
        o_wb_sel=WbSel.MEM,
        o_rf_wen=1,
    )
    await FallingEdge(dut.clk)
    dut.i_valid.value = 0
    dut.i_mem_wen.value = 0
    await _check(
        dut,
        i_ready=1,
        i_fu_data=1,
        i_funct3=MemOp.WORD,
        i_store_data=0x1234,
        o_valid=1,
        o_fu_data=1,
        o_mem_error=1,
    )


@cocotb.test()
async def route_status_flags(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_is_fence.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        o_ready=0,
        i_is_fence=1,
        o_valid=1,
        o_is_fence=1,
    )

    dut.i_ready.value = 1
    dut.i_is_fence.value = 0
    dut.i_is_ecall.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, i_is_ecall=1, o_valid=1, o_is_ecall=1)

    dut.i_is_ecall.value = 0
    dut.i_is_ebreak.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, i_is_ebreak=1, o_valid=1, o_is_ebreak=1)

    dut.i_is_ebreak.value = 0
    dut.i_is_illegal.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, i_valid=1, i_ready=1, i_is_illegal=1, o_valid=1, o_is_illegal=1)


@cocotb.test()
async def flush_cancels_waiting_access(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 4
    dut.i_funct3.value = MemOp.WORD
    dut.i_mem_ren.value = 1
    await _check(
        dut,
        i_valid=1,
        o_ready=0,
        i_fu_data=4,
        i_funct3=MemOp.WORD,
        i_mem_ren=1,
        o_dmem_valid=1,
        o_dmem_ren=1,
        o_dmem_addr=4 & ~(BYTES - 1),
    )

    dut.i_flush.value = 1
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_fu_data=4,
        i_funct3=MemOp.WORD,
        i_mem_ren=1,
    )
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_fu_data=4,
        i_funct3=MemOp.WORD,
        i_mem_ren=1,
    )

    dut.i_flush.value = 0
    dut.i_mem_ren.value = 0
    dut.i_fu_data.value = 7
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_valid=1,
        o_ready=0,
        i_fu_data=7,
        i_funct3=MemOp.WORD,
        o_valid=1,
        o_fu_data=7,
    )

    dut.i_flush.value = 1
    await FallingEdge(dut.clk)
    await _check(
        dut,
        i_flush=1,
        i_valid=1,
        i_fu_data=7,
        i_funct3=MemOp.WORD,
        o_fu_data=7,
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
def test_ecore_stage_memory(p):
    run(
        "ecore",
        "stage_memory",
        [
            "~ecore/pkgs/ecore_pkg_cpu.sv",
            "~ecore/ecore_lsu.sv",
            "~ecore/stages/ecore_stage_memory.sv",
        ],
        params=p,
    )
