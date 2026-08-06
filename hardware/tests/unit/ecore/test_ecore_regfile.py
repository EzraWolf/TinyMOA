import os
import cocotb
import pytest
from random import randint
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer

from tests import CHECK_DELAY_NS, CLOCK_PERIOD_NS
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
DEPTH = int(os.environ.get("DEPTH", 32))
R_PORTS = int(os.environ.get("R_PORTS", 2))
W_PORTS = int(os.environ.get("W_PORTS", 1))
XLEN_MASK = (1 << WIDTH) - 1

R_ZERO = (0,) * R_PORTS
W_ZERO = (0,) * W_PORTS


async def setup(dut):
    cocotb.start_soon(Clock(dut.clk, CLOCK_PERIOD_NS, "ns").start())

    # dut.rst.value = 0
    for i in range(W_PORTS):
        dut.i_wen[i].value = 0
        dut.i_waddr[i].value = 0
        dut.i_wdata[i].value = 0

    for i in range(R_PORTS):
        dut.i_raddr[i].value = 0

    await FallingEdge(dut.clk)
    # dut.rst.value = 1

    await _check(dut)


async def _check(
    dut,
    # rst=1,
    i_wen=W_ZERO,
    i_waddr=W_ZERO,
    i_wdata=W_ZERO,
    i_raddr=R_ZERO,
    o_rdata=R_ZERO,
):
    await Timer(CHECK_DELAY_NS, "ns")
    # assert dut.rst.value == rst
    for i in range(W_PORTS):
        assert dut.i_wen[i].value == i_wen[i]
        assert dut.i_waddr[i].value == i_waddr[i]
        assert dut.i_wdata[i].value == i_wdata[i]

    for i in range(R_PORTS):
        assert dut.i_raddr[i].value == i_raddr[i]
        assert dut.o_rdata[i].value == o_rdata[i]


async def _write(dut, addrs, data, wen):
    for i in range(W_PORTS):
        dut.i_wen[i].value = wen[i]
        dut.i_waddr[i].value = addrs[i]
        dut.i_wdata[i].value = data[i]

    await FallingEdge(dut.clk)
    for i in range(W_PORTS):
        dut.i_wen[i].value = 0
        dut.i_waddr[i].value = 0
        dut.i_wdata[i].value = 0


async def _write_one(dut, addr, data, port=0, wen=1):
    addrs = [0] * W_PORTS
    values = [0] * W_PORTS
    enables = [0] * W_PORTS
    addrs[port] = addr
    values[port] = data
    enables[port] = wen
    await _write(dut, addrs, values, enables)


async def _read(dut, addrs, data):
    for i in range(R_PORTS):
        dut.i_raddr[i].value = addrs[i]
    await _check(dut, i_raddr=addrs, o_rdata=data)


@cocotb.test()
async def proper_io_widths(dut):
    await setup(dut)

    addr_width = (DEPTH - 1).bit_length()
    for i in range(W_PORTS):
        assert len(dut.i_waddr[i]) == addr_width
        assert len(dut.i_wdata[i]) == WIDTH

    for i in range(R_PORTS):
        assert len(dut.i_raddr[i]) == addr_width
        assert len(dut.o_rdata[i]) == WIDTH


@cocotb.test()
async def x0_hardwired(dut):
    await setup(dut)

    for port in range(W_PORTS):
        await _write_one(dut, 0, randint(1, XLEN_MASK), port)
    await _read(dut, list(R_ZERO), list(R_ZERO))


@cocotb.test()
async def write_read_all(dut):
    await setup(dut)

    data = [randint(0, XLEN_MASK) for _ in range(DEPTH)]
    for addr in range(DEPTH):
        await _write_one(dut, addr, data[addr], addr % W_PORTS)

    data[0] = 0
    for addr in range(DEPTH):
        await _read(dut, [addr] * R_PORTS, [data[addr]] * R_PORTS)


@cocotb.test()
async def read_ports(dut):
    await setup(dut)

    addrs = [(i % (DEPTH - 1)) + 1 for i in range(R_PORTS)]
    data = [randint(0, XLEN_MASK) for _ in range(R_PORTS)]
    for i in range(R_PORTS):
        await _write_one(dut, addrs[i], data[i], i % W_PORTS)
    await _read(dut, addrs, data)


@cocotb.test()
async def write_ports(dut):
    await setup(dut)

    addrs = [i + 1 for i in range(W_PORTS)]
    data = [randint(0, XLEN_MASK) for _ in range(W_PORTS)]
    await _write(dut, addrs, data, [1] * W_PORTS)

    for i in range(W_PORTS):
        await _read(dut, [addrs[i]] * R_PORTS, [data[i]] * R_PORTS)


@cocotb.test()
async def write_disabled(dut):
    await setup(dut)

    for port in range(W_PORTS):
        addr = port + 1
        data = randint(0, XLEN_MASK)
        await _write_one(dut, addr, data, port)
        await _write_one(dut, addr, randint(0, XLEN_MASK), port, wen=0)
        await _read(dut, [addr] * R_PORTS, [data] * R_PORTS)


@cocotb.test()
async def back_to_back_writes(dut):
    await setup(dut)

    data1 = randint(0, XLEN_MASK)
    data2 = randint(0, XLEN_MASK)
    await _write_one(dut, 1, data1)
    await _write_one(dut, 2, data2)
    await _read(dut, [1] * R_PORTS, [data1] * R_PORTS)
    await _read(dut, [2] * R_PORTS, [data2] * R_PORTS)


"""
@cocotb.test()
async def reset_clears(dut):
    await setup(dut)

    # include writing to x0
    for addr in range(DEPTH):
        await _write_one(dut, addr, randint(1, XLEN_MASK), addr % W_PORTS)

    dut.rst.value = 0
    await FallingEdge(dut.clk)
    dut.rst.value = 1

    for addr in range(DEPTH):
        await _read(dut, [addr] * R_PORTS, [0] * R_PORTS)
"""


@pytest.mark.parametrize(
    "p",
    [
        pytest.param(
            {"WIDTH": 32, "DEPTH": 16, "R_PORTS": 2, "W_PORTS": 1},
            id="width32_depth16_r2_w1",
        ),
        pytest.param(
            {"WIDTH": 32, "DEPTH": 16, "R_PORTS": 3, "W_PORTS": 2},
            id="width32_depth16_r3_w2",
        ),
        pytest.param(
            {"WIDTH": 32, "DEPTH": 32, "R_PORTS": 2, "W_PORTS": 1},
            id="width32_depth32_r2_w1",
        ),
        pytest.param(
            {"WIDTH": 32, "DEPTH": 32, "R_PORTS": 3, "W_PORTS": 2},
            id="width32_depth32_r3_w2",
        ),
        pytest.param(
            {"WIDTH": 64, "DEPTH": 16, "R_PORTS": 2, "W_PORTS": 1},
            id="width64_depth16_r2_w1",
        ),
        pytest.param(
            {"WIDTH": 64, "DEPTH": 16, "R_PORTS": 3, "W_PORTS": 2},
            id="width64_depth16_r3_w2",
        ),
        pytest.param(
            {"WIDTH": 64, "DEPTH": 32, "R_PORTS": 2, "W_PORTS": 1},
            id="width64_depth32_r2_w1",
        ),
        pytest.param(
            {"WIDTH": 64, "DEPTH": 32, "R_PORTS": 3, "W_PORTS": 2},
            id="width64_depth32_r3_w2",
        ),
    ],
)
def test_ecore_regfile(p):
    run("ecore", "regfile", ["~ecore/ecore_regfile.sv"], params=p)
