# TinyMOA

LLM inference should be transparent and not require a datacenter. TinyMOA is a transformer accelerator that runs inference directly in memory.

## Quickstart

Insallation

```python
example program
```

## Architecture

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

### CPU Core

RV32EC, nibble-serial, 6-state pipeline:

### DCIM Accelerator
