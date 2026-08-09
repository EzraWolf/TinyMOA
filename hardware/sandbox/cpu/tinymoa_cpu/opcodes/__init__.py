"""Vendored riscv-opcodes match/mask tables for encode gating.

Regenerate `instr_match_mask.json` from https://github.com/riscv/riscv-opcodes:
  git clone https://github.com/riscv/riscv-opcodes && cd riscv-opcodes && make
  then extract the mnemonic keys we encode into this JSON (match/mask only).
"""

from __future__ import annotations

import json
from pathlib import Path

_PATH = Path(__file__).with_name("instr_match_mask.json")


def load_match_mask() -> dict[str, dict[str, str]]:
    return json.loads(_PATH.read_text())


def assert_word_matches(mnemonic: str, word: int, table: dict[str, dict[str, str]] | None = None) -> None:
    table = table if table is not None else load_match_mask()
    if mnemonic not in table:
        raise KeyError(f"mnemonic {mnemonic!r} missing from { _PATH.name }")
    match = int(table[mnemonic]["match"], 0)
    mask = int(table[mnemonic]["mask"], 0)
    got = word & 0xFFFFFFFF
    if (got & mask) != match:
        raise AssertionError(
            f"{mnemonic}: word={got:#010x} & mask={mask:#010x} = {got & mask:#010x} != match={match:#010x}"
        )
