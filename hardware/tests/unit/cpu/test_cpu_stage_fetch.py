import os
import cocotb
import pytest
from random import randint
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS, N_FUZZ
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 64))


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    dut.rst.value = 0
    dut.i_valid.value = 0
    dut.i_pc.value = 0
    dut.i_imem_ready.value = 0
    dut.i_imem_rdata.value = 0
    dut.i_ready.value = 0

    await FallingEdge(dut.clk)
    dut.rst.value = 1

    await _check(dut)


async def _check(
    dut, o_valid=0, o_imem_valid=1, o_imem_addr=0, o_pc=None, o_instr=None
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.o_valid.value == o_valid
    assert dut.o_imem_valid.value == o_imem_valid
    assert dut.o_imem_addr.value == o_imem_addr
    if o_pc is not None:
        assert dut.o_pc.value == o_pc
    if o_instr is not None:
        assert dut.o_instr.value == o_instr


@cocotb.test()
async def pc_resets_zero(dut):
    await setup(dut)
    dut.i_ready.value = 1
    dut.i_imem_ready.value = 1
    for _ in range(N_FUZZ):
        dut.i_imem_rdata.value = randint(1, 0xFFFF_FFFF)
        await FallingEdge(dut.clk)

    assert dut.o_valid.value == 1
    assert dut.o_pc.value != 0

    dut.rst.value = 0
    await _check(dut, o_pc=0, o_instr=0)


@cocotb.test()
async def fetch_one_ipc(dut):
    await setup(dut)

    dut.i_ready.value = 1
    dut.i_imem_ready.value = 1
    for i in range(N_FUZZ):
        instr = randint(0, 0xFFFF_FFFF)
        ext_pc = i * 4
        dut.i_imem_rdata.value = instr
        await FallingEdge(dut.clk)

        await _check(
            dut,
            o_valid=1,
            o_imem_addr=ext_pc + 4,
            o_pc=ext_pc,
            o_instr=instr,
        )


@cocotb.test()
async def verify_handshake(dut):
    await setup(dut)

    pc_next = 0
    expect_valid = False
    expect_pc = 0
    expect_instr = 0
    for _ in range(N_FUZZ):
        ready = randint(0, 1)
        imem_ready = randint(0, 1)
        instr = randint(0, 0xFFFF_FFFF)

        dut.i_ready.value = ready
        dut.i_imem_ready.value = imem_ready
        dut.i_imem_rdata.value = instr

        if expect_valid and ready:
            expect_valid = False
        if (not expect_valid or ready) and imem_ready:
            expect_valid = True
            expect_pc = pc_next
            expect_instr = instr
            pc_next += 4

        await FallingEdge(dut.clk)
        await _check(
            dut,
            o_valid=expect_valid,
            o_imem_valid=not expect_valid or ready,
            o_imem_addr=pc_next,
            o_pc=expect_pc if expect_valid else None,
            o_instr=expect_instr if expect_valid else None,
        )


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    assert WIDTH == len(dut.i_pc)
    assert WIDTH == len(dut.o_imem_addr)
    assert WIDTH == len(dut.o_pc)
    assert 32 == len(dut.i_imem_rdata)
    assert 32 == len(dut.o_instr)


@cocotb.test()
async def waits_for_instr_mem(dut):
    await setup(dut)

    dut.i_ready.value = 1
    dut.i_imem_ready.value = 0
    for _ in range(100):
        await FallingEdge(dut.clk)
        await _check(dut)

    dut.i_imem_rdata.value = 0x12345678
    dut.i_imem_ready.value = 1
    await FallingEdge(dut.clk)

    await _check(dut, o_valid=1, o_imem_addr=4, o_pc=0, o_instr=0x12345678)


@cocotb.test()
async def hold_on_backpressure(dut):
    await setup(dut)

    dut.i_ready.value = 1
    dut.i_imem_ready.value = 1
    dut.i_imem_rdata.value = 0x12345678
    await FallingEdge(dut.clk)
    await _check(dut, o_valid=1, o_imem_addr=4, o_pc=0, o_instr=0x12345678)

    dut.i_ready.value = 0
    dut.i_imem_rdata.value = 0xDEADBEEF
    for _ in range(100):
        await FallingEdge(dut.clk)
        await _check(
            dut,
            o_valid=1,
            o_imem_valid=0,
            o_imem_addr=4,
            o_pc=0,
            o_instr=0x12345678,
        )

    dut.i_ready.value = 1
    await FallingEdge(dut.clk)
    await _check(dut, o_valid=1, o_imem_addr=8, o_pc=4, o_instr=0xDEADBEEF)


@cocotb.test()
async def redirect_flush(dut):
    await setup(dut)

    dut.i_ready.value = 1
    dut.i_imem_ready.value = 1
    dut.i_imem_rdata.value = 0x12345678
    await FallingEdge(dut.clk)
    await _check(dut, o_valid=1, o_imem_addr=4, o_pc=0, o_instr=0x12345678)

    dut.i_ready.value = 0
    dut.i_valid.value = 1
    dut.i_pc.value = 0x100
    dut.i_imem_rdata.value = 0xDEADBEEF
    await _check(
        dut,
        o_valid=1,
        o_imem_addr=0x100,
        o_pc=0,
        o_instr=0x12345678,
    )
    await FallingEdge(dut.clk)

    await _check(
        dut,
        o_valid=1,
        o_imem_addr=0x100,
        o_pc=0x100,
        o_instr=0xDEADBEEF,
    )


@pytest.mark.parametrize("p", [{"WIDTH": 32}, {"WIDTH": 64}])
def test_cpu_stage_fetch(p):
    run("cpu", "stage_fetch", ["~cpu/stages/cpu_stage_fetch.sv"], params=p)
