import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.common import encode_rv32i as rv32i
from tests.runner import run


RESULT_ADDR = 0x100
RESULT = 55
CYCLE_TIMEOUT = 500

PROGRAM = [
    rv32i.encode_addi(5, 0, 10),  # addi t0, zero, 10
    rv32i.encode_addi(6, 0, 0),  # addi t1, zero, 0
    rv32i.encode_addi(7, 0, 1),  # addi t2, zero, 1
    rv32i.encode_beq(5, 0, 24),  # beq  t0, zero, done
    rv32i.encode_add(8, 6, 7),  # add  s0, t1, t2
    rv32i.encode_addi(6, 7, 0),  # addi t1, t2, 0
    rv32i.encode_addi(7, 8, 0),  # addi t2, s0, 0
    rv32i.encode_addi(5, 5, -1),  # addi t0, t0, -1
    rv32i.encode_jal(0, -20),  # jal  zero, loop
    rv32i.encode_addi(9, 0, 0x100),  # addi s1, zero, 0x100
    rv32i.encode_sw(9, 6, 0),  # sw   t1, 0(s1)
    rv32i.encode_jal(0, 0),  # halt: jal zero, halt
]


def _load_program(program):
    return {i * 4: instr for i, instr in enumerate(program)}


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
    for _ in range(CYCLE_TIMEOUT):
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
            return

    raise AssertionError(f"timeout after {CYCLE_TIMEOUT} cycles")


@cocotb.test()
async def fibonacci(dut):
    instr_mem, data_mem = await setup(dut, PROGRAM)
    await run_until_halt(dut, instr_mem, data_mem, halt_pc=(len(PROGRAM) - 1) * 4)
    assert data_mem.get(RESULT_ADDR, 0) == RESULT


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
