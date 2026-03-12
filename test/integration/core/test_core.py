"""Integration tests for core_generic: full RV32EC CPU pipeline."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge

import rv32i_encode as rv32i
import rv32c_encode as rv32c

NOP = rv32i.encode_addi(0, 0, 0)

S_FETCH = 0
S_DECODE = 1
S_EXECUTE = 2
S_WRITEBACK = 3
S_MEM = 4
S_LOAD_WB = 5


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
    await ClockCycles(dut.clk, 9)  # 9 clocks guarantees a full 8-cycle aligned window
    return int(dut.reg_probe_val.value)


async def setup_compressed(dut, c_instrs):
    """Pack 16-bit C instructions two-per-word and load them.

    Each pair (lo, hi) is stored as a single 32-bit word: word = (hi << 16) | lo.
    The core uses pc[1] to select the upper or lower half on fetch.
    """
    words = []
    for i in range(0, len(c_instrs), 2):
        lo = c_instrs[i] & 0xFFFF
        hi = (
            (c_instrs[i + 1] & 0xFFFF)
            if i + 1 < len(c_instrs)
            else rv32c.encode_c_nop()
        )
        words.append((hi << 16) | lo)
    await setup(dut, words)


@cocotb.test()
async def test_read_reg_sanity(dut):
    """Does read_reg return the right value after a single ADDI?"""
    await setup(dut, [rv32i.encode_addi(6, 0, 42)])
    await run_instructions(dut, 1)
    val = await read_reg(dut, 6)
    dut._log.info(f"read_reg(6) after ADDI x6,x0,42 = {val}")
    assert val == 42, f"read_reg broken: got {val}, expected 42"


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

    x5 = await read_reg(dut, 5)
    x6 = await read_reg(dut, 6)
    assert x5 == 5, f"x5: got {x5}, expected 5"
    assert x6 == 5, f"x6: got {x6}, expected 5"


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


@cocotb.test()
async def test_fibonacci(dut):
    """
    Compute fib(12) = 144 using a branch loop

    x5 = fib(n-2)
    x6 = fib(n-1)
    x7 = temp
    x8 = loop counter
    x9 = limit (12)

    fib(0)=0, fib(1)=1, fib(2)=1, ... fib(12)=144

    Program assembly:
    (0x00)  ADDI x5, x0, 0       # a = 0
    (0x04)  ADDI x6, x0, 1       # b = 1
    (0x08)  ADDI x8, x0, 1       # i = 1
    (0x0C)  ADDI x9, x0, 12      # n = 12
    loop (0x10):
        (0x10)  ADD  x7, x5, x6      # tmp = a + b
        (0x14)  ADDI x5, x6, 0       # a = b
        (0x18)  ADDI x6, x7, 0       # b = tmp
        (0x1C)  ADDI x8, x8, 1       # i++
        (0x20)  BNE  x8, x9, -16     # if i != n goto loop (0x20 + (-16) = 0x10)
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 0),
            rv32i.encode_addi(6, 0, 1),
            rv32i.encode_addi(8, 0, 1),
            rv32i.encode_addi(9, 0, 12),
            rv32i.encode_add(7, 5, 6),  # loop
            rv32i.encode_addi(5, 6, 0),
            rv32i.encode_addi(6, 7, 0),
            rv32i.encode_addi(8, 8, 1),
            rv32i.encode_bne(8, 9, -16),
        ],
    )

    # 4 setup + 11 loop iterations * 5 instrs = 59 instructions
    # (i goes 1,2,...,12: 11 taken branches + final BNE not taken still executes)
    await run_instructions(dut, 59)

    # Debug: read all fibonacci registers
    pc = int(dut.dbg_pc.value)
    dut._log.info(f"After fibonacci: PC={pc:#010x}")

    for reg in [5, 6, 7, 8, 9]:
        val = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {val} ({val:#010x})")

    fib = await read_reg(dut, 6)
    assert fib == 144, f"fib(12): got {fib}, expected 144 (0x{144:X})"


@cocotb.test()
async def test_fibonacci_compressed(dut):
    """Compute fib(12) = 144 using RV32C compressed instructions.

    Register assignment:
      x8  = a (fib n-2), starts at 0
      x9  = b (fib n-1), starts at 1
      x10 = temp
      x11 = loop counter, counts down from 11 to 0

    After 11 iterations x9 = fib(12) = 144.

    Byte layout (two C instructions packed per 32-bit word):
      0x00  C.LI  x8,  0      a = 0
      0x02  C.LI  x9,  1      b = 1
      0x04  C.LI  x11, 11     counter = 11
    loop:
      0x06  C.MV  x10, x9     tmp = b
      0x08  C.ADD x9,  x8     b += a
      0x0A  C.MV  x8,  x10    a = tmp
      0x0C  C.ADDI x11, -1    counter--
      0x0E  C.BNEZ x11, -8    if counter != 0, goto 0x06
    """
    c_program = [
        rv32c.encode_c_li(8, 0),  # C.LI  x8,  0
        rv32c.encode_c_li(9, 1),  # C.LI  x9,  1
        rv32c.encode_c_li(11, 11),  # C.LI  x11, 11
        rv32c.encode_c_mv(10, 9),  # C.MV  x10, x9
        rv32c.encode_c_add(9, 8),  # C.ADD x9,  x8
        rv32c.encode_c_mv(8, 10),  # C.MV  x8,  x10
        rv32c.encode_c_addi(11, -1),  # C.ADDI x11, -1
        rv32c.encode_c_bnez(11, -8),  # C.BNEZ x11, -8
    ]
    await setup_compressed(dut, c_program)

    # 3 setup instructions + 11 iterations × 5 instructions = 58 total
    await run_instructions(dut, 58)

    x8 = await read_reg(dut, 8)
    x9 = await read_reg(dut, 9)
    dut._log.info(
        f"After compressed fibonacci: x8={x8} (fib(11)={89}), x9={x9} (fib(12)={144})"
    )
    assert x8 == 89, f"fib(11): got x8={x8}, expected 89"
    assert x9 == 144, f"fib(12): got x9={x9}, expected 144"


@cocotb.test()
async def test_load_store_word(dut):
    """Store words to memory, load them back, verify round-trip.

    Uses addresses 0x80+ (word 32+) safely above the program area.

    Program:
      ADDI x5, x0, 171    # x5 = 0xAB
      ADDI x6, x0, 128    # x6 = 0x80 (data base address)
      SW   x5, 0(x6)      # mem[0x80] = 0xAB
      LW   x7, 0(x6)      # x7 = mem[0x80] — expect 0xAB
      ADDI x8, x0, 55     # x8 = 0x37
      ADD  x9, x5, x8     # x9 = 0xAB + 0x37 = 0xE2
      SW   x9, 4(x6)      # mem[0x84] = 0xE2
      LW   x10, 4(x6)     # x10 = mem[0x84] — expect 0xE2
      LW   x11, 0(x6)     # x11 = mem[0x80] — expect 0xAB (still there)
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 171),    # x5 = 0xAB
            rv32i.encode_addi(6, 0, 128),    # x6 = 0x80
            rv32i.encode_sw(6, 5, 0),        # mem[0x80] = x5
            rv32i.encode_lw(7, 6, 0),        # x7 = mem[0x80]
            rv32i.encode_addi(8, 0, 55),     # x8 = 0x37
            rv32i.encode_add(9, 5, 8),       # x9 = x5 + x8 = 0xE2
            rv32i.encode_sw(6, 9, 4),        # mem[0x84] = x9
            rv32i.encode_lw(10, 6, 4),       # x10 = mem[0x84]
            rv32i.encode_lw(11, 6, 0),       # x11 = mem[0x80]
        ],
    )
    await run_instructions(dut, 9)

    expected = {5: 171, 7: 171, 8: 55, 9: 226, 10: 226, 11: 171}
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got} ({got:#010x}), expected {val} ({val:#010x})")
        assert got == val, f"x{reg}: got {got}, expected {val}"


@cocotb.test()
async def test_load_store_computed(dut):
    """Store-load-compute loop: accumulate values through memory.

    Program:
      ADDI x5, x0, 10       # x5 = 10
      ADDI x6, x0, 128      # x6 = 0x80 (data base)
      SW   x5, 0(x6)        # mem[0x80] = 10
      LW   x7, 0(x6)        # x7 = 10
      ADD  x7, x7, x5       # x7 = 10 + 10 = 20
      SW   x7, 4(x6)        # mem[0x84] = 20
      LW   x8, 4(x6)        # x8 = 20
      ADD  x8, x8, x7       # x8 = 20 + 20 = 40
      SW   x8, 8(x6)        # mem[0x88] = 40
      LW   x9, 8(x6)        # x9 = 40
      LW   x10, 0(x6)       # x10 = 10 (verify original still intact)
      ADD  x11, x9, x10     # x11 = 40 + 10 = 50
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 10),
            rv32i.encode_addi(6, 0, 128),
            rv32i.encode_sw(6, 5, 0),
            rv32i.encode_lw(7, 6, 0),
            rv32i.encode_add(7, 7, 5),
            rv32i.encode_sw(6, 7, 4),
            rv32i.encode_lw(8, 6, 4),
            rv32i.encode_add(8, 8, 7),
            rv32i.encode_sw(6, 8, 8),
            rv32i.encode_lw(9, 6, 8),
            rv32i.encode_lw(10, 6, 0),
            rv32i.encode_add(11, 9, 10),
        ],
    )
    await run_instructions(dut, 12)

    expected = {5: 10, 7: 20, 8: 40, 9: 40, 10: 10, 11: 50}
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got} ({got:#010x}), expected {val} ({val:#010x})")
        assert got == val, f"x{reg}: got {got}, expected {val}"
