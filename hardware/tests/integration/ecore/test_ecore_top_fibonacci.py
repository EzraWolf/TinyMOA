import os

import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.common import encode_rv32i as rv32i
from tests.runner import run

from tinymoa_cpu.cpu import Core
from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    imem_from_words,
)


RESULT_ADDR = FIB_RESULT_ADDR
RESULT = FIB_RESULT
CYCLE_TIMEOUT = 500

PROGRAM = list(FIBONACCI)


def _load_program(program):
    return {i * 4: instr for i, instr in enumerate(program)}


def _sandbox_fib(width: int, depth: int):
    return Core(width=width, depth=depth, imem=imem_from_words(PROGRAM)).run(
        halt_pc=FIB_HALT_PC
    )


async def setup(dut, program):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    instr_mem = _load_program(program)
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

        if dut.o_dmem_valid.value:
            addr = int(dut.o_dmem_addr.value)
            if dut.o_dmem_wen.value:
                data = int(dut.o_dmem_wdata.value)
                mask = int(dut.o_dmem_wmask.value)
                word = data_mem.get(addr, 0)
                for i in range(4):
                    if mask & (1 << i):
                        word &= ~(0xFF << (i * 8))
                        word |= data & (0xFF << (i * 8))
                data_mem[addr] = word

            if dut.o_dmem_ren.value:
                dut.i_dmem_rdata.value = data_mem.get(addr, 0)

        pc = int(dut.o_imem_addr.value)
        dut.i_imem_rdata.value = instr_mem.get(pc, rv32i.encode_jal(0, 0))

        await Timer(CHECK_DELAY_NS, "ns")
        if dut.o_valid.value and dut.o_pc.value == halt_pc:
            return cycle + 1

    raise AssertionError(f"timeout after {CYCLE_TIMEOUT} cycles")


@cocotb.test()
async def fibonacci(dut):
    instr_mem, data_mem = await setup(dut, PROGRAM)
    cycles = await run_until_halt(dut, instr_mem, data_mem, halt_pc=FIB_HALT_PC)
    assert data_mem.get(RESULT_ADDR, 0) == RESULT

    # Live lockstep vs sandbox (expected cycles exported by pytest wrapper)
    expect = int(os.environ["SANDBOX_FIB_CYCLES"])
    assert cycles == expect, f"RTL cycles {cycles} != sandbox {expect}"
    assert data_mem.get(RESULT_ADDR, 0) == int(os.environ["SANDBOX_FIB_RESULT"])


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
    ref = _sandbox_fib(width=p["WIDTH"], depth=p["DEPTH"])
    assert ref.dmem.get(RESULT_ADDR, 0) == RESULT
    os.environ["SANDBOX_FIB_CYCLES"] = str(ref.cycles)
    os.environ["SANDBOX_FIB_RESULT"] = str(ref.dmem[RESULT_ADDR])

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
