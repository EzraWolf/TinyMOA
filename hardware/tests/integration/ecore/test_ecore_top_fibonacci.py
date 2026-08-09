"""Live ecore_top fibonacci: sandbox cycle count + dmem vs Verilator."""

import os

import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.common.ideal_mem_tb import drive_imem, load_imem, service_dmem
from tests.runner import run

from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    run_fibonacci,
    xlen_addr,
)


RESULT = FIB_RESULT
CYCLE_TIMEOUT = 500

PROGRAM = list(FIBONACCI)

WIDTH = int(os.environ.get("WIDTH", "32"))
DEPTH = int(os.environ.get("DEPTH", "32"))
RESULT_ADDR = xlen_addr(FIB_RESULT_ADDR, WIDTH)


async def setup(dut, program):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    instr_mem = load_imem(program)
    data_mem = {}
    dut.rst.value = 0
    dut.i_imem_ready.value = 1
    dut.i_imem_rdata.value = instr_mem[0]
    dut.i_dmem_ready.value = 1
    dut.i_dmem_rdata.value = 0

    await FallingEdge(dut.clk)
    dut.rst.value = 1
    return instr_mem, data_mem


async def run_until_halt(dut, instr_mem, data_mem, halt_pc):
    for cycle in range(CYCLE_TIMEOUT):
        await FallingEdge(dut.clk)
        service_dmem(dut, data_mem, width=WIDTH)
        drive_imem(dut, instr_mem)
        await Timer(CHECK_DELAY_NS, "ns")
        if dut.o_valid.value and int(dut.o_pc.value) == halt_pc:
            return cycle + 1
    raise AssertionError(f"timeout after {CYCLE_TIMEOUT} cycles")


@cocotb.test()
async def fibonacci(dut):
    assert len(dut.o_pc) == WIDTH, f"DUT o_pc width {len(dut.o_pc)} != WIDTH={WIDTH}"

    ref = run_fibonacci(width=WIDTH, depth=DEPTH)

    instr_mem, data_mem = await setup(dut, PROGRAM)
    cycles = await run_until_halt(dut, instr_mem, data_mem, halt_pc=FIB_HALT_PC)

    assert data_mem.get(RESULT_ADDR, 0) == RESULT
    assert data_mem.get(RESULT_ADDR, 0) == ref.dmem.get(RESULT_ADDR, 0)
    assert cycles == ref.cycles, f"RTL cycles {cycles} != sandbox {ref.cycles}"


@pytest.mark.parametrize(
    "p",
    [
        pytest.param({"WIDTH": 32, "DEPTH": 32}, id="rv32i"),
        pytest.param({"WIDTH": 32, "DEPTH": 16}, id="rv32e"),
        pytest.param({"WIDTH": 64, "DEPTH": 32}, id="rv64i"),
        pytest.param({"WIDTH": 64, "DEPTH": 16}, id="rv64e"),
    ],
)
def test_ecore_top_fibonacci(p):
    result_addr = xlen_addr(FIB_RESULT_ADDR, p["WIDTH"])
    ref = run_fibonacci(width=p["WIDTH"], depth=p["DEPTH"])
    assert ref.dmem.get(result_addr, 0) == RESULT

    run(
        "ecore",
        "top",
        [
            "~ecore/pkgs/ecore_pkg_cfg.sv",
            "~ecore/pkgs/ecore_pkg_alu.sv",
            "~ecore/ecore_alu.sv",
            "~ecore/ecore_bru.sv",
            "~ecore/ecore_decoder.sv",
            "~ecore/ecore_regfile.sv",
            "~ecore/ecore_lsu.sv",
            "~ecore/stages/ecore_stage_fetch.sv",
            "~ecore/stages/ecore_stage_decode.sv",
            "~ecore/stages/ecore_stage_execute.sv",
            "~ecore/stages/ecore_stage_memory.sv",
            "~ecore/stages/ecore_stage_writeback.sv",
            "~ecore/ecore_top.sv",
        ],
        test_name="fibonacci",
        params=p,
        kind="integration",
    )
