"""
Test runner using cocotb_test - no Makefiles needed per unit.
Run with: `pytest test.py` or `uv run pytest test.py`
"""

import pytest
from pathlib import Path
from cocotb_test import simulator


def run_unit_test(src_module, test_module, test_type="unit", dir=None):
    """
    Run a standard cocotb unit test using pytest and cocotb-test.
    """
    PROJECT_DIR = Path(__file__).parent.resolve()
    SRC_DIR = PROJECT_DIR.parent / "src"
    SIM_BUILD = PROJECT_DIR / "sim_build"

    test_dir = dir or src_module

    src_path = SRC_DIR / (dir or "") / f"{src_module}.v"
    tb_path = PROJECT_DIR / test_type / test_dir / f"tb_{src_module}.v"
    module = f"{test_type}.{test_dir}.test_{test_module}"
    toplevel = f"tb_{src_module}"

    simulator.run(
        verilog_sources=[str(src_path), str(tb_path)],
        toplevel=toplevel,
        module=module,
        simulator="icarus",
        sim_build=str(SIM_BUILD / src_module),
        python_search=[str(PROJECT_DIR)],
    )


# ALU Unit Tests
def test_alu():
    run_unit_test("alu", "alu", dir="alu")


def test_multiplier():
    run_unit_test("multiplier", "multiplier", dir="alu")


def test_shifter():
    run_unit_test("shifter", "shifter", dir="alu")


# Decoder Unit Tests
def test_decoder_integration():
    run_unit_test("decoder", "decoder_integration")


def test_decoder_moa():
    run_unit_test("decoder", "decoder_moa")


def test_decoder_rv32c():
    run_unit_test("decoder", "decoder_rv32c")


def test_decoder_rv32i():
    run_unit_test("decoder", "decoder_rv32i")


# Register Unit Tests
def test_registers():
    run_unit_test("registers", "registers")


def test_counter():
    run_unit_test("counter", "counter")


# Integration tests (WIP)
def test_main_design():
    run_unit_test("placeholder", "placeholder", test_type="integration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
