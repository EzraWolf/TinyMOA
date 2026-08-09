# RISC-V CPU Sandbox

Cycle-accurate in-order model of `ecore` (README phase CPU #1).

Layout mirrors the RTL:
- `encode.py` — sandbox-owned instruction encoder (programs built from this)
- `isa.py` / `alu.py` / `bru.py` / `lsu.py` / `regfile.py` — leaf units
- `mem.py` — IdealMem (always-ready imem/dmem; missing imem → `jal x0,0`)
- `top.py` — `ecore_top` wiring + NBA-style `step()` + CycleSample
- `arch.py` — non-pipelined ISS using the same leaf units
- `spike.py` — Spike retire-step compare (`SPIKE=/path/to/spike`)
- `lockstep.py` — retire + cycle-trace diff helpers
- `programs.py` — directed programs (fib, RAW, branch, LSU, E, W64)

```bash
uv sync --all-packages
export SPIKE=/path/to/spike   # optional; spike tests skip/fail without it
uv run pytest hardware/tests/unit/sandbox -q
uv run pytest -k 'test_ecore_top_fibonacci or test_ecore_cycle_lockstep' -q
```
