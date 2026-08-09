# RISC-V CPU Sandbox

Cycle-accurate in-order model of `ecore` (README phase CPU #1).

Layout mirrors the RTL:
- `isa.py` / `alu.py` / `bru.py` / `lsu.py` / `regfile.py` — leaf units
- `top.py` — `ecore_top` wiring + NBA-style `step()`
- `arch.py` — non-pipelined ISS using the same leaf units
- `programs.py` — shared fibonacci image (encoding locked to `tests.common.encode_rv32i`)

```bash
uv sync --all-packages
uv run pytest hardware/sandbox/cpu/tests -q
uv run pytest -k test_ecore_top_fibonacci -q   # live lockstep vs Verilator RTL
```
