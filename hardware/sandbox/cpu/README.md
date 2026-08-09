# RISC-V CPU Sandbox

Cycle-accurate in-order model of `ecore` (README phase CPU #1).

```bash
uv sync --all-packages
uv run pytest hardware/sandbox/cpu/tests -q
uv run pytest -k test_ecore_top_fibonacci -q   # live lockstep vs Verilator RTL
```

Fibonacci (`mem[0x100] == 55`) matches `ecore_top` in both result and cycle count.
