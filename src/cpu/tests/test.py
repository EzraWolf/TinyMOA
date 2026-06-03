"""
CPU tests using pytest + cocotb
Run with `pytest test.py` or `uv run pytest test.py`
"""

import toml
import pytest
from pathlib import Path
from cocotb_test import simulator


def run_test(module_name: str):
    PROJECT_PATH = Path(__file__).parents[3].resolve()
    SYSTEM_PATH = Path(__file__).parents[1].resolve()

    with open(PROJECT_PATH / "Veryl.toml") as f:
        config = toml.load(f)

    # dynamically fetch transpiled SV path
    # Veryl "bundle" build target not supported yet
    TARGET_PATH = None
    if config["build"]["target"]["type"] == "directory":
        TARGET_PATH = PROJECT_PATH / config["build"]["target"]["path"]

    if config["build"]["target"]["type"] == "source":
        TARGET_PATH = SYSTEM_PATH

    assert TARGET_PATH

    # Veryl file     `cpu_alu.veryl` must have
    # Veryl modules  `cpu_alu and `dut_cpu_alu`
    #
    # `veryl build` creates `cpu_alu.sv` and thus
    # `dut_cpu_alu` transpiles to `tinymoa_cpu_dut_alu`
    project_name: str = config["project"]["name"]
    toplevel = f"{project_name}_dut_{module_name}"

    sources = [str(TARGET_PATH / SYSTEM_PATH.name / f"{module_name}.sv")]
    simulator.run(
        toplevel=toplevel,
        verilog_sources=sources,
        module=f"test_{module_name}",
        simulator=config["test"]["simulator"],
    )


def test_cpu_alu():
    run_test("cpu_alu")


if __name__ == "__main__":
    # run_test2("cpu_alu")
    pytest.main([__file__])
