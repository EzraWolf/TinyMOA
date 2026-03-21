"""
Test runner using cocotb_test - no Makefiles needed per unit.
Run with: `pytest test.py` or `uv run pytest test.py`
"""

import pytest
from pathlib import Path
from cocotb_test import simulator


def run_test(src_module, test_module, test_type="unit", dir=None, extra_sources=None):
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

    sources = (
        [str(src_path)]
        + [str(SRC_DIR / s) for s in (extra_sources or [])]
        + [str(tb_path)]
    )

    simulator.run(
        verilog_sources=sources,
        toplevel=toplevel,
        module=module,
        simulator="icarus",
        sim_build=str(SIM_BUILD / src_module),
        python_search=[str(PROJECT_DIR)],
    )


# Integration tests
# def test_main_design():
#     run_test("placeholder", "placeholder", test_type="integration")


def test_core():
    run_test(
        "core",
        "core",
        test_type="integration",
        extra_sources=[
            "decoder.v",
            "registers.v",
            "alu/alu.v",
            "alu/shifter.v",
            "alu/multiplier.v",
        ],
    )


# Unit tests
# ALU Unit Tests
def test_alu():
    run_test("alu", "alu", dir="alu")


def test_multiplier():
    run_test("multiplier", "multiplier", dir="alu")


def test_shifter():
    run_test("shifter", "shifter", dir="alu")


# Bootloader unit tests
def test_bootloader():
    run_test("bootloader", "bootloader")


# QSPI unit tests
def test_qspi_controller():
    run_test("qspi_controller", "qspi_controller")


# Register Unit Tests
def test_registers():
    run_test("registers", "registers")


# TCM unit tests
def test_tcm():
    run_test("tcm", "tcm")


def test_counter():
    run_test("counter", "counter")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
