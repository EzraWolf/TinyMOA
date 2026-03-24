"""
TinyMOA system integration tests.

Tests PAR IO, debug stream, and CPU-DCIM communication through tinymoa_top.
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge
import utility.rv32i_encode as rv32i


async def setup(dut):
    """Reset and configure for PAR mode."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    dut.is_parallel.value = 0
    dut.par_space.value = 0
    dut.par_cpu_nrst.value = 0
    dut.par_we.value = 0
    dut.par_oe.value = 0
    dut.par_addr.value = 0
    dut.dbg_en.value = 0
    dut.par_data_in.value = 0

    dut.nrst.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


async def par_write_nibbles(dut, data):
    """Write one 32-bit word via 8 nibble strobes (LSN first). Does NOT set mode/addr."""
    for nibble_idx in range(8):
        nibble = (data >> (nibble_idx * 4)) & 0xF
        dut.par_data_in.value = nibble
        dut.par_we.value = 1
        await ClockCycles(dut.clk, 1)
        dut.par_we.value = 0
        await ClockCycles(dut.clk, 1)
    await ClockCycles(dut.clk, 1)


async def par_load_words(dut, region, words):
    """Load a list of 32-bit words into TCM via PAR auto-increment.
    region: 0=code(0x000), 1=weights(0x1A0), 2=acts(0x1C0), 3=results(0x1E0)
    """
    dut.is_parallel.value = 1
    dut.par_space.value = 0  # TCM
    dut.par_addr.value = region
    dut.par_cpu_nrst.value = 0  # hold CPU in reset
    await ClockCycles(dut.clk, 2)  # let addr counter reset to base
    for w in words:
        await par_write_nibbles(dut, w)


async def par_mmio_write(dut, reg_idx, data):
    """Write 32-bit value to DCIM MMIO register via PAR.
    reg_idx: 0=CTRL, 1=STATUS, 2=WEIGHT_BASE, 3=ACT_BASE
    """
    dut.is_parallel.value = 1
    dut.par_space.value = 1  # MMIO
    dut.par_addr.value = reg_idx & 0x3
    await ClockCycles(dut.clk, 1)
    await par_write_nibbles(dut, data)


async def par_mmio_read(dut, reg_idx):
    """Read 32-bit value from DCIM MMIO register via PAR.
    1. Toggle par_addr to reset nibble counter.
    2. Assert par_oe to trigger DCIM read and latch mmio_rdata.
    3. Toggle addr again to reset nibble counter after the trigger.
    4. Read 8 nibbles (await first so registered output settles).
    """
    dut.is_parallel.value = 1
    dut.par_space.value = 1  # MMIO
    dut.par_we.value = 0
    dut.par_oe.value = 0

    # Reset nibble counter by toggling par_addr
    dut.par_addr.value = (reg_idx + 1) & 0x3
    await ClockCycles(dut.clk, 1)
    dut.par_addr.value = reg_idx & 0x3
    await ClockCycles(dut.clk, 1)

    # Trigger DCIM read (1 cycle par_oe latches mmio_rdata)
    dut.par_oe.value = 1
    await ClockCycles(dut.clk, 1)

    # Reset nibble counter again (par_oe advanced it to 1)
    dut.par_oe.value = 0
    dut.par_addr.value = (reg_idx + 1) & 0x3
    await ClockCycles(dut.clk, 1)
    dut.par_addr.value = reg_idx & 0x3
    await ClockCycles(dut.clk, 1)

    # Read 8 nibbles. Await THEN read so registered output is valid.
    dut.par_oe.value = 1
    word = 0
    for nibble_idx in range(8):
        await ClockCycles(dut.clk, 1)
        nibble = int(dut.par_data_out.value)
        word |= (nibble & 0xF) << (nibble_idx * 4)

    dut.par_oe.value = 0
    await ClockCycles(dut.clk, 1)
    return word


@cocotb.test()
async def test_par_rdy_pulses(dut):
    """PAR mode: writing 8 nibbles produces a par_rdy pulse."""
    await setup(dut)

    dut.is_parallel.value = 1
    dut.par_space.value = 0
    dut.par_addr.value = 0
    await ClockCycles(dut.clk, 1)

    # Write 8 nibbles (0x0 through 0x7)
    for i in range(8):
        dut.par_data_in.value = i
        dut.par_we.value = 1
        await ClockCycles(dut.clk, 1)
        dut.par_we.value = 0
        await ClockCycles(dut.clk, 1)

    # After 8 nibbles: par_rdy should have pulsed, address should be 1
    await ClockCycles(dut.clk, 1)
    addr = int(dut.par_addr_out.value)
    assert addr == 1, f"word address should be 1 after first word commit, got {addr}"


@cocotb.test()
async def test_par_addr_increments(dut):
    """PAR mode: word address increments after writing two full words."""
    await setup(dut)

    dut.is_parallel.value = 1
    dut.par_space.value = 0
    dut.par_addr.value = 0
    await ClockCycles(dut.clk, 2)

    # Write two full words (16 nibble strobes)
    await par_write_nibbles(dut, 0xDEADBEEF)
    await par_write_nibbles(dut, 0xCAFEBABE)

    addr = int(dut.par_addr_out.value)
    assert addr == 2, f"word address should be 2 after two words, got {addr}"


@cocotb.test()
async def test_dbg_strobe_sync_byte(dut):
    """Debug mode: first 8 bits of frame should be 0xAA sync byte."""
    await setup(dut)

    # Let shift register pre-load after reset
    await ClockCycles(dut.clk, 1)

    # Enter debug mode
    dut.dbg_en.value = 1
    await ClockCycles(dut.clk, 1)

    # Read first 8 bits (should be 0xAA = 10101010)
    sync = 0
    for i in range(8):
        await RisingEdge(dut.clk)
        bit = int(dut.dbg_strobe.value)
        sync = (sync << 1) | bit

    assert sync == 0xAA, f"sync byte should be 0xAA, got 0x{sync:02X}"


@cocotb.test()
async def test_dbg_frame_end_pulses(dut):
    """Debug mode: dbg_frame_end pulses after 144 bits."""
    await setup(dut)

    dut.dbg_en.value = 1
    await ClockCycles(dut.clk, 1)

    # Wait for frame_end pulse (should come at bit 143)
    for cycle in range(200):
        await RisingEdge(dut.clk)
        if int(dut.dbg_frame_end.value) == 1:
            # Frame end should occur at cycle ~143
            assert cycle >= 140, f"frame_end too early at cycle {cycle}"
            assert cycle <= 145, f"frame_end too late at cycle {cycle}"
            return

    assert False, "dbg_frame_end never pulsed within 200 cycles"


@cocotb.test()
async def test_cpu_reset_held_in_par_mode(dut):
    """PAR mode with par_cpu_nrst=0 keeps CPU in reset."""
    await setup(dut)

    dut.is_parallel.value = 1
    dut.par_cpu_nrst.value = 0
    await ClockCycles(dut.clk, 5)

    # CPU should be stuck in FETCH (state 0) since it's held in reset
    state = int(dut.cpu_state.value)
    assert state == 0, f"CPU should be in FETCH (reset), got state {state}"


@cocotb.test()
async def test_output_pins_default_ser_mode(dut):
    """SER mode defaults: NCS lines all high (deasserted), QSPI idle."""
    await setup(dut)

    dut.is_parallel.value = 0
    await ClockCycles(dut.clk, 2)

    uo_val = int(dut.uo_out.value)
    # uo[7:4] should be NCS lines, all high (deasserted) = 0xF0
    # uo[3:2] = qspi_sck=0, qspi_oe=0
    # uo[1:0] = dbg_frame_end=0, dbg_strobe=X (depends on shift reg)
    ncs = (uo_val >> 4) & 0xF
    assert ncs == 0xF, f"NCS lines should all be high in idle, got 0x{ncs:X}"

    sck = (uo_val >> 3) & 1
    assert sck == 0, f"QSPI SCK should be 0 in idle, got {sck}"


@cocotb.test()
async def test_par_dcim_mmio_write_read(dut):
    """PAR writes DCIM WEIGHT_BASE register and reads it back."""
    await setup(dut)

    # Write 0x123 to WEIGHT_BASE (register 2)
    await par_mmio_write(dut, 2, 0x123)

    # Read it back
    result = await par_mmio_read(dut, 2)
    # WEIGHT_BASE is 10 bits, so mask
    assert (result & 0x3FF) == 0x123, (
        f"WEIGHT_BASE readback: expected 0x123, got 0x{result:08X}"
    )


@cocotb.test()
async def test_par_load_tcm_and_cpu_executes(dut):
    """PAR loads a program into TCM, CPU runs it and writes result to TCM."""
    await setup(dut)

    # Program: write 0x1A0 to DCIM WEIGHT_BASE via MMIO, read it back,
    # store to TCM byte 0x80 (word 0x20). Then self-loop.
    #
    # Registers: x4=tp (DCIM base), x10=a0, x11=a1
    program = [
        rv32i.encode_lui(4, 0x400),  # x4 = 0x400000 (tp = DCIM MMIO base)
        rv32i.encode_addi(10, 0, 0x1A0),  # x10 = 0x1A0
        rv32i.encode_sw(4, 10, 0x08),  # SW x10, 0x08(x4) -> WEIGHT_BASE = 0x1A0
        rv32i.encode_lw(11, 4, 0x08),  # LW x11, 0x08(x4) -> x11 = WEIGHT_BASE
        rv32i.encode_sw(0, 11, 0x20),  # SW x11, 0x20(x0) -> TCM word 0x20
        rv32i.encode_beq(0, 0, 0),  # BEQ x0, x0, 0 -> self-loop
    ]

    # Load program via PAR into code region (auto-increment from word 0)
    await par_load_words(dut, 0, program)

    # Verify program loaded into TCM
    for i in range(len(program)):
        try:
            val = int(dut.dut.tcm.mem[i].value)
            dut._log.info(f"TCM[{i}] = 0x{val:08X} (expected 0x{program[i]:08X})")
        except ValueError:
            dut._log.error(f"TCM[{i}] = X (not written!)")

    # Release CPU
    dut.par_we.value = 0
    dut.par_cpu_nrst.value = 1

    names = ["FETCH", "DECODE", "EXEC", "MEM", "WB"]
    for cyc in range(60):
        await ClockCycles(dut.clk, 1)
        try:
            st = int(dut.cpu_state.value)
            pc = int(dut.cpu_pc.value)
            sn = names[st] if st < len(names) else f"?{st}"
            ready = int(dut.dut.cpu_mem_ready.value)
            rd = int(dut.dut.cpu_mem_read.value)
            wr = int(dut.dut.cpu_mem_write.value)
            addr = int(dut.dut.cpu_mem_addr.value)
            dut._log.info(
                f"cy{cyc:3d} {sn:<6s} pc={pc} addr=0x{addr:06X} rd={rd} wr={wr} rdy={ready}"
            )
        except Exception:
            dut._log.info(f"cy{cyc:3d} X values")

    # Check TCM word 0x20 (byte 0x80) via behavioral memory
    try:
        result = int(dut.dut.tcm.mem[0x20].value)
    except ValueError:
        pc = int(dut.cpu_pc.value) if hasattr(dut, "cpu_pc") else "?"
        state = int(dut.cpu_state.value) if hasattr(dut, "cpu_state") else "?"
        assert False, f"TCM[0x20] is X. CPU pc={pc} state={state}"

    assert result == 0x1A0, (
        f"CPU->DCIM roundtrip: expected 0x1A0 at TCM[0x20], got 0x{result:08X}"
    )


@cocotb.test()
async def test_cpu_triggers_dcim_compute(dut):
    """CPU starts DCIM inference, polls for done, reads result from TCM.

    All-ones weights (16 words at 0x1A0), all-ones activation (1 word at 0x1C0).
    16x16, 1-bit precision. Expected result per column: 16.
    CPU writes CTRL, polls STATUS, loads result[0], stores to TCM[0x30].
    """
    await setup(dut)

    # Pre-load weights (16 words of 0xFFFF at 0x1A0) and activation (0xFFFF at 0x1C0)
    weight_data = [0x0000FFFF] * 16
    act_data = [0x0000FFFF]

    await par_load_words(dut, 1, weight_data)  # region 1 = 0x1A0
    await par_load_words(dut, 2, act_data)     # region 2 = 0x1C0

    # Verify weights loaded
    for i in range(16):
        val = int(dut.dut.tcm.mem[0x1A0 + i].value)
        assert val == 0xFFFF, f"weight[{i}] = 0x{val:08X}, expected 0xFFFF"
    val = int(dut.dut.tcm.mem[0x1C0].value)
    assert val == 0xFFFF, f"act[0] = 0x{val:08X}, expected 0xFFFF"

    # CPU program:
    #  0: LUI x4, 0x400         # x4 = 0x400000 (DCIM MMIO base)
    #  1: ADDI x10, x0, 0x13    # x10 = 0x13 (reload=1, prec=1, start=1)
    #  2: SW x10, 0x00(x4)      # CTRL = 0x13 -> start inference
    #  3: LW x11, 0x04(x4)      # x11 = STATUS
    #  4: ANDI x11, x11, 0x2    # x11 &= DONE bit
    #  5: BEQ x11, x0, -8       # loop to 3 if not done
    #  6: ADDI x12, x0, 0x1E0   # x12 = result base address
    #  7: LW x13, 0x00(x12)     # x13 = result[0]
    #  8: SW x0, x13, 0x30       # TCM[0x30] = result[0]
    #  9: BEQ x0, x0, 0          # self-loop
    program = [
        rv32i.encode_lui(4, 0x400),
        rv32i.encode_addi(10, 0, 0x13),
        rv32i.encode_sw(4, 10, 0x00),
        rv32i.encode_lw(11, 4, 0x04),
        rv32i.encode_andi(11, 11, 0x2),
        rv32i.encode_beq(11, 0, -8),
        rv32i.encode_addi(12, 0, 0x1E0),
        rv32i.encode_lw(13, 12, 0x00),
        rv32i.encode_sw(0, 13, 0x30),
        rv32i.encode_beq(0, 0, 0),
    ]

    await par_load_words(dut, 0, program)

    # Release CPU and exit PAR mode so port B is free for DCIM
    dut.par_we.value = 0
    dut.par_cpu_nrst.value = 1
    dut.is_parallel.value = 0

    # Wait long enough for inference + CPU polling + result read
    names = ["FETCH", "DECODE", "EXEC", "MEM", "WB"]
    for cyc in range(300):
        await ClockCycles(dut.clk, 1)
        try:
            st = int(dut.cpu_state.value)
            pc = int(dut.cpu_pc.value)
            sn = names[st] if st < len(names) else f"?{st}"
            ready = int(dut.dut.cpu_mem_ready.value)
            rd = int(dut.dut.cpu_mem_read.value)
            wr = int(dut.dut.cpu_mem_write.value)
            addr = int(dut.dut.cpu_mem_addr.value)
            ds = int(dut.dcim_state.value)
            dut._log.info(
                f"cy{cyc:3d} {sn:<6s} pc={pc} addr=0x{addr:06X} rd={rd} wr={wr} rdy={ready} dcim={ds}"
            )
            if pc == 9:
                dut._log.info(f"cy{cyc:3d} CPU reached self-loop at PC=9")
                break
        except Exception as e:
            dut._log.info(f"cy{cyc:3d} X values: {e}")
    else:
        assert False, "CPU never reached self-loop (PC=9) within 300 cycles"

    # Debug: check weights in TCM
    for i in range(4):
        try:
            wv = int(dut.dut.tcm.mem[0x1A0 + i].value)
            dut._log.info(f"TCM[0x{0x1A0+i:03X}] = 0x{wv:08X}")
        except ValueError:
            dut._log.error(f"TCM[0x{0x1A0+i:03X}] = X (weight lost!)")

    # Debug: check DCIM internals
    try:
        sa0 = int(dut.dut.dcim.shift_acc[0].value)
        dut._log.info(f"DCIM shift_acc[0] = {sa0}")
    except ValueError:
        dut._log.error("DCIM shift_acc[0] = X")
    try:
        br = int(dut.dut.dcim.bias_reg.value)
        dut._log.info(f"DCIM bias_reg = {br}")
    except ValueError:
        dut._log.error("DCIM bias_reg = X")
    try:
        w0 = int(dut.dut.dcim.weight_reg[0].value)
        dut._log.info(f"DCIM weight_reg[0] = 0x{w0:04X}")
    except ValueError:
        dut._log.error("DCIM weight_reg[0] = X")

    # Debug: check DCIM results at 0x1E0
    for i in range(4):
        try:
            v = int(dut.dut.tcm.mem[0x1E0 + i].value)
            dut._log.info(f"TCM[0x{0x1E0+i:03X}] = {v} (0x{v:08X})")
        except ValueError:
            dut._log.error(f"TCM[0x{0x1E0+i:03X}] = X")

    # Check TCM[0x30] for the DCIM result
    try:
        result = int(dut.dut.tcm.mem[0x30].value)
    except ValueError:
        assert False, "TCM[0x30] is X - CPU never wrote the result"

    # Convert to signed
    if result >= 0x80000000:
        result -= 0x100000000

    assert result == 16, (
        f"CPU-DCIM compute: expected 16 at TCM[0x30], got {result}"
    )
