"""Per-cycle Verilator ↔ sandbox lockstep for directed ecore programs."""

from __future__ import annotations

import os

import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.common.ideal_mem_tb import drive_imem, load_imem, service_dmem
from tests.runner import run

from tinymoa_cpu.lockstep import diff_cycle_samples
from tinymoa_cpu.mem import IdealMem, imem_from_words
from tinymoa_cpu.programs import (
    BRANCH_HALT_PC,
    BRANCH_STORM,
    FIBONACCI,
    FIB_HALT_PC,
    LOAD_STORE_PARTIAL,
    LSU_HALT_PC,
    RAW_CHAIN,
    RAW_HALT_PC,
)
from tinymoa_cpu.top import Core, CycleSample


WIDTH = int(os.environ.get("WIDTH", "32"))
DEPTH = int(os.environ.get("DEPTH", "32"))
CYCLE_TIMEOUT = 2000

_PROGRAMS = {
    "fibonacci": (FIBONACCI, FIB_HALT_PC),
    "raw_chain": (RAW_CHAIN, RAW_HALT_PC),
    "branch_storm": (BRANCH_STORM, BRANCH_HALT_PC),
    "load_store_partial": (LOAD_STORE_PARTIAL, LSU_HALT_PC),
}


def _ecore_sources():
    return [
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
    ]


async def _setup(dut, program):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())
    instr_mem = load_imem(program)
    data_mem: dict[int, int] = {}
    dut.rst.value = 0
    dut.i_imem_ready.value = 1
    dut.i_imem_rdata.value = instr_mem[0]
    dut.i_dmem_ready.value = 1
    dut.i_dmem_rdata.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 1
    return instr_mem, data_mem


def _sample_dut(dut, cycle: int) -> CycleSample:
    imem_valid = bool(int(dut.o_imem_valid.value))
    dmem_valid = bool(int(dut.o_dmem_valid.value))
    retire_valid = bool(int(dut.o_valid.value))
    return CycleSample(
        cycle=cycle,
        imem_valid=imem_valid,
        imem_addr=int(dut.o_imem_addr.value) if imem_valid else 0,
        dmem_valid=dmem_valid,
        dmem_ren=bool(int(dut.o_dmem_ren.value)) if dmem_valid else False,
        dmem_wen=bool(int(dut.o_dmem_wen.value)) if dmem_valid else False,
        dmem_addr=int(dut.o_dmem_addr.value) if dmem_valid else 0,
        dmem_wdata=int(dut.o_dmem_wdata.value) if dmem_valid else 0,
        dmem_wmask=int(dut.o_dmem_wmask.value) if dmem_valid else 0,
        retire_valid=retire_valid,
        retire_pc=int(dut.o_pc.value) if retire_valid else 0,
        rf=(),  # port-level lockstep; RF via public_flat later
    )


@cocotb.test()
async def cycle_lockstep(dut):
    assert len(dut.o_pc) == WIDTH
    program_name = os.environ.get("PROGRAM", "fibonacci")
    halt_pc = int(os.environ.get("HALT_PC", str(FIB_HALT_PC)))
    program, expected_halt = _PROGRAMS[program_name]
    assert halt_pc == expected_halt

    ref = Core(
        width=WIDTH,
        depth=DEPTH,
        mem=IdealMem(imem=imem_from_words(program)),
    )
    instr_mem, data_mem = await _setup(dut, program)

    for cycle in range(1, CYCLE_TIMEOUT + 1):
        await FallingEdge(dut.clk)
        service_dmem(dut, data_mem, width=WIDTH)
        drive_imem(dut, instr_mem)
        await Timer(CHECK_DELAY_NS, "ns")

        ref_sample = ref.step()
        dut_sample = _sample_dut(dut, cycle)

        msg = diff_cycle_samples([ref_sample], [dut_sample], check_rf=False)
        if msg:
            raise AssertionError(f"first mismatch at RTL cycle {cycle}: {msg}")

        if dut_sample.retire_valid and dut_sample.retire_pc == halt_pc:
            assert ref_sample.retire_valid and ref_sample.retire_pc == halt_pc
            for addr, val in ref.mem.dmem.items():
                assert data_mem.get(addr, 0) == val, f"dmem[{addr:#x}]"
            return

    raise AssertionError(f"timeout after {CYCLE_TIMEOUT} cycles")


@pytest.mark.parametrize(
    "prog,halt,p",
    [
        pytest.param("fibonacci", FIB_HALT_PC, {"WIDTH": 32, "DEPTH": 32}, id="fib-rv32i"),
        pytest.param("raw_chain", RAW_HALT_PC, {"WIDTH": 32, "DEPTH": 32}, id="raw-rv32i"),
        pytest.param("branch_storm", BRANCH_HALT_PC, {"WIDTH": 32, "DEPTH": 32}, id="br-rv32i"),
        pytest.param(
            "load_store_partial", LSU_HALT_PC, {"WIDTH": 32, "DEPTH": 32}, id="lsu-rv32i"
        ),
        pytest.param("fibonacci", FIB_HALT_PC, {"WIDTH": 32, "DEPTH": 16}, id="fib-rv32e"),
        pytest.param("fibonacci", FIB_HALT_PC, {"WIDTH": 64, "DEPTH": 32}, id="fib-rv64i"),
    ],
)
def test_ecore_cycle_lockstep(prog, halt, p):
    run(
        "ecore",
        "top",
        _ecore_sources(),
        test_name="cycle_lockstep",
        params=p,
        kind="integration",
        extra_env={"PROGRAM": prog, "HALT_PC": halt},
    )
