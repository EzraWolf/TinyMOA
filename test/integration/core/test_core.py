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
S_EX2 = 6  # Second execute pass for MUL/SHIFT/SLT


async def setup(dut, program=None, data=None):
    """Initialize the core testbench.

    program: list of 32-bit instruction words loaded starting at address 0.
             Remaining memory is filled with NOPs.
    data:    dict of {word_index: value} for pre-loading data words (e.g. for
             sub-word load tests). Applied after program loading, before nrst.
    """
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

    if data:
        for word_idx, value in data.items():
            dut.mem[word_idx].value = value

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
    """PC increments by 4 for each 32b NOP."""
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

    # 4 setup + (11 iters * 5 instrs) = 59 instructions
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
        rv32c.encode_c_li(8, 0),
        rv32c.encode_c_li(9, 1),
        rv32c.encode_c_li(11, 11),
        rv32c.encode_c_mv(10, 9),
        rv32c.encode_c_add(9, 8),
        rv32c.encode_c_mv(8, 10),
        rv32c.encode_c_addi(11, -1),
        rv32c.encode_c_bnez(11, -8),
    ]
    await setup_compressed(dut, c_program)

    # 3 setup + (11 iters * 5 instr)
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
            rv32i.encode_addi(5, 0, 171),  # x5 = 0xAB
            rv32i.encode_addi(6, 0, 128),  # x6 = 0x80
            rv32i.encode_sw(6, 5, 0),  # mem[0x80] = x5
            rv32i.encode_lw(7, 6, 0),  # x7 = mem[0x80]
            rv32i.encode_addi(8, 0, 55),  # x8 = 0x37
            rv32i.encode_add(9, 5, 8),  # x9 = x5 + x8 = 0xE2
            rv32i.encode_sw(6, 9, 4),  # mem[0x84] = x9
            rv32i.encode_lw(10, 6, 4),  # x10 = mem[0x84]
            rv32i.encode_lw(11, 6, 0),  # x11 = mem[0x80]
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


# =============================================================================
# LUI / AUIPC
# =============================================================================


@cocotb.test()
async def test_lui_auipc(dut):
    """LUI loads a 20-bit upper immediate. AUIPC adds it to the instruction's PC.

    Program:
      0x00  LUI   x5, 0x12345   x5 = 0x12345000
      0x04  AUIPC x6, 1         x6 = PC + 0x1000 = 0x04 + 0x1000 = 0x1004
      0x08  AUIPC x7, 0         x7 = PC = 0x08  (upper imm=0 -> adds 0)
    """
    await setup(
        dut,
        [
            rv32i.encode_lui(5, 0x12345),
            rv32i.encode_auipc(6, 1),
            rv32i.encode_auipc(7, 0),
        ],
    )
    await run_instructions(dut, 3)

    x5 = await read_reg(dut, 5)
    x6 = await read_reg(dut, 6)
    x7 = await read_reg(dut, 7)
    dut._log.info(f"x5={x5:#010x} x6={x6:#010x} x7={x7:#010x}")
    assert x5 == 0x12345000, f"LUI: got {x5:#010x}, expected 0x12345000"
    assert x6 == 0x1004, f"AUIPC x6: got {x6:#010x}, expected 0x00001004"
    assert x7 == 0x0008, f"AUIPC x7: got {x7:#010x}, expected 0x00000008"


# Shifts (via S_EX2 with fully-assembled rs1_full)
@cocotb.test()
async def test_shifts_immediate(dut):
    """Immediate shifts: SLLI, SRLI, SRAI.

    Uses x5=0x80000001 as the test value to cover both MSB and LSB simultaneously.
    Constructs x5 via: LUI x5, 0x80000 -> x5=0x80000000, then ADDI x5, x5, 1.

    Expected:
      SLLI x6, x5, 1  -> 0x80000001 << 1 = 0x00000002  (left shift, MSB dropped)
      SRLI x7, x5, 1  -> 0x80000001 >> 1 = 0x40000000  (logical, zero-fill MSB)
      SRAI x8, x5, 1  -> 0x80000001 >> 1 = 0xC0000000  (arithmetic, sign-fill MSB)
      SLLI x9, x5, 4  -> 0x80000001 << 4 = 0x00000010
      SRLI x10, x5, 4 -> 0x80000001 >> 4 = 0x08000000  (logical)
      SRAI x10... reuse register — use x5 = 0xF0000000 for last two
    """
    await setup(
        dut,
        [
            rv32i.encode_lui(5, 0x80000),  # x5 = 0x80000000
            rv32i.encode_addi(5, 5, 1),  # x5 = 0x80000001
            rv32i.encode_slli(6, 5, 1),  # x6 = 0x80000001 << 1 = 0x00000002
            rv32i.encode_srli(7, 5, 1),  # x7 = 0x80000001 >> 1 = 0x40000000 (logical)
            rv32i.encode_srai(8, 5, 1),  # x8 = 0x80000001 >> 1 = 0xC0000000 (arith)
            rv32i.encode_slli(9, 5, 4),  # x9 = 0x80000001 << 4 = 0x00000010
            rv32i.encode_srli(
                10, 5, 28
            ),  # x10 = 0x80000001 >> 28 = 0x00000008 (logical)
            rv32i.encode_srai(
                11, 5, 28
            ),  # x11 = 0x80000001 >> 28 arithmetic = 0xFFFFFFF8
            # bits[31:28] of original = 1000b = 8; upper 28 positions filled with sign=1
        ],
    )
    await run_instructions(dut, 8)

    expected = {
        5: 0x80000001,
        6: 0x00000002,
        7: 0x40000000,
        8: 0xC0000000,
        9: 0x00000010,
        10: 0x00000008,
        11: 0xFFFFFFF8,
    }
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got:#010x}, expected {val:#010x}")
        assert got == val, f"x{reg}: got {got:#010x}, expected {val:#010x}"


@cocotb.test()
async def test_shifts_register(dut):
    """Register shifts: SLL, SRL, SRA.

    Shift amount is taken from rs2[4:0], which is the register VALUE (not register number).
    Uses small shift amounts to avoid register-number coincidence.

    x5 = 0x80000001 (test value)
    x6 = 3          (shift amount)

    Expected:
      SLL x7, x5, x6  -> 0x80000001 << 3 = 0x00000008
      SRL x8, x5, x6  -> 0x80000001 >> 3 = 0x10000000 (logical)
      SRA x9, x5, x6  -> 0x80000001 >> 3 = 0xF0000000 (arithmetic)
    """
    await setup(
        dut,
        [
            rv32i.encode_lui(5, 0x80000),
            rv32i.encode_addi(5, 5, 1),  # x5 = 0x80000001
            rv32i.encode_addi(6, 0, 3),  # x6 = 3 (shift amount)
            rv32i.encode_sll(7, 5, 6),  # x7 = x5 << x6 = 0x80000001 << 3 = 0x00000008
            rv32i.encode_srl(8, 5, 6),  # x8 = x5 >> x6 (logical) = 0x10000000
            rv32i.encode_sra(9, 5, 6),  # x9 = x5 >> x6 (arith)   = 0xF0000000
        ],
    )
    await run_instructions(dut, 6)

    expected = {5: 0x80000001, 6: 3, 7: 0x00000008, 8: 0x10000000, 9: 0xF0000000}
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got:#010x}, expected {val:#010x}")
        assert got == val, f"x{reg}: got {got:#010x}, expected {val:#010x}"


# =============================================================================
# SLT / SLTU (via S_EX2 with final alu_cmp)
# =============================================================================


@cocotb.test()
async def test_slt_sltu(dut):
    """SLT/SLTU: set rd=1 if rs1 < rs2, else rd=0.

    Key cases:
      SLT  (-1, 0)  -> 1  (-1 is less than 0 signed)
      SLT  (0, -1)  -> 0  (0 is NOT less than -1 signed)
      SLTU (-1, 0)  -> 0  (0xFFFFFFFF is NOT less than 0 unsigned)
      SLTU (0, -1)  -> 1  (0 IS less than 0xFFFFFFFF unsigned)
      SLTI (x, 5)   -> 1  if x < 5 signed
      SLTIU(x, 5)   -> 1  if x < 5 unsigned
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, -1),  # x5 = 0xFFFFFFFF (-1 signed)
            rv32i.encode_addi(6, 0, 0),  # x6 = 0
            rv32i.encode_slt(7, 5, 6),  # x7  = (-1 < 0  signed)   = 1
            rv32i.encode_slt(8, 6, 5),  # x8  = (0  < -1 signed)   = 0
            rv32i.encode_sltu(
                9, 5, 6
            ),  # x9  = (-1 < 0  unsigned) = 0  (0xFFFFFFFF > 0)
            rv32i.encode_sltu(
                10, 6, 5
            ),  # x10 = (0  < -1 unsigned) = 1  (0 < 0xFFFFFFFF)
            rv32i.encode_addi(11, 0, 3),  # x11 = 3
            rv32i.encode_slti(12, 11, 5),  # x12 = (3 < 5  signed)   = 1
            rv32i.encode_slti(13, 5, 5),  # x13 = (-1 < 5 signed)   = 1
            rv32i.encode_sltiu(14, 6, 1),  # x14 = (0 < 1  unsigned) = 1
            rv32i.encode_sltiu(15, 5, 1),  # x15 = (0xFFFFFFFF < 1 unsigned) = 0
        ],
    )
    await run_instructions(dut, 11)

    expected = {7: 1, 8: 0, 9: 0, 10: 1, 12: 1, 13: 1, 14: 1, 15: 0}
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got}, expected {val}")
        assert got == val, f"x{reg}: got {got}, expected {val}"


# Branches
@cocotb.test()
async def test_beq(dut):
    """BEQ: taken when rs1 == rs2, not-taken otherwise.

    Taken path:  x5 = x6 = 5 -> branch skips ADDI x7, x0, 99 -> x7 stays 42
    Not-taken path: x5=5, x6=6 -> falls through to ADDI x7, x0, 99 -> x7 = 99

    Note: registers are NOT reset on nrst (no reset in register file), so x7 must
    be written explicitly before the branch to have a known sentinel value.
    """
    # --- Taken ---
    # 0x00 ADDI x5, x0, 5
    # 0x04 ADDI x6, x0, 5
    # 0x08 ADDI x7, x0, 42    x7 = 42 (sentinel, must not change if branch taken)
    # 0x0C BEQ  x5, x6, +8    target = 0x14 (skips 0x10)
    # 0x10 ADDI x7, x0, 99    skipped
    # 0x14 ADDI x8, x0, 1     executed
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 5),
            rv32i.encode_addi(6, 0, 5),
            rv32i.encode_addi(7, 0, 42),
            rv32i.encode_beq(5, 6, 8),
            rv32i.encode_addi(7, 0, 99),
            rv32i.encode_addi(8, 0, 1),
        ],
    )
    await run_instructions(dut, 5)  # ADDI x5, x6, x7=42, BEQ(taken), ADDI x8=1
    x7 = await read_reg(dut, 7)
    x8 = await read_reg(dut, 8)
    assert x7 == 42, f"BEQ taken: x7 was overwritten: got {x7}, expected 42"
    assert x8 == 1, f"BEQ taken: branch target not reached: x8={x8}"

    # Not-taken
    # 0x00 ADDI x5, x0, 5
    # 0x04 ADDI x6, x0, 6
    # 0x08 ADDI x7, x0, 42  ->  x7 = 42 (sentinel)
    # 0x0C BEQ  x5, x6, +8  ->  not taken (5 != 6), falls through to 0x10
    # 0x10 ADDI x7, x0, 99  ->  executed
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 5),
            rv32i.encode_addi(6, 0, 6),
            rv32i.encode_addi(7, 0, 42),
            rv32i.encode_beq(5, 6, 8),
            rv32i.encode_addi(7, 0, 99),
        ],
    )
    await run_instructions(dut, 5)  # ADDI x5, x6, x7=42, BEQ(not-taken), ADDI x7=99
    x7 = await read_reg(dut, 7)
    assert x7 == 99, f"BEQ not-taken: x7 should be 99, got {x7}"


@cocotb.test()
async def test_bne(dut):
    """BNE: taken when rs1 != rs2.

    Taken:     x5=5, x6=6 -> branch taken, ADDI x7 at +8 executed
    Not-taken: x5=5, x6=5 -> falls through, ADDI x7 at +4 executed
    """
    # --- Taken ---
    # 0x08 BNE x5, x6, +8 -> target = 0x10
    # 0x0C ADDI x7, x0, 0    skipped
    # 0x10 ADDI x7, x0, 1    executed
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 5),
            rv32i.encode_addi(6, 0, 6),
            rv32i.encode_bne(5, 6, 8),
            rv32i.encode_addi(7, 0, 0),
            rv32i.encode_addi(7, 0, 1),
        ],
    )
    await run_instructions(dut, 4)  # setup x5, x6, BNE(taken), ADDI x7=1
    x7 = await read_reg(dut, 7)
    assert x7 == 1, f"BNE taken: x7 should be 1, got {x7}"

    # --- Not-taken ---
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 5),
            rv32i.encode_addi(6, 0, 5),
            rv32i.encode_bne(5, 6, 8),
            rv32i.encode_addi(7, 0, 42),  # executed (fall through)
            rv32i.encode_addi(7, 0, 1),  # NOT executed
        ],
    )
    await run_instructions(dut, 4)  # setup x5, x6, BNE (not taken), ADDI x7=42
    x7 = await read_reg(dut, 7)
    assert x7 == 42, f"BNE not-taken: x7 should be 42, got {x7}"


@cocotb.test()
async def test_blt_bge(dut):
    """BLT/BGE: signed comparisons.

    BLT taken:  -1 < 0  (signed)
    BGE taken:   0 >= -1 (signed)
    BLT not-taken: 0 is NOT < -1 (signed, 0 > -1)
    """
    # BLT taken: x5=-1, x6=0, -1 < 0 then branch
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, -1),
            rv32i.encode_addi(6, 0, 0),
            rv32i.encode_blt(5, 6, 8),  # -1 < 0: taken
            rv32i.encode_addi(7, 0, 0),  # skipped
            rv32i.encode_addi(7, 0, 1),  # executed
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 1, f"BLT taken: got {x7}, expected 1"

    # BLT not-taken: x5=0, x6=-1, 0 < -1 is false signed
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 0),
            rv32i.encode_addi(6, 0, -1),
            rv32i.encode_blt(5, 6, 8),  # 0 < -1: NOT taken
            rv32i.encode_addi(7, 0, 42),  # executed
            rv32i.encode_addi(7, 0, 1),  # not reached
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 42, f"BLT not-taken: got {x7}, expected 42"

    # BGE taken: x5=0, x6=-1, 0 >= -1 signed -> taken
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 0),
            rv32i.encode_addi(6, 0, -1),
            rv32i.encode_bge(5, 6, 8),  # 0 >= -1: taken
            rv32i.encode_addi(7, 0, 0),  # skipped
            rv32i.encode_addi(7, 0, 1),  # executed
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 1, f"BGE taken: got {x7}, expected 1"


@cocotb.test()
async def test_bltu_bgeu(dut):
    """BLTU/BGEU: unsigned comparisons.

    BLTU taken:  0 < 1 unsigned
    BGEU taken:  0xFFFFFFFF >= 1 unsigned
    BLTU not-taken: 0xFFFFFFFF is NOT < 1 unsigned
    """
    # BLTU taken: 0 < 1
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 0),
            rv32i.encode_addi(6, 0, 1),
            rv32i.encode_bltu(5, 6, 8),  # 0 < 1 unsigned: taken
            rv32i.encode_addi(7, 0, 0),  # skipped
            rv32i.encode_addi(7, 0, 1),  # executed
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 1, f"BLTU taken: got {x7}, expected 1"

    # BLTU not-taken: 0xFFFFFFFF >= 1 unsigned, so 0xFFFFFFFF < 1 is false
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, -1),  # x5 = 0xFFFFFFFF
            rv32i.encode_addi(6, 0, 1),
            rv32i.encode_bltu(5, 6, 8),  # 0xFFFFFFFF < 1 unsigned: NOT taken
            rv32i.encode_addi(7, 0, 42),  # executed
            rv32i.encode_addi(7, 0, 1),  # not reached
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 42, f"BLTU not-taken: got {x7}, expected 42"

    # BGEU taken: 0xFFFFFFFF >= 1 unsigned
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, -1),  # x5 = 0xFFFFFFFF
            rv32i.encode_addi(6, 0, 1),
            rv32i.encode_bgeu(5, 6, 8),  # 0xFFFFFFFF >= 1 unsigned: taken
            rv32i.encode_addi(7, 0, 0),  # skipped
            rv32i.encode_addi(7, 0, 1),  # executed
        ],
    )
    await run_instructions(dut, 4)
    x7 = await read_reg(dut, 7)
    assert x7 == 1, f"BGEU taken: got {x7}, expected 1"


# JAL / JALR
@cocotb.test()
async def test_jal(dut):
    """JAL: jumps and writes return address to rd.

    Program:
      0x00  ADDI x5, x0, 0     x5 = 0 (sentinel, should stay 0)
      0x04  JAL  x1, +8        x1 = 0x08 (return addr = PC+4), jump to 0x0C
      0x08  ADDI x5, x0, 99    skipped
      0x0C  ADDI x6, x0, 1     executed (branch target)
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 0),
            rv32i.encode_jal(1, 8),
            rv32i.encode_addi(5, 0, 99),
            rv32i.encode_addi(6, 0, 1),
        ],
    )
    await run_instructions(dut, 3)  # ADDI x5, JAL, ADDI x6

    x1 = await read_reg(dut, 1)
    x5 = await read_reg(dut, 5)
    x6 = await read_reg(dut, 6)
    dut._log.info(f"x1={x1:#010x} x5={x5} x6={x6}")
    assert x1 == 0x08, f"JAL: x1 (return addr) = {x1:#010x}, expected 0x00000008"
    assert x5 == 0, f"JAL: skipped instr ran: x5={x5}, expected 0"
    assert x6 == 1, f"JAL: branch target not reached: x6={x6}, expected 1"


@cocotb.test()
async def test_jalr(dut):
    """JALR: jumps to rs1+imm (bit 0 cleared), writes return address to rd.

    Program:
      0x00  ADDI x5, x0, 0x1C  x5 = 28 = 0x1C (jump target)
      0x04  JALR x1, x5, 0     x1 = 0x08 (return addr), PC = x5 = 0x1C
      0x08-0x18                 skipped (6 instructions = NOPs)
      0x1C  ADDI x7, x0, 1     executed (jump target = word index 7)
    """
    program = [NOP] * 8
    program[0] = rv32i.encode_addi(5, 0, 0x1C)
    program[1] = rv32i.encode_jalr(1, 5, 0)
    # program[2..6] are NOPs
    program[7] = rv32i.encode_addi(7, 0, 1)
    await setup(dut, program)
    await run_instructions(dut, 3)  # ADDI x5, JALR, ADDI x7

    x1 = await read_reg(dut, 1)
    x7 = await read_reg(dut, 7)
    dut._log.info(f"x1={x1:#010x} x7={x7}")
    assert x1 == 0x08, f"JALR: x1 (return addr) = {x1:#010x}, expected 0x00000008"
    assert x7 == 1, f"JALR: branch target not reached: x7={x7}, expected 1"


# Sub-word loads (LB/LBU/LH/LHU at word-aligned offset 0)
@cocotb.test()
async def test_load_subword(dut):
    """LBU/LB/LHU/LH: verify byte and halfword extraction and sign/zero extension.

    Pre-loads mem[32] (byte address 0x80) with 0x00008180:
      byte[0] at 0x80 = 0x80  (bit 7=1: LB sign-extends to 0xFFFFFF80)
      byte[1] at 0x81 = 0x81  (bit 7=1: LB sign-extends to 0xFFFFFF81)
      half[0] at 0x80 = 0x8180 (bit 15=1: LH sign-extends to 0xFFFF8180)

    All loads are at offset 0 from the word-aligned base address 0x80.
    """
    # x6 = 0x80 (base address for all loads)
    program = [
        rv32i.encode_addi(6, 0, 0x80),  # x6 = 0x80
        rv32i.encode_lbu(5, 6, 0),  # x5 = LBU: byte[0x80] = 0x80 -> 0x00000080
        rv32i.encode_lb(7, 6, 0),  # x7 = LB:  byte[0x80] = 0x80 -> 0xFFFFFF80
        rv32i.encode_lhu(8, 6, 0),  # x8 = LHU: half[0x80] = 0x8180 -> 0x00008180
        rv32i.encode_lh(9, 6, 0),  # x9 = LH:  half[0x80] = 0x8180 -> 0xFFFF8180
        rv32i.encode_lw(10, 6, 0),  # x10 = LW: word[0x80] = 0x00008180
    ]
    # word index 32 = byte address 0x80
    await setup(dut, program, data={32: 0x00008180})
    await run_instructions(dut, len(program))

    expected = {
        5: 0x00000080,
        7: 0xFFFFFF80,
        8: 0x00008180,
        9: 0xFFFF8180,
        10: 0x00008180,
    }
    for reg, val in expected.items():
        got = await read_reg(dut, reg)
        dut._log.info(f"  x{reg} = {got:#010x}, expected {val:#010x}")
        assert got == val, f"x{reg}: got {got:#010x}, expected {val:#010x}"


# C.MUL (via S_EX2 EX2_MUL path)
@cocotb.test()
async def test_c_mul(dut):
    """C.MUL rd, rs2: rd = rd * rs2[15:0] (lower 32 bits of 32x16 product).

    Uses setup_compressed to pack 16-bit instructions into 32-bit words.

    Program:
      C.LI  x5, 6     x5 = 6
      C.LI  x6, 7     x6 = 7
      C.MUL x5, x6    x5 = 6 * 7 = 42
      C.NOP
    """
    c_program = [
        rv32c.encode_c_li(5, 6),
        rv32c.encode_c_li(6, 7),
        rv32c.encode_c_mul(5, 6),
        rv32c.encode_c_nop(),
    ]
    await setup_compressed(dut, c_program)
    await run_instructions(dut, 4)

    x5 = await read_reg(dut, 5)
    x6 = await read_reg(dut, 6)
    dut._log.info(f"C.MUL: x5={x5} (expected 42), x6={x6} (expected 7)")
    assert x5 == 42, f"C.MUL: got {x5}, expected 42 (6 * 7)"
    assert x6 == 7, f"C.MUL: x6 was modified: got {x6}, expected 7"


@cocotb.test()
async def test_c_mul_larger(dut):
    """C.MUL with larger values: 100 * 200 = 20000.

    Built with 32-bit setup instructions (ADDI), then packed C.MUL.
    The program mixes 32-bit and 16-bit instructions so we place C.MUL
    at word-aligned boundary after the 32-bit setup.

    Program (32-bit words):
      0x00  ADDI x5, x0, 100   (32b)
      0x04  ADDI x6, x0, 200   (32b)
      0x08  C.MUL x5, x6       (16b, low half of word)
            C.NOP               (16b, high half of word)
    """
    mul_word = (rv32c.encode_c_nop() << 16) | rv32c.encode_c_mul(5, 6)
    await setup(
        dut,
        [
            rv32i.encode_addi(5, 0, 100),
            rv32i.encode_addi(6, 0, 200),
            mul_word,
        ],
    )
    await run_instructions(dut, 4)  # ADDI x5, ADDI x6, C.MUL, C.NOP

    x5 = await read_reg(dut, 5)
    dut._log.info(f"C.MUL larger: x5={x5} (expected 20000)")
    assert x5 == 20000, f"C.MUL 100*200: got {x5}, expected 20000"
