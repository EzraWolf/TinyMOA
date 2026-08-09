"""Ensure hardware/tests/common/encode_rv32i stays byte-identical to sandbox encode (truth)."""

from __future__ import annotations

import importlib.util
from pathlib import Path

from tinymoa_cpu import encode as sandbox_enc
from tinymoa_cpu.programs import FIBONACCI


def _load_test_encode():
    path = Path(__file__).resolve().parents[2] / "common" / "encode_rv32i.py"
    spec = importlib.util.spec_from_file_location("encode_rv32i_test_helper", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_sandbox_encode_matches_test_helper_api():
    test_enc = _load_test_encode()
    cases = [
        ("encode_addi", (5, 0, 10)),
        ("encode_add", (8, 6, 7)),
        ("encode_beq", (5, 0, 24)),
        ("encode_jal", (0, -20)),
        ("encode_sw", (9, 6, 0)),
        ("encode_lui", (1, 0x12345)),
        ("encode_ecall", ()),
    ]
    for name, args in cases:
        assert getattr(sandbox_enc, name)(*args) == getattr(test_enc, name)(*args), name


def test_fibonacci_built_from_sandbox_encode():
    expected = [
        sandbox_enc.encode_addi(5, 0, 10),
        sandbox_enc.encode_addi(6, 0, 0),
        sandbox_enc.encode_addi(7, 0, 1),
        sandbox_enc.encode_beq(5, 0, 24),
        sandbox_enc.encode_add(8, 6, 7),
        sandbox_enc.encode_addi(6, 7, 0),
        sandbox_enc.encode_addi(7, 8, 0),
        sandbox_enc.encode_addi(5, 5, -1),
        sandbox_enc.encode_jal(0, -20),
        sandbox_enc.encode_lui(9, 0x80001),
        sandbox_enc.encode_sw(9, 6, 0),
        sandbox_enc.encode_jal(0, 0),
    ]
    assert FIBONACCI == expected
