import cocotb
import random
from cocotb.triggers import Timer


async def _alu(dut, i_op, i_a, i_b):
    dut.i_op.value = i_op
    dut.i_a.value = i_a
    dut.i_b.value = i_b
    await Timer(1, "ns")
    return int(dut.o_res.value)


@cocotb.test()
async def add_basic(dut):
    max_size = 0xFFFF_FFFF_FFFF_FFFF
    for _ in range(20):
        a = random.randint(0, max_size)
        b = random.randint(0, max_size)
        expected = (a + b) & max_size
        actual = await _alu(dut, 0b0000, a, b) & max_size
        assert expected == actual


@cocotb.test()
async def sub_basic(dut):
    max_size = 0xFFFF_FFFF_FFFF_FFFF
    for _ in range(20):
        a = random.randint(0, max_size)
        b = random.randint(0, max_size)
        expected = (a - b) & max_size
        actual = await _alu(dut, 0b0010, a, b)
        assert expected == actual
