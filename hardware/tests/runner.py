"""shared runner utilities for cocotb + pytest."""

import re
import glob
import toml
import logging
from pathlib import Path
from xml.etree import ElementTree as ET
from cocotb_tools.runner import get_runner


def run(
    block: str,
    dut: str,
    src: list[str],
    test_name: str = "",
    params: dict = {},
    kind: str = "unit",
):
    PRJ_DIR = Path(__file__).parents[2].resolve()
    test = "_".join(filter(None, (block, dut, test_name)))
    SIM_DIR = (
        Path(__file__).parent.resolve()
        / "sim_build"
        / block
        / test
        / "_".join(("{}_{}".format(*i) for i in params.items()))
    )

    with open(PRJ_DIR / "Veryl.toml") as f:
        config = toml.load(f)

    assert config["build"]["target"]["type"] == "directory"
    SRC_DIR = PRJ_DIR / config["build"]["target"]["path"]
    assert SRC_DIR

    toplevel = f"tinymoa_{block}_{dut}"
    module = f"tests.{kind}.{block}.test_{test}"
    sources = [
        str(((SRC_DIR if s.startswith("~") else PRJ_DIR) / s.removeprefix("~")))
        for s in src
    ]

    r = get_runner("verilator")
    r.log.addHandler(logging.NullHandler())  # shut up!!
    r.log.propagate = False

    try:
        r.build(
            hdl_toplevel=toplevel,
            sources=sources,
            parameters=params,
            timescale=("1ns", "1ps"),
            build_dir=str(SIM_DIR),
            log_file=str(SIM_DIR / "build.log"),
        )
    except Exception:
        errors = _extract_build_errors(str(SIM_DIR), "build.log")
        raise AssertionError("\n".join(errors)) from None

    try:
        r.test(
            hdl_toplevel=toplevel,
            test_module=module,
            parameters=params,
            timescale=("1ns", "1ps"),
            build_dir=str(SIM_DIR),
            test_dir=str(SIM_DIR),
            log_file=str(SIM_DIR / "test.log"),
            extra_env={k: str(v) for k, v in params.items()},
        )
    except SystemExit:
        failures = _extract_failure_trace(str(SIM_DIR))
        if failures:
            raise AssertionError("\n\n".join(failures)) from None
        raise RuntimeError("simulation failed") from None


def _extract_build_errors(sim_build_dir: str, log_name: str) -> list[str]:
    """gathers warnings/errors from `sim_build/path/build.log` because cocotb doesnt"""
    log = Path(sim_build_dir) / log_name
    if not log.exists():
        return ["build.log not found"]

    errors: list[str] = []
    for line in log.read_text().splitlines():
        stripped = line.strip()
        if stripped.startswith(("%Error", "%Warning")):
            # verilator format: "%Warning-TYPE: /path/file.sv:LINE:COL: message"
            # split on first ":" to drop the "%Warning-TYPE" prefix
            body = stripped.split(":", 1)[1].strip() if ":" in stripped else stripped

            # extract "/path/file.sv:LINE:COL" and "message" as two lines
            m = re.match(r"(.+?:\d+:\d+):\s*(.*)", body)
            if m:
                errors.append(m.group(1))
                errors.append(m.group(2))
            else:
                errors.append(stripped)
        elif stripped.startswith(": ... note:") or stripped == "":
            continue
        elif "|" in line and errors:
            # trailing source line with caret, e.g. "   20 |     logic ..."
            errors.append(line.split("|", 1)[1])
    return errors or ["build failed (no errors in build.log)"]


def _extract_failure_trace(sim_build_dir: str) -> list[str]:
    results = glob.glob(f"{sim_build_dir}/*.result.xml")
    xml_files = [r for r in results if Path(r).stat().st_size > 0]
    if not results or not xml_files:
        return _extract_build_errors(sim_build_dir, "build.log")

    tree = ET.parse(max(xml_files, key=lambda p: Path(p).stat().st_mtime))
    failures = []
    for tc in tree.iter("testcase"):
        for f in tc.iter("failure"):
            name = tc.get("name")
            desc = f.get("error_msg")
            file = Path(tc.get("file", "???")).name
            failures.append(f"{name} ({file})\n{desc}")
    return failures
