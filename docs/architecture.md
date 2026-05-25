# TinyMOA Specs

- 64-bit RISC-V CPU (RV64IMAFCV + BF16)
- Hybrid VLIW frontend, OoO backend/retire (TBD)
- Configurable LPU datapath to support modified transformer architectures
- CIM cores use high count of tiny corelets to increase compute density and yield
- Corelets are 256x256, BFP8 (B=32), 4-bit exponent, CIM array computes 4-bit mantissa
- AoT compiler owns scheduling
- CPU dispatches to itself and LPU
- ICI managed by CPU (planned)

```
TinyMOA
├── RISC-V CPU
├── ICI Fabric (2D torus?)
├── Shared SRAM (ECC, AoT-managed)
└── LPU
     ├── Norm
     ├── RoPE
     ├── Softmax
     ├── VPU (vector processing unit)
     ├── SPU (scalar processing unit, ALU/FPU/format converter)
     ├── Local SRAM (ECC)
     ├── Feed Forward (dense/sparse)
     └── CIM Cores (dense/sparse)
          └── Corelets (256x256, BFP8, 4-bit mantissa, B=32)
```
