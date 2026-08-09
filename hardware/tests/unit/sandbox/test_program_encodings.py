"""Sandbox encode is the single packing source; tests.common.encode_rv32i re-exports it."""

from __future__ import annotations

import importlib.util
import inspect
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


def test_encode_rv32i_reexports_sandbox_encode():
    test_enc = _load_test_encode()
    sandbox_fns = {
        name: fn
        for name, fn in inspect.getmembers(sandbox_enc, inspect.isfunction)
        if name.startswith("encode_")
    }
    assert sandbox_fns, "sandbox encode surface empty"
    for name, fn in sandbox_fns.items():
        assert getattr(test_enc, name) is fn, name


def test_rv64_shift_encode_keeps_six_bit_shamt():
    assert sandbox_enc.encode_slli(2, 1, 40, width=64) == sandbox_enc.encode_i_type(40, 1, 0x1, 2, 0x13)
    assert sandbox_enc.encode_srli(2, 1, 40, width=64) == sandbox_enc.encode_i_type(40, 1, 0x5, 2, 0x13)
    assert sandbox_enc.encode_srai(2, 1, 40, width=64) == sandbox_enc.encode_i_type(0x400 | 40, 1, 0x5, 2, 0x13)
    # RV32 truncates; shamt 40 must not survive as 40.
    assert sandbox_enc.encode_slli(2, 1, 40, width=32) == sandbox_enc.encode_i_type(8, 1, 0x1, 2, 0x13)


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
