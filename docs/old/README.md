<!-- PROPOSED SKELETON — headings only, content TBD after review -->

# TinyMOA Documentation

TinyMOA is a nibble-serial RV32EC RISC-V CPU with an on-chip Compute-in-Memory (CIM) accelerator, an SRAM TCM, and QSPI flash/PSRAM interfaces, targeting IHP SG13G2 @ 130nm via TinyTapeout shuttle IHP26a.

## Overview?
One paragraph: nibble-serial RV32EC CPU + DCIM accelerator, IHP SG13G2 130nm, TinyTapeout IHP26a shuttle.

Quick-reference table: ISA (RV32EC + Zcb + Zicond), datapath width (4-bit serial), SRAM size (up to 1024×32 dual-port), clock target, extensions implemented.

`High level architectural diagram (draw.io)`


## Core Documents

| Document | Purpose |
|----------|---------|
| [RV32EC Architecture](./Architecture.md) | System design: CPU, memory, address map, boot |
| [DCIM Architecture](./DCIM.md) | CIM accelerator design |
| [ISA Reference](./ISA.md) | RV32EC instruction set and extensions |
| [Bootloader](./Bootloader.md) | Physical bootloader FSM design and CPU start-up sequence|
| [TODO](./TODO.md) | All verification stages and work items |

## What's In, What's Out
Canonical extension status table: RV32I (full), E (16 regs), C/Zca (full Q0/Q1/Q2), Zcb (full, C.MUL uses custom opcode), Zicond - no Zicsr, no M, no F, no TinyQV custom, no RV64x, no RV128x.

|                      | Notes |
|----------------------|-------|
| RV32I base           | Full  |
| E (Embedded)         | x0-x15 registers only instead of x0-x31 |
| C (compressed) / Zca | Full Q0/Q1/Q2\* |
| Zcb                  | `c.lbu`, `c.lhu`, `c.lh`, `c.sb`, `c.sh`, `c.zext.b`, `c.sext.b`, `c.zext.h`, `c.sext.h`, `c.not`, `c.mul` |
| Zicond               | `czero.eqz`, `czero.nez` |
| F (floating-point)   | *Not implemented* - opcodes reserved for future use |
| RV64 / RV128         | *Not implemented* - RV32 only |

\* *We exclude (but reserve) all compressed FP operations since we are not using the RVF extension. However, [they are required if RVF or RVD extensions are used](https://docs.riscv.org/reference/isa/v20240411/unpriv/c-st-ext.html)*


## Pin Map
TinyTapeout pinout table ui_in/uo_out/uio_in/uio_out/uio_oe — QSPI pins, reset, debug output.

---
<!-- EXISTING CONTENT BELOW — preserved for reference -->

# TinyMOA Documentation

TinyMOA is a nibble-serial RV32EC RISC-V CPU with an on-chip Compute-in-Memory (CIM) accelerator, an SRAM TCM, and QSPI flash/PSRAM interfaces, targeting IHP SG13G2 @ 130nm via TinyTapeout shuttle `IHP26a`.



ISA Specification: 

## What's In, What's Out

| | Notes |
|-|-------|
| RV32I base | Full |
| E (Embedded) | x0-x15 registers only instead of x0-x31 |
| C (compressed) / Zca | Full Q0/Q1/Q2\* |
| Zcb | `c.lbu`, `c.lhu`, `c.lh`, `c.sb`, `c.sh`, `c.zext.b`, `c.sext.b`, `c.zext.h`, `c.sext.h`, `c.not`, `c.mul` |
| Zicond | `czero.eqz`, `czero.nez` |
| F (floating-point) | *Not implemented* - opcodes reserved for future use |
| RV64 / RV128 | *Not implemented* - RV32 only |

\* *We exclude (but reserve) all compressed FP operations since we are not using the RVF extension. However, [they are required if RVF or RVD extensions are used]()*

