import os
import cocotb
import pytest
from random import randint
from cocotb.triggers import Timer

from tests import CHECK_DELAY_NS, N_FUZZ
from tests.common.cpu_types import MemOp
from tests.runner import run


WIDTH = int(os.environ.get("WIDTH", 32))
BYTES = WIDTH // 8
XLEN_MASK = (1 << WIDTH) - 1


async def setup(dut):
    dut.i_addr.value = 0
    dut.i_store_data.value = 0
    dut.i_op.value = MemOp.BYTE
    dut.i_is_load.value = 0
    dut.i_is_store.value = 0
    dut.i_rdata.value = 0
    await _check(dut)


async def _check(
    dut,
    i_addr=0,
    i_store_data=0,
    i_op=0,
    i_is_load=0,
    i_is_store=0,
    i_rdata=0,
    o_wdata=0,
    o_wmask=0,
    o_load_data=0,
    o_error=0,
):
    await Timer(CHECK_DELAY_NS, "ns")
    assert dut.i_addr.value == i_addr
    assert dut.i_store_data.value == i_store_data
    assert dut.i_op.value == i_op
    assert dut.i_is_load.value == i_is_load
    assert dut.i_is_store.value == i_is_store
    assert dut.i_rdata.value == i_rdata
    assert dut.o_wdata.value == o_wdata
    assert dut.o_wmask.value == o_wmask
    assert dut.o_load_data.value == o_load_data
    assert dut.o_error.value == o_error


def _sext(data, bits):
    sign = 1 << (bits - 1)
    return ((data ^ sign) - sign) & XLEN_MASK


@cocotb.test()
async def proper_io_widths(dut):
    assert WIDTH == len(dut.i_addr)
    assert WIDTH == len(dut.i_store_data)
    assert 3 == len(dut.i_op)
    assert WIDTH == len(dut.i_rdata)
    assert WIDTH == len(dut.o_wdata)
    assert BYTES == len(dut.o_wmask)
    assert WIDTH == len(dut.o_load_data)


@cocotb.test()
async def lb_offsets_sign_extend(dut):
    await setup(dut)

    for offset in range(BYTES):
        for _ in range(N_FUZZ):
            rdata = randint(0, XLEN_MASK)
            data = (rdata >> (offset * 8)) & 0xFF
            dut.i_addr.value = offset
            dut.i_is_load.value = 1
            dut.i_rdata.value = rdata
            await _check(
                dut,
                i_addr=offset,
                i_is_load=1,
                i_rdata=rdata,
                o_load_data=_sext(data, 8),
            )


@cocotb.test()
async def lbu_offsets_zero_extend(dut):
    await setup(dut)

    dut.i_op.value = MemOp.BYTE_U
    dut.i_is_load.value = 1
    for offset in range(BYTES):
        for _ in range(N_FUZZ):
            rdata = randint(0, XLEN_MASK)
            data = (rdata >> (offset * 8)) & 0xFF
            dut.i_addr.value = offset
            dut.i_rdata.value = rdata
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.BYTE_U,
                i_is_load=1,
                i_rdata=rdata,
                o_load_data=data,
            )


@cocotb.test()
async def lh_offsets_sign_extend(dut):
    await setup(dut)

    dut.i_op.value = MemOp.HALF
    dut.i_is_load.value = 1
    for offset in range(0, BYTES, 2):
        for _ in range(N_FUZZ):
            rdata = randint(0, XLEN_MASK)
            data = (rdata >> (offset * 8)) & 0xFFFF
            dut.i_addr.value = offset
            dut.i_rdata.value = rdata
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.HALF,
                i_is_load=1,
                i_rdata=rdata,
                o_load_data=_sext(data, 16),
            )


@cocotb.test()
async def lhu_offsets_zero_extend(dut):
    await setup(dut)

    dut.i_op.value = MemOp.HALF_U
    dut.i_is_load.value = 1
    for offset in range(0, BYTES, 2):
        for _ in range(N_FUZZ):
            rdata = randint(0, XLEN_MASK)
            data = (rdata >> (offset * 8)) & 0xFFFF
            dut.i_addr.value = offset
            dut.i_rdata.value = rdata
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.HALF_U,
                i_is_load=1,
                i_rdata=rdata,
                o_load_data=data,
            )


@cocotb.test()
async def lw_offsets_sign_extend(dut):
    await setup(dut)

    dut.i_op.value = MemOp.WORD
    dut.i_is_load.value = 1
    for offset in range(0, BYTES, 4):
        for _ in range(N_FUZZ):
            rdata = randint(0, XLEN_MASK)
            data = (rdata >> (offset * 8)) & 0xFFFF_FFFF
            dut.i_addr.value = offset
            dut.i_rdata.value = rdata
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.WORD,
                i_is_load=1,
                i_rdata=rdata,
                o_load_data=_sext(data, 32),
            )


@cocotb.test()
async def sb_offsets_set_mask_data(dut):
    await setup(dut)

    dut.i_is_store.value = 1
    for offset in range(BYTES):
        for _ in range(N_FUZZ):
            data = randint(0, XLEN_MASK)
            dut.i_addr.value = offset
            dut.i_store_data.value = data
            await _check(
                dut,
                i_addr=offset,
                i_store_data=data,
                i_is_store=1,
                o_wdata=(data << (offset * 8)) & XLEN_MASK,
                o_wmask=1 << offset,
            )


@cocotb.test()
async def sh_offsets_set_mask_data(dut):
    await setup(dut)

    dut.i_op.value = MemOp.HALF
    dut.i_is_store.value = 1
    for offset in range(0, BYTES, 2):
        for _ in range(N_FUZZ):
            data = randint(0, XLEN_MASK)
            dut.i_addr.value = offset
            dut.i_store_data.value = data
            await _check(
                dut,
                i_addr=offset,
                i_store_data=data,
                i_op=MemOp.HALF,
                i_is_store=1,
                o_wdata=(data << (offset * 8)) & XLEN_MASK,
                o_wmask=0b0011 << offset,
            )


@cocotb.test()
async def sw_sets_full_mask_data(dut):
    await setup(dut)

    dut.i_op.value = MemOp.WORD
    dut.i_is_store.value = 1
    for offset in range(0, BYTES, 4):
        for _ in range(N_FUZZ):
            data = randint(0, XLEN_MASK)
            dut.i_addr.value = offset
            dut.i_store_data.value = data
            await _check(
                dut,
                i_addr=offset,
                i_store_data=data,
                i_op=MemOp.WORD,
                i_is_store=1,
                o_wdata=(data << (offset * 8)) & XLEN_MASK,
                o_wmask=0b1111 << offset,
            )


@cocotb.test()
async def misaligned_half_reports_error(dut):
    await setup(dut)

    for is_load in (0, 1):
        dut.i_is_load.value = is_load
        dut.i_is_store.value = not is_load
        dut.i_op.value = MemOp.HALF
        for offset in range(1, BYTES, 2):
            dut.i_addr.value = offset
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.HALF,
                i_is_load=is_load,
                i_is_store=not is_load,
                o_error=1,
            )


@cocotb.test()
async def misaligned_word_reports_error(dut):
    await setup(dut)

    for is_load in (0, 1):
        dut.i_is_load.value = is_load
        dut.i_is_store.value = not is_load
        dut.i_op.value = MemOp.WORD
        for offset in range(BYTES):
            if offset % 4 == 0:
                continue
            dut.i_addr.value = offset
            await _check(
                dut,
                i_addr=offset,
                i_op=MemOp.WORD,
                i_is_load=is_load,
                i_is_store=not is_load,
                o_error=1,
            )


@cocotb.test()
async def invalid_op_reports_error(dut):
    await setup(dut)

    dut.i_is_load.value = 1
    for op in (0b011, 0b110, 0b111):
        dut.i_op.value = op
        await _check(dut, i_op=op, i_is_load=1, o_error=1)

    dut.i_is_load.value = 0
    dut.i_is_store.value = 1
    for op in range(0b011, 0b1000):
        dut.i_op.value = op
        await _check(dut, i_op=op, i_is_store=1, o_error=1)


@pytest.mark.parametrize("p", [{"WIDTH": 32}, {"WIDTH": 64}])
def test_cpu_lsu(p):
    run("cpu", "lsu", ["~cpu/cpu_lsu.sv"], params=p)
