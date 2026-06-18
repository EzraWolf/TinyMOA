<div align="center">
<picture>
    <!-- tinygrad README <3, but i've already been using the "tiny" prefix -->
  <source media="(prefers-color-scheme: dark)" srcset="docs/logo_dark.svg">
  <img alt="a" src="docs/logo_light.svg">
</picture>

LLMs are cool but the compute itself is closed-source

thus, (very early) open-source LLM inference SoC built from scratch

<h3>

[Docs](docs/)  |  [X](https://x.com/ezrwolf) (updates)  |  [Portfolio](https://terse.ink)

</h3>

<!--
[![GitHub Repo stars](https://img.shields.io/github/stars/ezrawolf/tinymoa)](https://github.com/ezrawolf/tinymoa/stargazers)
[![Unit Tests](#)](#)
[![Discord](#)](#)
-->

</div>

---

more precisely, a highly parameterized 4-way out-of-order RISC-V CPU that controls a Language Processing Unit (LPU). the LPU is an embedded transformer using Digital Compute-in-Memory (DCIM) for efficient general matrix-matrix (GEMM) and matrix-vector (GEMV) operations.

3x ASICs via [tinytapeout](https://tinytapeout.com) arriving Nov '26 for CPU and DCIM characterization.

## target metrics & specs

- \>30 tok/s, 32K window Llama 3.2 8B Q4
- \>100 TOPS/W on FP8 (~12x NVIDIA H100 SXM @ 8.4 TOPS/W)
- 4-way OoO RISC-V CPU (parameterized `RV32GC` or `RV64GC`)
- optional ISA `MAFDCZbb_Zcb_Zicsr_Zifencei_Zicond_Zfbfmin`
- CPU boots custom uLinux, runs ML models via [tinygrad](https://github.com/tinygrad/tinygrad) 
- LPU with ~1MB CIM, >4GB GDDR6 (if)
- precision: BMX8 (block-mixed-FP8, E4M3, block=32)
- 2D torous NoC inter-chip-interconnect (ICI) topology

# milestones

phase CPU
1. cycle-accurate model
2. in-order CPU RTL
3. OoO upgrade

phase LPU
1. tinygrad functional models (nanoGPT, LLaMA 3.2 both on MXFP8)
2. CPU/LPU memory map design
3. cycle-accurate model
4. CIM fabric
5. primitives (relu, div, sqrt, exp, norm)
6. sequencer
7. attention
8. end-to-end vs tinygrad golden reference

## architecture

*soon.*

## quick start

no FPGA/ASIC bring-up yet.

```bash
git clone https://github.com/ezrawolf/tinymoa.git
cd tinymoa

# build
uv sync
veryl build

# run all tests or individually
pytest -q --no-header --tb=short -n auto
pytest -q --no-header --tb=short -n auto -k test_cpu_alu
```

## project structure

```
docs/              (soon)
software/          (soon) custom tinygrad AoT compiler, runtime
firmware/          (soon) custom linux kernel, drivers, bootloader

hardware/rtl/      SoC home in Veryl
hardware/fpga/     FPGA targets for verification
hardware/tests/    pytest + cocotb testbenches
hardware/sandbox/  cycle-accurate python models
```
