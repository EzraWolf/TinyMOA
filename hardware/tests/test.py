"""
CPU tests using pytest + cocotb
Run with `pytest test.py` or `uv run pytest test.py`
"""

import os
import sys
import glob
import toml
import pytest
from pathlib import Path
from xml.etree import cElementTree as ET
from cocotb_test.simulator import Verilator


def _extract_failure_trace(sim_build_dir: str) -> list[str]:
    """
    because cocotb-test hasn't pytest trace
    and pytest capture log is rancid.
    """
    results = glob.glob(f"{sim_build_dir}/*_results.xml")

    tree = ET.parse(max(results, key=os.path.getmtime))

    failures = []
    for tc in tree.iter("testcase"):
        for f in tc.iter("failure"):
            name = tc.get("name")
            # line = tc.get("lineno") # only returns the "@cocotb.test()" line
            desc = f.get("error_msg")
            file = os.path.basename(tc.get("file", "???"))
            failures.append(f"{name} ({file})\n{desc}\n\b")
    return failures


def run_test(
    block_name: str,
    module_name: str,
    test_type: str,
    pkgs: list = [],
    params: dict = {},
):
    PRJ_DIR = Path(__file__).parents[2].resolve()
    SIM_DIR = Path(__file__).resolve().parent / "sim_build" / module_name

    with open(PRJ_DIR / "Veryl.toml") as f:
        config = toml.load(f)

    # Veryl `bundle` and `source` build targets not supported
    assert config["build"]["target"]["type"] == "directory"
    SRC_DIR = PRJ_DIR / config["build"]["target"]["path"]
    assert SRC_DIR

    sources = [str(SRC_DIR / block_name / f"{module_name}.sv")]
    sources += [str(SRC_DIR / block_name / "pkgs" / f"{p}.sv") for p in pkgs]

    failures = []
    try:
        Verilator(
            toplevel=f"{config['project']['name']}_dut_{module_name}",
            module=f"{test_type}.{block_name}.test_{module_name}",
            sim_build=str(SIM_DIR),
            verilog_sources=sources,
            parameters=params,
        ).run()
    except SystemExit:
        failures = _extract_failure_trace(str(SIM_DIR))

    for failure in failures:
        pytest.fail(failure)


def test_cpu_alu():
    run_test("cpu", "cpu_alu", "unit", pkgs=["pkg_cpu_alu"])


@pytest.mark.parametrize("params", [{"WIDTH": 64, "DEPTH": 4}])
def test_mem_fifo(params):
    run_test("mem", "mem_fifo", "unit", params=params)


if __name__ == "__main__":
    # show terse error trace in summary (same info as `-v --tb=short`, just shorter)
    # works by using `pytest.fail()` in `run_test()`
    pytest.main(
        [
            __file__,
            *sys.argv[1:],
            "-q",
            "--no-header",
            "--tb=line",
            "--show-capture=no",
            "-rfE",
            "-W",
            "ignore::pytest.PytestAssertRewriteWarning",
        ]
    )
