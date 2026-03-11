"""Integration tests for core_generic: full RV32EC CPU pipeline."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

import rv32i_encode as rv32i

NOP = rv32i.encode_addi(0, 0, 0)

S_FETCH = 0
S_DECODE = 1
S_EXECUTE = 2
S_WRITEBACK = 3
S_MEM = 4


async def setup(dut, program=None):
    clock = Clock(dut.clk, 8, unit="ns")
    cocotb.start_soon(clock.start())
    dut.nrst.value = 0
    dut.reg_probe_sel.value = 0

    await ClockCycles(dut.clk, 1)

    if program:
        for i, instr in enumerate(program):
            dut.mem[i].value = instr
        for i in range(len(program), 256):
            dut.mem[i].value = NOP
        await ClockCycles(dut.clk, 1)
        readback = int(dut.mem[0].value)
        dut._log.info(
            f"mem[0] readback: {readback:#010x}, expected: {program[0]:#010x}"
        )

    dut.nrst.value = 1


async def wait_state(dut, target_state, timeout=200):
    for _ in range(timeout):
        await RisingEdge(dut.clk)
        if int(dut.dbg_state.value) == target_state:
            return
    raise TimeoutError(f"Timed out waiting for state {target_state}")


async def run_instructions(dut, count):
    for _ in range(count):
        await wait_state(dut, S_WRITEBACK)
        await wait_state(dut, S_FETCH)


async def read_reg(dut, reg_num):
    dut.reg_probe_sel.value = reg_num
    await ClockCycles(dut.clk, 8)
    return int(dut.reg_probe_val.value)


@cocotb.test()
async def test_state_sequence(dut):
    """
    Core should cycle through when running a NOP instruction.
    1. FETCH
    2. DECODE
    3. EXECUTE(x8)
    4. WRITEBACK
    5. FETCH
    """
    await setup(dut)

    states_seen = []
    for _ in range(50):
        await RisingEdge(dut.clk)
        states_seen.append(int(dut.dbg_state.value))
        if (
            len(states_seen) > 5
            and states_seen[-1] == S_FETCH
            and S_WRITEBACK in states_seen
        ):
            break

    assert S_FETCH in states_seen, "Never reached FETCH"
    assert S_DECODE in states_seen, "Never reached DECODE"
    assert S_EXECUTE in states_seen, "Never reached EXECUTE"
    assert S_WRITEBACK in states_seen, "Never reached WRITEBACK"


@cocotb.test()
async def test_nop_pc_increments(dut):
    """PC increments by 4 for each 32-bit NOP."""
    await setup(dut, [NOP] * 8)

    pc_values = []
    for i in range(4):
        await wait_state(dut, S_WRITEBACK)
        await wait_state(dut, S_FETCH)
        pc_values.append(int(dut.dbg_pc.value))

    for i, pc in enumerate(pc_values):
        expected = (i + 1) * 4
        assert pc == expected, (
            f"After NOP {i + 1}: PC={hex(pc)}, expected {hex(expected)}"
        )


@cocotb.test()
async def test_addi_chain(dut):
    """ADDI chain test

    Program (addi_chain.hex):
        x5 = 0 + 1 + 1 + 1 + 1 + 1 = 5
        x6 = x5 + 0 = 5 (copy)
    """

    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 1),
            rv32i.encode_addi(5, 5, 1),
            rv32i.encode_addi(5, 5, 1),
            rv32i.encode_addi(5, 5, 1),
            rv32i.encode_addi(5, 5, 1),
            rv32i.encode_addi(6, 5, 0),
        ],
    )
    await run_instructions(dut, 6)

    assert await read_reg(dut, 5) == 5, f"x5: got {await read_reg(dut, 5)}, expected 5"
    assert await read_reg(dut, 6) == 5, f"x6: got {await read_reg(dut, 6)}, expected 5"


@cocotb.test()
async def test_alu_basic(dut):
    """ALU instruction tests

    Program (alu_basic.hex):
        x5 = 10, x6 = 3
        x7 = ADD(x5,x6) = 13
        x8 = SUB(x5,x6) = 7
        x9 = AND(x5,x6) = 2
        x10 = OR(x5,x6) = 11
        x11 = XOR(x5,x6) = 9
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 10),
            rv32i.encode_addi(6, 0, 3),
            rv32i.encode_add(7, 5, 6),
            rv32i.encode_sub(8, 5, 6),
            rv32i.encode_and(9, 5, 6),
            rv32i.encode_or(10, 5, 6),
            rv32i.encode_xor(11, 5, 6),
        ],
    )
    await run_instructions(dut, 7)

    expected = {5: 10, 6: 3, 7: 13, 8: 7, 9: 2, 10: 11, 11: 9}
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        assert got == val, (
            f"x{reg}: got {got} ({hex(got)}), expected {val} ({hex(val)})"
        )
