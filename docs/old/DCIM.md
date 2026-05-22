# DCIM Core

> Based on: "DIMC: 2219TOPS/W 2569F^2/b Digital In-Memory Computing Macro in 28nm Based on Approximate Arithmetic Hardware" (ISSCC 2022, Wang et al.). We implement DIMC-D (double-approximate) scaled to 32x32 in IHP SG13G2 130nm using standard cells only -- no custom 12T FAs, no custom bitcells.

## Overview

The DCIM is a 32x32 all-digital crossbar that computes a binary-weight matrix-vector multiply (MVM) in one cycle per activation bit-plane. Weights are 1-bit (+/-1), stored in flip-flop registers inside the DCIM, pre-loaded from TCM. Activations are multi-bit, fed bit-serially (one bit-plane per cycle). All digital -- no ADC, no analog sense amps, no custom-drawn cells.

CPU interaction: write weights and activations to TCM, configure 6 MMIO registers, fire START, poll STATUS.DONE, read results from TCM.

## Paper vs Our Implementation

The paper builds a 256x64 macro in 28nm with custom 12T pass-gate full adders and custom SRAM bitcells. We differ as follows:

| | Paper (DIMC-D, 28nm) | TinyMOA DCIM (IHP 130nm) |
|---|---|---|
| Array size | 256 rows x 64 columns | 32 rows x 32 columns |
| Full adder | Custom 12T pass-gate FA (2250 F^2) | Standard-cell FA (synthesized) |
| Weight storage | Custom 6T SRAM bitcell | Flip-flop registers (1024 FFs, loaded from TCM) |
| Compressors per column | 16 x 16-input -> 3-bit each | 2 x 16-input -> 3-bit each |
| Adder tree | 16-input (sums 16 compressor outputs) | 2-input (sums 2 compressor outputs) |
| Compressor type | Double-approximate (AND/OR tree) | Double-approximate (AND/OR tree) |

The 12T FA and custom bitcell are physical design optimizations; they do not affect datapath logic. Our standard-cell version has identical functionality.

## Weight Storage: Flip-Flop Cache

There are **no intermediate buffers** between TCM and the DCIM compute array. The `weight_reg[col]` registers are the compute storage. During LOAD_WEIGHTS, the DCIM reads from TCM Port B and latches each word into column weight registers (with a runtime transpose). During COMPUTE, the XNOR gates read directly from `weight_reg`.

Each column has one 32-bit register (`weight_reg[col]`), where bit `[row]` holds the weight for that row-column intersection. Total: 32 columns x 32 bits = 1024 FFs.

Runtime transpose during LOAD_WEIGHTS: TCM stores weights row-major (one 32-bit word per row, bit[col] = W[row][col]). The DCIM needs weights column-major for the XNOR. The FSM reads one row-word at a time and distributes each bit to its column: `weight_reg[col][row_idx] = sram_rdata[col]`. After 32 reads, the transpose is complete.

## Column Datapath

Each of the 32 columns has this datapath:

```
                    32 weight bits (weight_reg[col], local FFs)
                           │
                    32 act bits (act_slice, 1-bit per row, current bit-plane)
                           │
                    ┌──────▼──────┐
                    │  32x XNOR   │  <- xnor_out[col] = ~(weight_reg[col] ^ act_slice)
                    │  (bitwise)  │     32 bits: 1 = match (+1), 0 = mismatch (-1)
                    └──────┬──────┘
                           │ 32 bits
                    ┌──────▼──────┐
              ┌─────┤  Split 2x16 ├─────┐
              │     └─────────────┘     │
         bits [0:15]              bits [16:31]
     ┌────────▼────────┐      ┌────────▼────────┐
     │  Compressor A   │      │  Compressor B   │
     │  16-input -> 3b │      │  16-input -> 3b │
     │  (double-approx)│      │  (double-approx)│
     └────────┬────────┘      └────────┬────────┘
           3 bits                   3 bits
              └────────┬───────────┘
                  ┌────▼────┐
                  │  Adder  │  <- popcount[col] = compA + compB
                  │  (4-bit)│     Range: 0-8 (approx, max 2x4)
                  └────┬────┘
                       │
                  ┌────▼──────────────┐
                  │ Shift Accumulate   │  <- shift_acc[col] = (shift_acc[col] << 1) + popcount[col]
                  │ (11-bit register)  │     Updated once per bit-plane
                  └────────────────────┘
```

### XNOR Multiply

For each column, all 32 rows simultaneously:
```verilog
assign xnor_out[col] = ~(weight_reg[col] ^ act_slice);
```
In MB-XNOR encoding, output 1 means the weight and activation bits agree (+1 x +1 or -1 x -1 = +1). Output 0 means they disagree (= -1). Single-gate-delay bitwise operation.

### Compressor (16-input Double-Approximate Popcount)

The compressor counts the number of 1s in a 16-bit input. We use the paper's double-approximate design, implemented as `tinymoa_compressor` in `ABC/src/dcim/compressor.v`.

16 inputs per compressor is the paper's design point. 16 inputs produce 8 AND/OR pairs at level 1, giving enough pairs for error cancellation. The grouping size does not change with array dimension -- what changes is the number of compressors: `ceil(rows / 16)`. For our 32-row array: 2 compressors per column.

Double-approximate compressor circuit (16:3 counter):

```
Level 1 (approximate): 8 pairs, alternating AND/OR
  L1[0] = in[0]  & in[1]      <- AND: outputs 1 only if both 1
  L1[1] = in[2]  | in[3]      <- OR:  outputs 1 if either 1
  L1[2] = in[4]  & in[5]
  L1[3] = in[6]  | in[7]
  L1[4] = in[8]  & in[9]
  L1[5] = in[10] | in[11]
  L1[6] = in[12] & in[13]
  L1[7] = in[14] | in[15]
  -> 8 single bits (vs 8 two-bit values from exact half-adders)

Level 2 (approximate): 4 pairs, alternating AND/OR
  L2[0] = L1[0] & L1[1]
  L2[1] = L1[2] | L1[3]
  L2[2] = L1[4] & L1[5]
  L2[3] = L1[6] | L1[7]
  -> 4 single bits

Level 3 (exact): standard popcount of 4 bits
  result = L2[0] + L2[1] + L2[2] + L2[3]
  -> 3-bit output (range 0-4)
```

Each approximate level eliminates the carry chain, dropping 1 output bit. Two approximate levels reduce a 5-bit exact popcount to 3 bits. The paper reports **55% fewer transistors** than exact and a **worst-case RMSE of 6.76%** (vs 22.5% for analog IMC).

Why errors partially cancel: an AND gate on a pair of uniform random bits has E[output] = 0.25 (true pair-count mean = 1.0), underestimating by 0.75. An OR gate has E[output] = 0.75, overestimating by 0.25. Across many alternating AND/OR pairs, the biases tend to cancel, especially with approximation-aware training.

Exact compressor (16:5 counter, for verification): standard popcount tree. In Verilog, sum all bits -- synthesis builds an FA tree. Output: 5 bits (range 0-16). Enabled with `ifdef EXACT_COMPRESSOR` for golden-model verification. The Verilog module always outputs 5 bits; in approximate mode the top 2 bits are zero.

### Adder Tree

Sums the two per-column compressor outputs:

- Paper (256-input, 16 compressors): 16-input adder tree using custom 12T RCA FAs. Sums 16 x 3-bit values -> 7-bit popcount.
- Our 32-input, 2 compressors: single addition: `popcount[col] = compA + compB`. Max = 4 + 4 = 8, fits in 4 bits.
- Exact mode: compA + compB, max = 16 + 16 = 32, fits in 6 bits.

### Shift Accumulator

11-bit register per column. After each bit-plane's popcount, the accumulator shifts left and adds:

```verilog
shift_acc[col] <= (shift_acc[col] << 1) + popcount[col];
```

The FSM processes bit-planes from MSB to LSB (bit_plane counts down from P-1 to 0). This gives the MSB popcount the highest positional weight. After P bit-planes, the accumulator holds the unsigned popcount-domain dot product.

Width justification (11 bits):
- 32-input double-approx max per cycle: 8. At 4-bit precision: 8 x (1+2+4+8) = 120, needs 7 bits.
- 32-input exact max per cycle: 32. At 4-bit: 32 x 15 = 480, needs 9 bits.
- 11 bits provides headroom for exact mode and future scaling.

### Popcount-to-Signed Conversion

The raw accumulator is an unsigned popcount-domain result. The CPU converts to the true signed MB-XNOR dot product after reading results from TCM:

```
dot_product_signed = 2 * shift_acc[col] - N * (2^P - 1)
```

where N = array dimension (32), P = activation precision (number of bit-planes). This subtraction runs in software -- the DCIM stores only the raw unsigned accumulator, avoiding signed arithmetic and subtractors in the datapath.

Example (1-bit, N=32): popcount = 20 means 20 of 32 XNORs matched. Signed = 2x20 - 32x(2^1 - 1) = 40 - 32 = +8.

Example (4-bit, N=32): accumulator = 300. Signed = 2x300 - 32x(2^4 - 1) = 600 - 480 = +120.

## MB-XNOR Number Format

### Conventional Binary vs MB-XNOR

In standard 2's complement, binary weights are w in {-1, 0}. Having w=0 destroys information (any activation x 0 = 0) and degrades CNN accuracy.

MB-XNOR solves this: each activation bit b_i is in {+1, -1} instead of {0, 1}. An N-bit activation value is:
```
a = sum(b_i * 2^i)    where b_i in {+1, -1},  i = 0..P-1
```

Weight encoding: binary 1 -> +1, binary 0 -> -1.

Multiply via XNOR: `w * b_i = XNOR(w_bit, a_bit)`. Same sign -> 1 (+1), different -> 0 (-1).

This format **cannot represent zero** -- all bit-planes contribute +/-1 weighted by powers of 2. Activation functions that produce zero (like ReLU) are incompatible. Use tanh or leaky ReLU instead.

### Bit-Plane Storage in TCM

The CPU pre-transposes activations into bit-planar format before writing to TCM. For P-bit precision with 32 activations:

| TCM Address | Contents |
|---|---|
| `act_base + 0` | Bit-plane 0 (LSB): bit[row] = activation[row]'s bit 0 |
| `act_base + 1` | Bit-plane 1: bit[row] = activation[row]'s bit 1 |
| ... | ... |
| `act_base + P-1` | Bit-plane P-1 (MSB): bit[row] = activation[row]'s MSB |

Each word is 32 bits -- one bit per row. The DCIM reads one word per FETCH_ACT, loaded directly into `act_slice`. The FSM processes MSB first (bit_plane = P-1, descending to 0) so the shift-accumulate produces correctly weighted results.

### Approximation-Aware Training

The double-approximate compressor introduces bounded, deterministic error. Conventional training yields only 25.2% accuracy on CIFAR-10 with double-approx hardware. Approximation-aware training -- where the PyTorch forward pass simulates the AND/OR gate behavior bitwise -- recovers accuracy to 86.96% (vs 89.6% exact). This training happens offline; the hardware is unchanged.

## 8-Bit Precision

The design supports 1, 2, and 4-bit activation precision. Extending to 8-bit requires widening `ACC_WIDTH` from 11 to 14 bits (exact-mode max at 8-bit: 32 x 255 = 8160) and adding a 4th bit to `cfg_precision`.

The paper warns against this for the double-approximate compressor: MSBs carry weight 2^7 = 128, so the compressor's ~6.76% RMSE produces large absolute errors on high bit-planes. The paper reports acceptable accuracy only at 1-bit activations with DIMC-D; for >=4-bit, it recommends single-approximate or exact compressors.

Other costs: 8 FETCH+COMPUTE cycles instead of 4 (2x longer), 96 extra accumulator FFs (3 bits x 32 columns), 8 TCM activation words instead of 4.

Recommendation: ship 1/2/4-bit for the initial tape-out. If 8-bit proves necessary, bump `ACC_WIDTH` and `cfg_precision` width -- parameter changes, not structural redesigns.

## Physical Design: Hardening as a Macro

The DCIM should be hardened as a fixed rectangular block in the OpenLane floorplan, separate from the CPU. This keeps the MAC tree (XNOR -> compressor -> adder -> accumulator) physically compact, prevents the placer from interleaving CPU and DCIM logic, and produces a clean die photo.

### OpenLane Macro Flow

To harden `tinymoa_dcim_core` as a standalone macro:

1. Create a separate OpenLane config directory (e.g., `openlane/tinymoa_dcim/config.json`).
2. Set `DESIGN_NAME` to `tinymoa_dcim_core`. Include both `dcim.v` and `compressor.v` in `VERILOG_FILES`.
3. Set `FP_SIZING` to `absolute` and specify `DIE_AREA` to force a rectangular shape. Start with a rough estimate (see Area Estimate below) and adjust after first synthesis.
4. Pin placement (`FP_PIN_ORDER_CFG`):
   - Left edge: MMIO ports (mmio_addr, mmio_wdata, mmio_rdata, mmio_read, mmio_write, mmio_ready) -- these face the CPU.
   - Top edge: SRAM ports (sram_addr, sram_rdata, sram_wdata, sram_wen, sram_ren) -- these face the TCM macro.
   - Bottom edge: clk, nrst.
5. Run the full OpenLane flow (synthesis -> floorplan -> placement -> CTS -> routing -> finishing). Output: GDS + LEF for the macro.
6. Verify timing closure at the target frequency. The critical path is XNOR -> compressor -> adder -> accumulator, all in one clock cycle.

### Top-Level Integration

In the top-level `tinymoa_top` OpenLane config:

1. Add the DCIM macro's GDS and LEF to `EXTRA_GDS_FILES` and `EXTRA_LEFS`.
2. Place the macro in the floorplan using `MACRO_PLACEMENT_CFG`. Position it adjacent to the TCM SRAM macro for short SRAM port routing.
3. The top-level flow routes the CPU bus, TCM Port B, and MMIO wires to the DCIM macro pins.

### Sub-Hardening the Compressor Bank

If the DCIM macro is too large for clean placement, or if you want the compressor tree to appear as a distinct block in the die photo, harden `tinymoa_compressor` as a leaf macro. Each column instantiates two compressors; the 64 instances would be pre-placed within the DCIM. This is optional -- the main benefit is visual clarity and tighter control of the critical timing path.

### Area Estimate

Rough gate counts for 32x32:
- XNOR array: 1024 XNOR2 gates
- Weight FFs: 1024 DFFs
- Compressor bank: 64 compressors x ~12 gates = ~768 gates
- Adder tree: 32 x 4-bit adder = ~128 gates
- Accumulators: 32 x 11-bit registers = 352 DFFs + increment logic
- FSM + MMIO: ~200 gates
- Total: ~3000-4000 gate equivalents

At IHP SG13G2 130nm standard-cell density, expect the macro to be roughly 200-400 um per side. Run a quick synthesis + floorplan to get an accurate number before committing to a die area.

## Performance Estimation (50 MHz, 130nm)

### Raw Throughput (GOPS)

Each COMPUTE cycle processes 32 x 32 = 1024 binary MACs (all columns, all rows, one XNOR + one popcount contribution).

| Mode | Bit-planes | Total MACs | Cycles (no reload) | Cycles (with reload) | GOPS @ 50 MHz (no reload) | GOPS @ 50 MHz (with reload) |
|------|-----------|-----------|-------------------|---------------------|---------------------------|----------------------------|
| 1-bit | 1 | 1024 | ~38 | ~102 | 1.35 | 0.50 |
| 2-bit | 2 | 2048 | ~41 | ~105 | 2.50 | 0.98 |
| 4-bit | 4 | 4096 | ~47 | ~111 | 4.36 | 1.85 |

Cycle breakdown (no reload): FETCH_ACT (2/plane) + COMPUTE (1/plane) + STORE_RESULT (32) + overhead (~3).

### Energy Efficiency Estimate (GOPS/W)

Scaling from the paper's measured results is approximate:

Paper reference: DIMC-D at 28nm, 0.9V, 752 MHz achieves ~12 TOPS throughput at ~5.5 mW -> 2219 TOPS/W.

Scaling factors (130nm vs 28nm):
- Gate capacitance: ~4.6x larger (scales with feature size)
- Supply voltage: ~1.2V vs ~0.9V -> V^2 ratio ~1.78x
- Combined per-gate-per-Hz power: ~8x higher than 28nm
- Array size: 1/16 of paper (1024 vs 16384 MACs)
- Frequency: 1/15 of paper (50 vs 752 MHz)

Estimated DCIM power at 50 MHz, 1.2V: rough scaling gives ~0.2 mW for the datapath alone. With FSM, MMIO, clock tree, and routing overhead: 0.5-2 mW (broad estimate).

| Mode | GOPS (no reload) | Power estimate | GOPS/W | TOPS/W |
|------|-----------------|---------------|--------|--------|
| 1-bit | 1.35 | 0.5-2 mW | 675-2700 | 0.7-2.7 |
| 4-bit | 4.36 | 1-3 mW | 1450-4360 | 1.5-4.4 |

These are back-of-envelope estimates with +/-5x uncertainty. Even the pessimistic end (~0.7 TOPS/W) is competitive for a 130nm academic design. Actual numbers require post-synthesis power analysis.

Context: paper (28nm custom) = 2219 TOPS/W. Our estimate (130nm std-cell) = 0.7-4.4 TOPS/W. Typical 130nm digital accelerator = 0.1-10 TOPS/W.

## CPU Interface

From the CPU's perspective, the DCIM is 6 memory-mapped registers at `0x400000` (via `tp`) plus three TCM regions accessed with normal load/store instructions.

### Memory Map

```
┌─────────────────────────────────────┐
│ TCM (0x000000 - 0x0007FF)           │
│   0x000680 - 0x0006FF: Weights      │ <- CPU writes here (Port A)
│   0x000700 - 0x00073F: Activations  │ <- CPU writes here (Port A)
│   0x000780 - 0x0007FF: Results      │ <- CPU reads here (Port A)
├─────────────────────────────────────┤
│ DCIM MMIO (0x400000 - 0x400017)     │
│   0x400000: CTRL                    │ <- START, precision, reload
│   0x400004: STATUS                  │ <- BUSY/DONE
│   0x400008: WEIGHT_BASE             │ <- TCM word addr
│   0x40000C: ACT_BASE                │
│   0x400010: RESULT_BASE             │
│   0x400014: ARRAY_SIZE              │
└─────────────────────────────────────┘
```

The CPU writes weight and activation data to TCM via Port A. It configures and starts the DCIM via MMIO. The DCIM reads weights/activations from TCM Port B (no bus contention with CPU Port A) and writes results back via Port B. The CPU reads results via normal `lw` after polling STATUS.DONE.

The CPU must not write to the weight/activation/result TCM regions while STATUS.BUSY is set. Port A and Port B access the same SRAM -- concurrent writes to the same address are undefined.

### Example C Program (Pseudo-Code)

```c
#include <stdint.h>

// MMIO registers (via tp = 0x400000)
#define DCIM_CTRL         (*(volatile uint32_t *)0x400000)
#define DCIM_STATUS       (*(volatile uint32_t *)0x400004)
#define DCIM_WEIGHT_BASE  (*(volatile uint32_t *)0x400008)
#define DCIM_ACT_BASE     (*(volatile uint32_t *)0x40000C)
#define DCIM_RESULT_BASE  (*(volatile uint32_t *)0x400010)
#define DCIM_ARRAY_SIZE   (*(volatile uint32_t *)0x400014)

// TCM regions (byte addresses for CPU, word addresses for DCIM config)
#define WEIGHT_TCM  ((volatile uint32_t *)0x000680)  // word addr 0x1A0
#define ACT_TCM     ((volatile uint32_t *)0x000700)  // word addr 0x1C0
#define RESULT_TCM  ((volatile uint32_t *)0x000780)  // word addr 0x1E0

#define N 32  // array dimension

// Write 32x32 weight matrix to TCM (row-major, bit[col] = W[row][col])
void dcim_load_weights(const uint32_t weights[N]) {
    for (int row = 0; row < N; row++)
        WEIGHT_TCM[row] = weights[row];
}

// Write activations in bit-planar format (one word per bit-plane)
void dcim_load_activations(const uint32_t act_planes[], int precision) {
    for (int p = 0; p < precision; p++)
        ACT_TCM[p] = act_planes[p];
}

// Run one MVM inference
void dcim_run(int precision, int reload_weights) {
    DCIM_WEIGHT_BASE = 0x1A0;   // TCM word address of weights
    DCIM_ACT_BASE    = 0x1C0;   // TCM word address of activations
    DCIM_RESULT_BASE = 0x1E0;   // TCM word address for results
    DCIM_ARRAY_SIZE  = N;

    // START=1, precision in bits [3:1], reload in bit [4]
    DCIM_CTRL = (reload_weights << 4) | (precision << 1) | 1;

    // Poll until done
    while (!(DCIM_STATUS & 0x2))
        ;  // spin on STATUS.DONE
}

// Read results and convert from popcount-domain to signed
void dcim_read_results(int32_t output[N], int precision) {
    int bias = N * ((1 << precision) - 1);
    for (int col = 0; col < N; col++)
        output[col] = 2 * (int32_t)RESULT_TCM[col] - bias;
}

// --- Example usage ---
void run_inference(void) {
    uint32_t weights[N];    // W[row] packed as 32-bit word
    uint32_t act_planes[4]; // 4-bit precision = 4 bit-planes
    int32_t  output[N];

    // ... fill weights and act_planes from model ...

    dcim_load_weights(weights);
    dcim_load_activations(act_planes, 4);
    dcim_run(4, 1);  // 4-bit precision, reload weights
    dcim_read_results(output, 4);

    // output[] now contains signed dot products
}
```

## MMIO Register Map (base `0x400000`, via `tp`)

| Offset | Name | Bits | R/W | Description |
|--------|------|------|-----|-------------|
| `0x00` | CTRL | [0] START, [3:1] ACT_PRECISION, [4] RELOAD_WEIGHTS | R/W | START self-clears when FSM leaves IDLE |
| `0x04` | STATUS | [0] BUSY, [1] DONE | R | BUSY=1 during operation, DONE=1 on completion |
| `0x08` | WEIGHT_BASE | [9:0] | R/W | TCM word address of weight row 0. Default: `0x1A0` |
| `0x0C` | ACT_BASE | [9:0] | R/W | TCM word address of activation bit-plane 0. Default: `0x1C0` |
| `0x10` | RESULT_BASE | [9:0] | R/W | TCM word address for result column 0. Default: `0x1E0` |
| `0x14` | ARRAY_SIZE | [5:0] | R/W | Active dimension N (1-32). Default: 32 |

## Finite State Machine

```
IDLE --(START)--> LOAD_WEIGHTS --> FETCH_ACT --> COMPUTE --> STORE_RESULT --> DONE --> IDLE
                                       ^              |
                                       +-- more bits --+
```

### State Details

| State | TCM Port B | Cycles | Action |
|-------|-----------|--------|--------|
| IDLE | -- | 1 | Wait for CTRL.START. Clear accumulators. Set bit_plane = cfg_precision - 1. Branch to LOAD_WEIGHTS or FETCH_ACT |
| LOAD_WEIGHTS | Read | 2 x N | For each row: assert sram_ren, addr = weight_base + row_idx. Next cycle: latch sram_rdata, distribute bits to weight_reg columns (transpose). 2 cycles per row |
| FETCH_ACT | Read | 2 | Assert sram_ren, addr = act_base + bit_plane. Next cycle: act_slice = sram_rdata |
| COMPUTE | -- | 1 | XNOR is combinational. Compute popcount via compressor + adder. shift_acc[col] = (shift_acc[col] << 1) + popcount[col]. If bit_plane > 0: decrement, go to FETCH_ACT. Else: go to STORE_RESULT |
| STORE_RESULT | Write | N | For each col: sram_wdata = shift_acc[col], addr = result_base + col_idx. 1 cycle per column (reuses row_idx counter) |
| DONE | -- | 1 | Set STATUS = DONE (clear BUSY). Return to IDLE |

Bit-plane processing order: MSB first (bit_plane starts at P-1, decrements to 0). This ensures the shift-accumulate weights each bit-plane correctly: MSB gets weight 2^(P-1), LSB gets weight 2^0.

### Total Cycle Counts

| Scenario | Formula | 1-bit | 4-bit |
|----------|---------|-------|-------|
| With weight reload | 2N + 3P + N + 3 | 64 + 3 + 32 + 3 = 102 | 64 + 12 + 32 + 3 = 111 |
| Without reload | 3P + N + 3 | 3 + 32 + 3 = 38 | 12 + 32 + 3 = 47 |

## Precision Modes

| Mode | Bit-planes (P) | FETCH+COMPUTE cycles | Paper recommendation |
|------|---------------|---------------------|---------------------|
| 1-bit | 1 | 3 | DIMC-D preferred (best accuracy: 86.96%) |
| 2-bit | 2 | 6 | DIMC-D acceptable with approx-aware training |
| 4-bit | 4 | 12 | Paper recommends DIMC-S (single-approx) for >=4-bit |

Set via CTRL.ACT_PRECISION[3:1].

## Scaling to 64x64

| Parameter | 32x32 | 64x64 |
|---|---|---|
| Weight flip-flops | 1024 | 4096 |
| Compressors per column | 2 x 16-input | 4 x 16-input |
| Adder tree inputs | 2 | 4 |
| Popcount bits (double-approx) | 4 | 5 |
| Shift accumulator width | 11 bits | 13 bits |
| TCM weight words | 32 | 64 |
| TCM activation words/plane | 1 (32 bits) | 2 (64 bits, needs 2 reads) |
| TCM result words | 32 | 64 |
| LOAD_WEIGHTS cycles | 64 | 128 |

## Verification

- Python golden model: NumPy MB-XNOR MVM with both exact and double-approx compressor simulation
- Cocotb testbench: randomized 32x32 weight/activation matrices, compare against golden model
- RMSE threshold: auto-fail if > 7% over 10,000 random vectors (double-approx target: 6.76%)
- Exact mode: verify zero RMSE with `ifdef EXACT_COMPRESSOR`
- Bit-plane sweep: verify 1, 2, 4-bit precision modes produce correctly weighted accumulation
- Known-pattern tests: identity weights (output = activation), all-ones weights (output = popcount of activation)
