# TinyMOA Test Suite

Test suite for the TinyMOA compute-in-memory processor using `cocotb`, `cocotb-test`, and `pytest`.

Note that we must cycle 8 times for every 32b operation since we run on a 4b datapath (1 nibble). This is why we use `nibble_counter`.

Major credit goes towards [TinyQV](https://github.com/MichaelBell/tinyQV/tree/858986b72975157ebf27042779b6caaed164c57b/test), which much of these tests are build on.

## Structure

```python
test/
├── integration/     # Full system-wide CPU tests (WIP)
├── unit/
│   ├── alu/         # ALU ops (add, sub, slt, sll)
│   ├── counter/     # Program counter (register)
│   ├── decoder/     # RV32I, RV32C, and custom instruction decoding
│   └── registers/   # Register file write and dual-port reading
```

## Running Tests

```bash
cd test
uv run pytest test.py
```

View waveforms with `gtkwave` or `surfer` on the generated `.fst` files in `test/sim_build/`.

## Dependencies

Install with `pyproject.toml` using `uv sync` (Python 3.12+, cocotb 2.0+, Icarus Verilog).
