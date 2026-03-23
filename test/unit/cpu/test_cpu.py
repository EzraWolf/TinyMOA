"""
CPU unit tests with behavioral TCM memory.

Programs load into dut.mem[] (word-addressed) before reset.
tb_cpu.v behavioral memory:
  addr < 256:  same-cycle ready (TCM, blocking assign)
  addr >= 256: 12-cycle latency (QSPI sim)

Cycle budget per instruction (non-pipelined FSM, same-cycle TCM):
  ALU/LUI/AUIPC:  FETCH(1) + DECODE(1) + EXEC(1) + WB(1) = 4
  Load/Store:      FETCH(1) + DECODE(1) + EXEC(1) + MEM(1) + WB(1) = 5
  Branch/Jump:     FETCH(1) + DECODE(1) + EXEC(1) + WB(1) = 4

  Planned tests:
  test_addi
  test_add
  test_sub
  test_and
  test_or
  test_xor
  test_fibonacci_rv32i
  test_fibonacci_rv32c
  test_is_prime_rv32i
  test_is_prime_rv32c
  test_linked_list_rv32i
  test_linked_list_rv32c
  test_single_neuron_rv32i
  test_single_neuron_rv32c
  test_simple_hash_rv32i
  test_simple_hash_rv32c"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
import utility.rv32i_encode as rv32i

NOP = rv32i.encode_addi(0, 0, 0)
HALT = rv32i.encode_jal(0, 0)

CYCLES_ALU = 4
CYCLES_MEM = 5
CYCLES_BRANCH = 4


async def setup(dut, instrs):
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())
    dut.nrst.value = 0

    for i in range(2048):
        dut.mem[i].value = 0

    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1

    for i, word in enumerate(instrs):
        dut.mem[i].value = word

    await ClockCycles(dut.clk, 1)


async def run_cycles(dut, n):
    """Run n clock cycles, logging state each cycle."""
    for i in range(n):
        state = int(dut.dbg_state.value)
        pc = int(dut.dbg_pc.value)
        instr = int(dut.dbg_instr.value)
        alu = int(dut.dbg_alu_result.value)
        names = ["FETCH", "DECODE", "EXEC", "MEM", "WB"]
        name = names[state] if state < len(names) else f"?{state}"
        dut._log.info(
            f"cycle {i:3d}  {name:<6s}  pc={pc}  instr={instr:08x}  alu={alu}"
        )
        await ClockCycles(dut.clk, 1)


async def run_until_wb(dut, timeout=50):
    """Run until WB state is reached, or timeout."""
    for i in range(timeout):
        await RisingEdge(dut.clk)
        if int(dut.dbg_state.value) == 4:  # FSM_WB
            return i + 1
    raise TimeoutError(f"WB not reached in {timeout} cycles")


@cocotb.test()
async def test_addi(dut):
    """
    addi x1, x0, 42   -> x1 = 42
    Check: dbg_alu_result == 42 after first instruction completes.
    """
    await setup(
        dut,
        [
            rv32i.encode_addi(1, 0, 42),
            HALT,
        ],
    )

    # Run until first WB, then check ALU result
    cycles = await run_until_wb(dut)
    dut._log.info(f"first WB reached after {cycles} cycles")

    result = int(dut.dbg_alu_result.value)
    assert result == 42, f"expected 42, got {result}"


@cocotb.test()
async def test_alu_store_load(dut):
    """
    addi x1, x0, 10      x1 = 10
    addi x2, x0, 7       x2 = 7
    add  x3, x1, x2      x3 = 17
    sw   x3, 128(x0)     mem[128] = 17
    lw   x4, 128(x0)     x4 = 17
    sub  x5, x4, x1      x5 = 17 - 10 = 7
    sw   x5, 129(x0)     mem[129] = 7
    halt
    """
    DATA = 128  # word address for data region (away from code)

    await setup(
        dut,
        [
            rv32i.encode_addi(1, 0, 10),  # 0: x1 = 10
            rv32i.encode_addi(2, 0, 7),  # 1: x2 = 7
            rv32i.encode_add(5, 1, 2),  # 2: x5 = 17
            rv32i.encode_sw(0, 5, DATA),  # 3: mem[128] = x5
            rv32i.encode_lw(6, 0, DATA),  # 4: x6 = mem[128]
            rv32i.encode_sub(7, 6, 1),  # 5: x7 = x6 - x1
            rv32i.encode_sw(0, 7, DATA + 1),  # 6: mem[129] = x7
            HALT,
        ],
    )

    # Run through all 7 instructions + HALT fetch
    await run_cycles(dut, 45)

    val_128 = int(dut.mem[DATA].value)
    val_129 = int(dut.mem[DATA + 1].value)
    assert val_128 == 17, f"mem[128] expected 17, got {val_128}"
    assert val_129 == 7, f"mem[129] expected 7, got {val_129}"
