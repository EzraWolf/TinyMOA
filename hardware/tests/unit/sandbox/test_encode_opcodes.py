"""Gate sandbox encode words against vendored riscv-opcodes match/mask."""

from __future__ import annotations

from tinymoa_cpu.encode_cases import encode_gate_cases
from tinymoa_cpu.opcodes import assert_word_matches, load_match_mask


def test_encode_matches_riscv_opcodes_match_mask():
    table = load_match_mask()
    for case in encode_gate_cases():
        assert_word_matches(case.mnemonic, case.word, table)


def test_opcodes_table_covers_gate_mnemonics():
    table = load_match_mask()
    needed = {c.mnemonic for c in encode_gate_cases()}
    missing = sorted(needed - set(table))
    assert not missing, f"instr_match_mask.json missing: {missing}"
