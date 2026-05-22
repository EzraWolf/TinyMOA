# TinyMOA Architecture

> RTL module structure, address map, pipeline, and interconnects. For the programmer model (registers, instructions), see [ISA.md](./ISA.md). For the DCIM accelerator, see [DCIM.md](./DCIM.md).

## Overview

TinyMOA is a nibble-serial RV32EC RISC-V CPU with a 32x32 Digital Compute-in-Memory (DCIM) accelerator, sharing a dual-port TCM SRAM. Targets IHP SG13G2 130nm via TinyTapeout IHP26a (8x2 tile layout).

Key design decisions:
1. **Nibble-serial pipelined execute** — register read, ALU, and register write overlap at 4 bits/cycle.
2. **Dual-port SRAM** — Port A: CPU, Port B: boot FSM then DCIM. No arbitration.
3. **DCIM via MMIO** — CPU configures DCIM via 6 registers at `0x400000`. Polling, no interrupts.

### Component Interconnect

| From | To | Via | Purpose |
|------|----|-----|---------|
| CPU | TCM | Port A (R/W) | Instruction fetch, data load/store |
| DCIM FSM | TCM | Port B (R/W) | Read weights + activations, write results |
| Boot FSM | TCM | Port A (W) | Copy flash → TCM on reset |
| Boot FSM | QSPI | Read | Fetch flash contents during boot |
| CPU | QSPI | R/W | Flash read, PSRAM access (after boot) |
| CPU | DCIM | MMIO (Port A) | Configure, start, poll status, read results |

## Address Map

### Global Address Map

| addr[23:22] | Byte Range | Target | Decode |
|-------------|------------|--------|--------|
| `00` | `0x000000 - 0x0007FF` | TCM (2 KB, 512x32) | `addr[23:11] == 0` |
| `00` | `0x000800 - 0x000FFF` | Reserved (future TCM) | — |
| `00` | `0x001000 - 0x3FFFFF` | QSPI Flash | `addr[23:22]==00 && !is_tcm` |
| `01` | `0x400000 - 0x400017` | DCIM MMIO (6 regs) | `addr[23:22] == 01` |
| `10` | `0x800000 - 0xBFFFFF` | QSPI PSRAM A | `addr[23:22] == 10` |
| `11` | `0xC00000 - 0xFFFFFF` | QSPI PSRAM B | `addr[23:22] == 11` |

Pseudo-hardcoded registers:
- `tp` = `0x400000` - DCIM MMIO base; all MMIO accesses use `tp`-relative addressing.
- `gp` = `0x000400` - TCM globals anchor; `gp`-relative loads/stores reach the full TCM range within the 12-bit signed offset window.

### Internal TCM Layout

A dual-port IHP pre-generated SRAM (512x32) macro is used as Tighly Coupled Memory (TCM) and is partitioned as follows:

| Word Addr       | Byte Addr       | Size              | Contents                                             |
|-----------------|-----------------|-------------------|------------------------------------------------------|
| `0x000 - 0x0FF` | `0x000 - 0x3FF` | 256 words (1 KB)  | Code                                                 |
| `0x100 - 0x17F` | `0x400 - 0x5FF` | 128 words (512 B) | Stack + globals (`gp` = byte `0x400` = word `0x100`) |
| `0x180 - 0x19F` | `0x600 - 0x67F` | 32 words (128 B)  | Reserved                                             |
| `0x1A0 - 0x1BF` | `0x680 - 0x6FF` | 32 words (128 B)  | DCIM weight matrix                                   |
| `0x1C0 - 0x1DF` | `0x700 - 0x77F` | 32 words (128 B)  | DCIM activation buffer                               |
| `0x1E0 - 0x1FF` | `0x780 - 0x7FF` | 32 words (128 B)  | DCIM result buffer                                   |

Stack pointer (`sp`) initialises to `0x5FC` (top of the stack+globals region) and grows downward.

`gp` at `0x400` gives `lw/sw gp, offset` access to globals across the full globals region with a signed 12-bit offset. 

DCIM default base addresses in `dcim.v` match this layout (`cfg_weight_base = 0x1A0`, `cfg_act_base = 0x1C0`, `cfg_result_base = 0x1E0`).

## Execution Pipeline

1. Fetch `IF`: 1 cycle if TCM, stall >8 cycles if QSPI
2. Decode `ID`: 1 cycle
3. Execute `EX`: 8 cycles (all ALU ops produce 32-bit results, so 8 nibbles always)
4. Writeback `WB`: 1 cycle (update flags and PC)
5. Memory `MEM`: 1 cycle if TCM, stall >8 cycles if QSPI (load/store only, wait for mem_ready)

Note: the ALU result is fully computed after 8 clock edges but requires 1 additional cycle for the final nibble's NBA to resolve before reading. Effectively 8+1 for external consumers.

Cycle counts (TCM):
- **RV32I ALU**: 1(F) + 1(D) + 8(E) + 1(W) = **11 cycles**
- **RV32C ALU**: 1(F) + 1(D) + 8(E) + 1(W) = **11 cycles**
- **Load/Store**: + MEM stall (1 cycle TCM, variable QSPI)
- **C.MUL**: 1(F) + 1(D) + ~12(E: 4 collect + 1 multiply + 8 shift out) + 1(W)
- **Shifts**: 1(F) + 1(D) + ~9(E: 1 read shamt + 8 shift) + 1(W)

ALU has 3 datapaths inside `alu.v`:
1. **Nibble-serial core**: ADD/SUB/AND/OR/XOR/SLT/SLTU/CZERO (carry-chained)
2. **Shifter**: SLL/SRL/SRA (needs shift amount first, then processes full value)
3. **Multiplier**: C.MUL: 16x16 signed → 32-bit (combinational, non-standard Zcb encoding)

## DCIM MMIO

6 registers at `0x400000` (accessible via `tp`-relative stores):

| Offset | Name | Description |
|--------|------|-------------|
| `0x00` | CTRL | [0] START, [3:1] ACT_PRECISION, [4] RELOAD_WEIGHTS |
| `0x04` | STATUS | [0] BUSY, [1] DONE |
| `0x08` | WEIGHT_BASE | [9:0] TCM word address of weight row 0 |
| `0x0C` | ACT_BASE | [9:0] TCM word address of activation word 0 |
| `0x10` | RESULT_BASE | [9:0] TCM word address for result writeback |
| `0x14` | ARRAY_SIZE | [5:0] N (array dimension, max 64) |

See [DCIM.md](./DCIM.md) for FSM details and full protocol.

## DCIM Module Overview (`dcim.v`)

`dcim_top` contains three independent always-sensitive blocks and one generate block:

**XNOR generate block (combinational)**
For each of the 32 columns, computes `xnor_out[col] = ~(weight_reg[col] ^ act_slice)`. This is a 32-wide XNOR between the stored weight column and the current 1-bit activation slice. Output is valid every cycle and consumed by the FSM during COMPUTE.

**MMIO block**
Handles CPU register-file transactions on the MMIO bus. Runs continuously alongside the FSM. On `mmio_write`, it decodes `mmio_addr[5:2]` and latches into the six `cfg_*` registers (`cfg_start`, `cfg_reload_weights`, `cfg_precision`, `cfg_weight_base`, `cfg_act_base`, `cfg_result_base`, `cfg_array_size`). On `mmio_read`, it muxes those same registers plus `status_reg` onto `mmio_rdata`. It also clears `cfg_start` once the FSM has left IDLE, so the CPU does not need to manually clear it.

**FSM block**
The compute state machine. Drives Port B of the TCM (`sram_addr`, `sram_ren`, `sram_wen`, `sram_wdata`) and steps through six states:

| State | Action |
|-------|--------|
| IDLE | Waits for `cfg_start`. Clears `shift_acc`. Branches to LOAD_WEIGHTS or FETCH_ACT based on `cfg_reload_weights`. |
| LOAD_WEIGHTS | Reads one TCM row per cycle (`cfg_weight_base + row_idx`). Each read distributes one bit to every column's `weight_reg`: `weight_reg[col][row_idx] = sram_rdata[col]`. Advances `row_idx` until `cfg_array_size` rows loaded. |
| FETCH_ACT | Reads one activation word from TCM (`cfg_act_base + word_idx`). Sets `act_slice` by extracting bit-plane `bit_plane` from each row word. Proceeds to COMPUTE. |
| COMPUTE | Clocks XNOR outputs (already combinational) into `shift_acc`: `shift_acc[col] <= (shift_acc[col] << 1) + popcount(xnor_out[col])`. Advances `bit_plane`; loops back to FETCH_ACT until `cfg_precision` planes done, then goes to STORE_RESULT. |
| STORE_RESULT | Writes `shift_acc[row_idx]` to TCM at `cfg_result_base + row_idx` for each column. After `cfg_array_size` writes, goes to DONE. |
| DONE | Sets `status_reg` to DONE, returns to IDLE. |

The two blocks (MMIO and FSM) are intentionally separate: the MMIO block must remain live at all times so the CPU can poll `STATUS` while the FSM is running.

## Module Hierarchy

```
ABC/src/
├── tinymoa.v      Top-level TinyTapeout wrapper (address decode, port muxing)
├── core.v         RV32EC CPU core (FSM, PC, IR, memory bus)
├── decoder.v      Combinational instruction decoder
├── alu.v          4-bit nibble-serial ALU + shifter + 16x16 multiplier
├── registers.v    16x32 register file (shift-register, nibble I/O)
├── counter.v      Nibble counter (0–7 for 32-bit, 0–3 for 16-bit)
├── tcm.v          IHP dual-port SRAM macro wrapper + simulation model
├── qspi.v         QSPI flash/PSRAM controller
├── bootloader.v   Boot FSM (flash → TCM loader)
└── dcim/
    ├── dcim.v         DCIM accelerator (crossbar + compressor + FSM)
    └── compressor.v   16-input approximate/exact popcount compressor
```
