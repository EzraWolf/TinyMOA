import cocotb
import random
from cocotb.triggers import Timer


async def _alu(dut, op, a, b):
    dut.i_op.value = op
    dut.i_a.value = a
    dut.i_b.value = b
    await Timer(1, "ns")
    return int(dut.o_res.value)


@cocotb.test()
async def add_basic(dut):
    max_size = 0xFFFF_FFFF_FFFF_FFFF
    for _ in range(20):
        a = random.randint(0, max_size)
        b = random.randint(0, max_size)
        r = await _alu(dut, 0b0000, a, b)
        assert r == (a + b) & max_size, f"{hex(a)} + {hex(b)}: got {hex(r)}"
