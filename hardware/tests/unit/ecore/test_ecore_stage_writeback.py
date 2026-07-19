import os
import cocotb
import pytest
from cocotb.triggers import Timer

from tests import CHECK_DELAY_NS, N_FUZZ
from tests.common.cpu_types import WbSel
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
DEPTH = int(os.environ.get("DEPTH", 32))
XLEN_MASK = (1 << WIDTH) - 1


async def setup(dut):
    dut.i_valid.value = 0
    dut.i_pc.value = 0
    dut.i_fu_data.value = 0
    dut.i_load_data.value = 0
    dut.i_is_fence.value = 0
    dut.i_is_ecall.value = 0
    dut.i_is_ebreak.value = 0
    dut.i_is_illegal.value = 0
    dut.i_mem_error.value = 0
    dut.i_wb_sel.value = WbSel.NONE
    dut.i_rf_wen.value = 0
    dut.i_rf_dst.value = 0
    await _check(dut)


async def _check(
    dut,
    i_valid=0,
    o_ready=1,
    i_pc=0,
    i_fu_data=0,
    i_load_data=0,
    i_is_fence=0,
    i_is_ecall=0,
    i_is_ebreak=0,
    i_is_illegal=0,
    i_mem_error=0,
    i_wb_sel=WbSel.NONE,
    i_rf_wen=0,
    i_rf_dst=0,
    o_rf_wen=0,
    o_rf_dst=0,
    o_rf_data=0,
    o_valid=0,
    o_pc=0,
    o_is_fence=0,
    o_is_ecall=0,
    o_is_ebreak=0,
    o_is_illegal=0,
    o_mem_error=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.i_valid.value == i_valid
    assert dut.o_ready.value == o_ready
    assert dut.i_pc.value == i_pc
    assert dut.i_fu_data.value == i_fu_data
    assert dut.i_load_data.value == i_load_data
    assert dut.i_is_fence.value == i_is_fence
    assert dut.i_is_ecall.value == i_is_ecall
    assert dut.i_is_ebreak.value == i_is_ebreak
    assert dut.i_is_illegal.value == i_is_illegal
    assert dut.i_mem_error.value == i_mem_error
    assert dut.i_wb_sel.value == i_wb_sel
    assert dut.i_rf_wen.value == i_rf_wen
    assert dut.i_rf_dst.value == i_rf_dst
    assert dut.o_rf_wen.value == o_rf_wen
    assert dut.o_rf_dst.value == o_rf_dst
    assert dut.o_rf_data.value == o_rf_data
    assert dut.o_valid.value == o_valid
    assert dut.o_pc.value == o_pc
    assert dut.o_is_fence.value == o_is_fence
    assert dut.o_is_ecall.value == o_is_ecall
    assert dut.o_is_ebreak.value == o_is_ebreak
    assert dut.o_is_illegal.value == o_is_illegal
    assert dut.o_mem_error.value == o_mem_error


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    addr_width = (DEPTH - 1).bit_length()
    assert WIDTH == len(dut.i_pc)
    assert WIDTH == len(dut.i_fu_data)
    assert WIDTH == len(dut.i_load_data)
    assert addr_width == len(dut.i_rf_dst)
    assert addr_width == len(dut.o_rf_dst)
    assert WIDTH == len(dut.o_rf_data)
    assert WIDTH == len(dut.o_pc)


@cocotb.test()
async def write_fu_data(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = 4
    dut.i_fu_data.value = 0x1234
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 3
    await _check(
        dut,
        i_valid=1,
        i_pc=4,
        i_fu_data=0x1234,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=3,
        o_rf_wen=1,
        o_rf_dst=3,
        o_rf_data=0x1234,
        o_valid=1,
        o_pc=4,
    )


@cocotb.test()
async def write_load_data(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_load_data.value = 0x5678
    dut.i_wb_sel.value = WbSel.MEM
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 4
    await _check(
        dut,
        i_valid=1,
        i_load_data=0x5678,
        i_wb_sel=WbSel.MEM,
        i_rf_wen=1,
        i_rf_dst=4,
        o_rf_wen=1,
        o_rf_dst=4,
        o_rf_data=0x5678,
        o_valid=1,
    )


@cocotb.test()
async def write_pc_plus_4(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_pc.value = XLEN_MASK - 3
    dut.i_wb_sel.value = WbSel.PC
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 1
    await _check(
        dut,
        i_valid=1,
        i_pc=XLEN_MASK - 3,
        i_wb_sel=WbSel.PC,
        i_rf_wen=1,
        i_rf_dst=1,
        o_rf_wen=1,
        o_rf_dst=1,
        o_rf_data=0,
        o_valid=1,
        o_pc=XLEN_MASK - 3,
    )


@cocotb.test()
async def disable_write(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 7
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 2
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_rf_wen=1,
        i_rf_dst=2,
        o_valid=1,
    )

    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 0
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_wb_sel=WbSel.FU,
        i_rf_dst=2,
        o_valid=1,
    )


@cocotb.test()
async def invalid_does_not_write(dut):
    await setup(dut)

    dut.i_fu_data.value = 7
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 2
    await _check(
        dut,
        i_fu_data=7,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=2,
    )


@cocotb.test()
async def x0_write_preserved(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_fu_data.value = 7
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        o_rf_wen=1,
        o_rf_data=7,
        o_valid=1,
    )


@cocotb.test()
async def route_status_flags(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_is_fence.value = 1
    await _check(dut, i_valid=1, i_is_fence=1, o_valid=1, o_is_fence=1)

    dut.i_is_fence.value = 0
    dut.i_is_ecall.value = 1
    dut.i_fu_data.value = 7
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    dut.i_rf_dst.value = 2
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_is_ecall=1,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=2,
        o_valid=1,
        o_is_ecall=1,
    )

    dut.i_is_ecall.value = 0
    dut.i_is_ebreak.value = 1
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_is_ebreak=1,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=2,
        o_valid=1,
        o_is_ebreak=1,
    )

    dut.i_is_ebreak.value = 0
    dut.i_is_illegal.value = 1
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_is_illegal=1,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=2,
        o_valid=1,
        o_is_illegal=1,
    )

    dut.i_is_illegal.value = 0
    dut.i_mem_error.value = 1
    await _check(
        dut,
        i_valid=1,
        i_fu_data=7,
        i_mem_error=1,
        i_wb_sel=WbSel.FU,
        i_rf_wen=1,
        i_rf_dst=2,
        o_valid=1,
        o_mem_error=1,
    )


@cocotb.test()
async def one_ipc(dut):
    await setup(dut)

    dut.i_valid.value = 1
    dut.i_wb_sel.value = WbSel.FU
    dut.i_rf_wen.value = 1
    for i in range(N_FUZZ):
        dut.i_pc.value = i * 4
        dut.i_fu_data.value = i
        dut.i_rf_dst.value = i % DEPTH
        await _check(
            dut,
            i_valid=1,
            i_pc=i * 4,
            i_fu_data=i,
            i_wb_sel=WbSel.FU,
            i_rf_wen=1,
            i_rf_dst=i % DEPTH,
            o_rf_wen=1,
            o_rf_dst=i % DEPTH,
            o_rf_data=i,
            o_valid=1,
            o_pc=i * 4,
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
def test_ecore_stage_writeback(p):
    run(
        "ecore",
        "stage_writeback",
        [
            "~ecore/pkgs/ecore_pkg_cpu.sv",
            "~ecore/stages/ecore_stage_writeback.sv",
        ],
        params=p,
    )
