"""
CPU tests using pytest + cocotb
Run with `pytest test.py` or `uv run pytest test.py`
"""

import toml
import pytest
from pathlib import Path
from cocotb_test import simulator


def run_test(block_name: str, module_name: str, test_type: str):
    PROJECT_PATH = Path(__file__).parents[2].resolve()

    with open(PROJECT_PATH / "Veryl.toml") as f:
        config = toml.load(f)

    # dynamically fetch transpiled SV path
    # Veryl `bundle` and `source` build targets not supported
    TARGET_PATH = None
    if config["build"]["target"]["type"] == "directory":
        TARGET_PATH = PROJECT_PATH / config["build"]["target"]["path"]

    # if config["build"]["target"]["type"] == "source":
    #    TARGET_PATH = PROJECT_PATH / config["build"]["sources"][0]

    assert TARGET_PATH

    # Veryl file     `cpu_alu.veryl` must have
    # Veryl modules  `cpu_alu and `dut_cpu_alu`
    #
    # `veryl build` creates `cpu_alu.sv` and thus
    # `dut_cpu_alu` transpiles to `tinymoa_cpu_dut_alu`
    toplevel = f"{config['project']['name']}_dut_{module_name}"
    sources = [str(TARGET_PATH / block_name / f"{module_name}.sv")]
    module = f"{test_type}.{block_name}.test_{module_name}"

    simulator.run(
        toplevel=toplevel,
        verilog_sources=sources,
        module=module,
        simulator=config["test"]["simulator"],
    )


def test_cpu_alu():
    run_test("cpu", "cpu_alu", "unit")


if __name__ == "__main__":
    # run_test2("cpu_alu")
    pytest.main([__file__])
