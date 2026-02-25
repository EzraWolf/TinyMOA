"""
Atomic RV32EC instruction integration/combination tests for TinyMOA

RISC-V ISA reference:
https://ww1.microchip.com/downloads/aemDocuments/documents/FPGA/ProductDocuments/UserGuides/ip_cores/directcores/riscvspec.pdf
"""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_decoder(dut):
    clock = Clock(dut.clk, 4, units="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.instr.value = 0
    dut.imm.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1


# ============================================================================
# Memristor-based CIM Operations
# ============================================================================


@cocotb.test()
async def test_cim_swt(dut):
    """Test CIM.SWT - Store Weight/Word operation

    Loads weight data into the write data register for programming memristors.
    Typically used row-by-row during weight programming phase.

    Format: CIM.SWT <source>
      source: register containing 16-bit row data (for 16-column corelet)
              OR immediate value (encoding TBD)

    Unknwons:
    - Exact operand encoding (I-type immediate? Register only?)
    - How to handle different row widths (4-bit vs 16-bit arrays)
    - Whether this is always register-sourced or can use immediate

    Used in sequence:
      CIM.SMASK row=N       # Select which row to program
      CIM.SWT x5            # Load row data from register
      CIM.CMD mode=WRITE    # Set write mode
      CIM.PULSE             # Execute programming
    """
    pass


@cocotb.test()
async def test_cim_smask(dut):
    """Test CIM.SMASK - Store Mask for programming operations

    Controls which memristor cells are written during CIM.SWT operations.
    Supports both row selection (which row to program) and bit-level masking
    (for write-verify operations where only failed bits are reprogrammed).

    Format: CIM.SMASK <row_select>, <bit_mask>
      OR: CIM.SMASK mode=<MODE>, data=<DATA>

    Possible modes:
      - row=N: Select single row N for programming
      - bits=<mask>: Bit-level write mask (which bits to actually write)
      - all: Pass-through mode, write all bits

    Unknowns:
    - Exact instruction format (two operands? mode bits + data?)
    - Whether row and bit mask are separate instructions or combined
    - Default behavior when not specified
    - How to encode for different array sizes (4x4 vs 16x16)

    Example usage:
      CIM.SMASK row=5, bits=0xFFFF   # Row 5, all bits
      CIM.SWT x5                      # Weight data
      CIM.PULSE                       # Write
      # ... verify, find bits 8,9 failed ...
      CIM.SMASK row=5, bits=0x0300   # Rewrite only bits 8,9
      CIM.PULSE
    """
    pass


@cocotb.test()
async def test_cim_pmask(dut):
    """Test CIM.PMASK - Pulse Mask for compute operations

    Controls which rows/columns are active during CIM.PULSE compute operations.
    Uses combined row+column masking to allow computing on subregions of the array.

    Format: CIM.PMASK <row_mask>, <col_mask>
      row_mask: Which rows to activate (input vector bit pattern)
      col_mask: Which columns to read out (output selection)

    Think of it as intersection: only (active rows) * (active columns) participate.

    Examples:
      CIM.PMASK x5, 0xFFFF     # Row pattern from register, all columns
      CIM.PMASK 0xF000, 0x000F # Top 4 rows, bottom 4 columns only
      CIM.PMASK x5, x6         # Both from registers

    Unknowns:
    - Exact operand encoding (both registers? reg + imm? imm + imm?)
    - Whether this should be two separate instructions (ROWMASK/COLMASK)
    - Default behavior (all-ones? sticky from previous?)
    - Bit width encoding for different array sizes
    - Whether column mask affects all corelets or per-corelet

    Alternative considered: separate CIM.ROWMASK and CIM.COLMASK instructions
    """
    pass


@cocotb.test()
async def test_cim_cmd(dut):
    """Test CIM.CMD - Command/control register configuration

    Sets up the operational mode, precision, and corelet selection for CIM operations.
    Replaces MNEMOSENSE's "FS" (Function Select) with more comprehensive control.

    Format: CIM.CMD <config_bits>
      Proposed 8-bit encoding:
        [7:6] = operation mode (00=WRITE, 01=FWD, 10=BWD, 11=REC)
        [5:4] = corelet_mode (00=SINGLE, 01=ROW, 10=COL, 11=ALL)
        [3:2] = precision (00=1b, 01=2b, 10=4b, 11=8b)
        [1:0] = corelet_id or recur_mode_bits

    Operation Modes:
      00 (WRITE): Program memristor weights
      01 (FWD):   Forward pass  - Input on BL → Output on SL
      10 (BWD):   Backward pass - Input on SL → Output on BL
      11 (REC):   Recurrent     - Input on BL → Output on BL (feedback)

    Precision (SAR ADC cycles during SAMPLE):
      00: 1-bit (1 cycle)  - sign only
      01: 2-bit (2 cycles)
      10: 4-bit (4 cycles)
      11: 8-bit (8 cycles)

    Unknowns:
    - Exact bit allocation in 8-bit immediate
    - How to specify recurrent iteration count (separate CIM.RCFG instruction?)
    - Whether corelet selection belongs here or in separate instruction
    - Default values when not explicitly set
    - Whether we need extended config for >8 bits of control

    Recurrent mode needs iteration count for MMM:
      CIM.RCFG 16         # 16 iterations (separate instruction?)
      CIM.CMD 0b11_11_10  # REC mode, ALL corelets, 4-bit precision

    Example:
      CIM.CMD 0b01_11_10_00  # FWD, ALL corelets, 4-bit, [1:0] unused
    """
    pass


@cocotb.test()
async def test_cim_pulse(dut):
    """Test CIM.PULSE - Execute array operation

    Trigger instruction that executes the operation configured by CIM.CMD.
    No operands - uses current state of all control registers.
    Replaces MNEMOSENSE's "DoA" (Do Array).

    Format: CIM.PULSE (no operands)

    Behavior:
      - WRITE mode: Programs memristors using SMASK + SWT data
      - FWD/BWD/REC: Executes MVM using PMASK row/col selection
      - Variable latency depending on mode and array size
      - May execute multiple iterations in REC mode (set by RCFG)
      - Blocking or non-blocking? (TBD)

    Unknowns:
    - Should this be blocking or non-blocking by default?
    - Do we need CIM.PULSE.NB (non-blocking variant)?
    - How to signal completion (status register polling? interrupt?)
    - Behavior when called with incomplete configuration
    - Whether recurrence iterations all happen in one PULSE or need multiple

    Timing:
      - Write: ~?μs per row (memristor programming time)
      - Compute: ~20ns per MVM (analog speed)
      - Recurrent: (single MVM time) * (iteration count)

    Example sequence:
      CIM.PMASK x5, 0xFFFF
      CIM.CMD 0b01_11_10_00  # FWD, ALL, 4-bit
      CIM.PULSE              # Execute, blocks until done
      CIM.SAMPLE x6          # Read result
    """
    pass


@cocotb.test()
async def test_cim_sample(dut):
    """Test CIM.SAMPLE - ADC sample and read operation

    Triggers SAR ADC sampling and reads result into destination register.
    Replaces MNEMOSENSE's "DoS" (Do Sample) + read operations.
    Precision (1-8 SAR cycles) is set by CIM.CMD, not here.

    Format: CIM.SAMPLE <dest>
      dest: destination register for result (rd)
            OR memory-mapped auto-write? (TBD)

    Behavior:
      - Initiates sample-and-hold of analog array outputs
      - Runs SAR ADC for N cycles (N = precision from CIM.CMD)
      - Converts analog voltages to digital values
      - Writes result to destination
      - Variable latency: 1-8 cycles based on precision

    Unknowns:
    - Should destination be a register or memory-mapped location?
    - Does it read one column, all columns, or columns specified by CMASK?
    - Is this blocking or returns immediately with async completion?
    - How to handle multiple columns (iterate? parallel? auto-increment?)
    - Whether result format is signed/unsigned, how many bits wide
    - Do we need column iteration (like MNEMOSENSE CS + DoR loop)?

    Precision from CMD affects SAR cycles:
      1-bit: 1 cycle  (just sign)
      2-bit: 2 cycles
      4-bit: 4 cycles
      8-bit: 8 cycles

    Possibly use auto-write to memory map (no dest register operand) or to fixed result register

    Example:
      CIM.CMD 0b01_11_10_00  # 4-bit precision
      CIM.PULSE
      CIM.SAMPLE x6          # 4 SAR cycles, result in x6
    """
    pass
