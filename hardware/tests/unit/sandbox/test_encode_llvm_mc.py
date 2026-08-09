"""Gate sandbox encode against llvm-mc (hard-fail if llvm-mc missing)."""

from __future__ import annotations

import struct
import subprocess
import tempfile
from pathlib import Path

from tinymoa_cpu.encode_cases import encode_gate_cases
from tinymoa_cpu.llvm_tools import find_llvm_mc, find_llvm_objcopy


def _assemble_word(asm: str, *, xlen: int) -> int:
    llvm_mc = find_llvm_mc()
    objcopy = find_llvm_objcopy()
    triple = "riscv64" if xlen >= 64 else "riscv32"
    with tempfile.TemporaryDirectory(prefix="tinymoa_llvmmc_") as td:
        src = Path(td) / "t.s"
        obj = Path(td) / "t.o"
        raw = Path(td) / "t.bin"
        src.write_text(f".text\n{asm}\n")
        subprocess.run(
            [llvm_mc, f"-triple={triple}", "-filetype=obj", "-o", str(obj), str(src)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [objcopy, "-O", "binary", "--only-section=.text", str(obj), str(raw)],
            check=True,
            capture_output=True,
            text=True,
        )
        data = raw.read_bytes()
        assert len(data) >= 4, f"empty .text for {asm!r}"
        return struct.unpack_from("<I", data, 0)[0]


def test_llvm_mc_available():
    path = find_llvm_mc()
    assert Path(path).is_file()


def test_encode_matches_llvm_mc():
    for case in encode_gate_cases():
        got = _assemble_word(case.asm, xlen=case.xlen)
        assert got == (case.word & 0xFFFFFFFF), (
            f"{case.mnemonic}: sandbox={case.word:#010x} llvm-mc={got:#010x} asm={case.asm!r}"
        )
