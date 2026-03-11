# Generic Core Tests

Tests for `src/core_generic.v`, the "ideal" RV32EC nibble-serial CPU core with full 32-bit addressing. This module is not used by tinymoa.v

These tests instantiate the full CPU (decoder, register file, ALU, shifter, multiplier) against an ideal single-cycle memory. The testbench (`tb_core_generic.v`) provides a 256-word synchronous RAM loaded from a hex file via `$readmemh`.

## Programs

Generated in `test_core_generic.py` through the `rv32i_encode.py` and `rv32c_encode.py` helper functions.

| File | Description |
|------|-------------|
| `nops` | 8 NOPs to verify PC cycling |
| `addi_chain` | Chain of ADDI into x5, copy to x6 to verify read-after-write |
| `alu_basic` | ADDI to load x5=10, x6=3, then ADD/SUB/AND/OR/XOR into x7-x11 to verify R-type ALU ops |

## Registers

x0 is hardwired zero, x3 (gp) and x4 (tp) are hardcoded in the register file, so all test programs use x5-x15.
