"""Ensure sandbox fibonacci image stays byte-identical to RTL test encoders."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tinymoa_cpu.programs import FIBONACCI


def _load_encode_rv32i():
    path = Path(__file__).resolve().parents[2] / "common" / "encode_rv32i.py"
    spec = importlib.util.spec_from_file_location("encode_rv32i", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_fibonacci_encodings_match_rtl_test_helpers():
    rv = _load_encode_rv32i()
    expected = [
        rv.encode_addi(5, 0, 10),
        rv.encode_addi(6, 0, 0),
        rv.encode_addi(7, 0, 1),
        rv.encode_beq(5, 0, 24),
        rv.encode_add(8, 6, 7),
        rv.encode_addi(6, 7, 0),
        rv.encode_addi(7, 8, 0),
        rv.encode_addi(5, 5, -1),
        rv.encode_jal(0, -20),
        rv.encode_addi(9, 0, 0x100),
        rv.encode_sw(9, 6, 0),
        rv.encode_jal(0, 0),
    ]
    assert FIBONACCI == expected
