"""
Test runner using cocotb_test - no Makefiles needed per unit.
Run with: `pytest test.py` or `uv run pytest test.py`
"""

import pytest
from pathlib import Path
from cocotb_test import simulator

TEST_DIR = Path(__file__).parent.resolve()
SRC_DIR = f"{TEST_DIR.parent}/src"


def test_alu():
    simulator.run(
        verilog_sources=[
            f"{SRC_DIR}/cpu/alu.v",
            f"{TEST_DIR}/unit/alu/tb_alu.v",
        ],
        toplevel="tb_alu",
        module="unit.alu.test_alu",
        simulator="icarus",
        work_dir=f"{TEST_DIR}/sim_build/alu",
        python_search=[str(TEST_DIR)],
    )


def test_multiplier():
    simulator.run(
        verilog_sources=[
            f"{SRC_DIR}/cpu/alu.v",
            f"{TEST_DIR}/unit/alu/tb_multiplier.v",
        ],
        toplevel="tb_multiplier",
        module="unit.alu.test_multiplier",
        simulator="icarus",
        work_dir=f"{TEST_DIR}/sim_build/multiplier",
        python_search=[str(TEST_DIR)],
    )


def test_registers():
    simulator.run(
        verilog_sources=[
            f"{SRC_DIR}/cpu/registers.v",
            f"{TEST_DIR}/unit/registers/tb_registers.v",
        ],
        toplevel="tb_registers",
        module="unit.registers.test_registers",
        simulator="icarus",
        work_dir=f"{TEST_DIR}/sim_build/registers",
        python_search=[str(TEST_DIR)],
    )


def test_counter():
    simulator.run(
        verilog_sources=[
            f"{SRC_DIR}/cpu/registers.v",
            f"{TEST_DIR}/unit/registers/tb_counter.v",
        ],
        toplevel="tb_counter",
        module="unit.registers.test_counter",
        simulator="icarus",
        work_dir=f"{TEST_DIR}/sim_build/counter",
        python_search=[str(TEST_DIR)],
    )


def test_main_design():
    simulator.run(
        verilog_sources=[
            f"{SRC_DIR}/tinymoa.v",
            f"{TEST_DIR}/integration/tb_placeholder.v",
        ],
        toplevel="testbench",
        module="integration.test_placeholder",
        simulator="icarus",
        work_dir=f"{TEST_DIR}/sim_build/main",
        python_search=[str(TEST_DIR)],
    )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
