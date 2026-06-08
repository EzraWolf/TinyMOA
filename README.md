# TinyMOA

open-source LLM inference SoC with custom Language Processing Unit (LPU).

target metrics
- \>30 tok/s, 32K window LLaMA 3.2 8B Q4
- \>100 TOPS/W @ INT/FP8 (~12x NVIDIA H100 SXM @ 8.4 TOPS/W)

target specs
- OoO RISC-V CPU (`RV32I` or `RV64I`)
- 4MB CIM, 8GB GDDR6
- baseline CPU ISA `RV32I` or `RV64I`
- optional CPU ISA `MAFDCZbb_Zcb_Zicsr_Zifencei_Zicond_Zfbfmin`
- BMX8 (block-mixed-FP8: E4M3, block=32)

## project structure

WIP

## quickstart

FPGA/ASIC targets not ready. public release must use verilator.

```bash
veryl build

# run all tests
cd hardware/tests
uv run test.py

# run specific test
uv run test.py -k test_cpu_alu
```

## acknowledgements

BMX8 is named after SplineDrive who made the KianV linux SoC, a key inspiration for TinyMOA. he rides BMX.
