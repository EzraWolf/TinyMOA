# TinyMOA Sandbox

Cycle-accurate models for quick testing.

- `cpu/` — in-order e-core (leaf units + `top.py` NBA step; see package README)
- `lpu/` — WIP

## Tooling (encode gates + Spike ELF)

Encode is gated against vendored `riscv-opcodes` match/mask **and** `llvm-mc` (hard-fail if missing). Spike payloads are assembled with `llvm-mc` + `ld.lld`.

```bash
brew install llvm lld
export LLVM_MC="$(brew --prefix llvm)/bin/llvm-mc"
export LD_LLD="$(brew --prefix lld)/bin/ld.lld"
export LLVM_OBJCOPY="$(brew --prefix llvm)/bin/llvm-objcopy"
export SPIKE=/path/to/spike   # optional; also searched on PATH
```
