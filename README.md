# TinyMOA

LLM inference should be transparent and not require a datacenter. TinyMOA is a transformer accelerator that runs inference directly in memory.

a

a

a

a

a

a

a

a

a

## Quickstart

Insallation

```python
example program
```

## Architecture

### CPU Core

RV32EC, nibble-serial, 6-state pipeline:


### ISA

| Extension    | Notes |
|--------------|-------|
| RV32I (base) | Fully implemented |
| E (embedded) | 16 registers instead of 32 (x0–x15) |
| C (compresseD) / Zca | Full Q0, Q1, Q2 |
| Zcb    | Byte ops + C.MUL (16x16 -> 32-bit) |
| Zicond | Full: `czero.eqz`, `czero.nez` |
| Zicsr  | Not implemented |
| M (multiply) | Not implemented - opcodes reserved, C.MUL covers the common case |
| F (float) | Not implemented - opcodes reserved |

### DCIM Accelerator





A minimal RISC-V CPU with a Digital Compute-in-Memory (DCIM) accelerator for neural network inference. TinyMOA is built on a 4-bit nibble-serial datapath targeting IHP SG13G2 130nm via [TinyTapeout IHP26a](https://tinytapeout.com/).

The CPU is directly based on [TinyQV](https://github.com/MichaelBell/tinyQV) by [Michael Bell](https://github.com/MichaelBell), and while structurally overhauled to support DCIM and Tighly Coupled Memory (TCM), the serial 4-bit bus architecture, register file design, and pipeline structure are all his work. *TinyMOA would not exist without it.*
