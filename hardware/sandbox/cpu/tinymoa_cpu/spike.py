"""Minimal Spike driver: bare ELF + -l/--log-commits retire compare."""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tinymoa_cpu.top import RetireEvent


def _find_spike() -> str:
    env = os.environ.get("SPIKE")
    if env and Path(env).is_file():
        return env
    which = shutil.which("spike")
    if which:
        return which
    for cand in (
        Path("/tmp/riscv-isa-sim/build/spike"),
        Path.home() / ".local/bin/spike",
        Path("/opt/riscv/bin/spike"),
    ):
        if cand.is_file():
            return str(cand)
    raise FileNotFoundError(
        "spike not found; build riscv-isa-sim or set SPIKE=/path/to/spike"
    )


def write_flat_elf(path: Path, words: list[int], *, base: int = 0x80000000, width: int = 32) -> None:
    """Write a minimal Spike-loadable RISC-V ELF (ELF32 for XLEN=32, ELF64 for XLEN=64)."""
    text = b"".join(struct.pack("<I", w & 0xFFFFFFFF) for w in words)
    shstr = b"\x00.text\x00.shstrtab\x00"
    if width <= 32:
        _write_elf32(path, text, base, shstr)
    else:
        _write_elf64(path, text, base, shstr)


def _write_elf32(path: Path, text: bytes, base: int, shstr: bytes) -> None:
    ehsize, phentsize, shentsize = 52, 32, 40
    phoff = ehsize
    text_off = phoff + phentsize
    text_off = (text_off + 3) & ~3
    shnum, shstrndx = 3, 2
    shoff = text_off + len(text)
    shoff = (shoff + 3) & ~3
    shstr_off = shoff + shentsize * shnum

    hdr = bytearray(ehsize)
    hdr[0:4] = b"\x7fELF"
    hdr[4:7] = b"\x01\x01\x01"
    struct.pack_into("<HHI", hdr, 16, 2, 243, 1)
    struct.pack_into("<IIII", hdr, 24, base, phoff, shoff, 0)
    struct.pack_into("<HHHHHH", hdr, 40, ehsize, phentsize, 1, shentsize, shnum, shstrndx)

    phdr = bytearray(phentsize)
    struct.pack_into("<IIIIIIII", phdr, 0, 1, text_off, base, base, len(text), len(text), 5, 4)

    shdrs = bytearray(shentsize * shnum)
    # .text @1
    struct.pack_into("<IIIIIIIIII", shdrs, shentsize, 1, 1, 6, base, text_off, len(text), 0, 0, 4, 0)
    # .shstrtab @2
    struct.pack_into(
        "<IIIIIIIIII", shdrs, shentsize * 2, 7, 3, 0, 0, shstr_off, len(shstr), 0, 0, 1, 0
    )

    blob = bytearray(shstr_off + len(shstr))
    blob[0:ehsize] = hdr
    blob[phoff : phoff + phentsize] = phdr
    blob[text_off : text_off + len(text)] = text
    blob[shoff : shoff + len(shdrs)] = shdrs
    blob[shstr_off:] = shstr
    path.write_bytes(blob)


def _write_elf64(path: Path, text: bytes, base: int, shstr: bytes) -> None:
    ehsize, phentsize, shentsize = 64, 56, 64
    phoff = ehsize
    text_off = phoff + phentsize
    text_off = (text_off + 7) & ~7
    shnum, shstrndx = 3, 2
    shoff = text_off + len(text)
    shoff = (shoff + 7) & ~7
    shstr_off = shoff + shentsize * shnum

    hdr = bytearray(ehsize)
    hdr[0:4] = b"\x7fELF"
    hdr[4:7] = b"\x02\x01\x01"
    struct.pack_into("<HHI", hdr, 16, 2, 243, 1)
    struct.pack_into("<QQQ", hdr, 24, base, phoff, shoff)
    struct.pack_into("<IHHHHHH", hdr, 48, 0, ehsize, phentsize, 1, shentsize, shnum, shstrndx)

    phdr = bytearray(phentsize)
    struct.pack_into("<II", phdr, 0, 1, 5)
    struct.pack_into("<QQQQQQ", phdr, 8, text_off, base, base, len(text), len(text), 8)

    shdrs = bytearray(shentsize * shnum)
    off = shentsize
    struct.pack_into("<II", shdrs, off, 1, 1)
    struct.pack_into("<QQQQ", shdrs, off + 8, 6, base, text_off, len(text))
    struct.pack_into("<QQ", shdrs, off + 48, 8, 0)
    off = shentsize * 2
    struct.pack_into("<II", shdrs, off, 7, 3)
    struct.pack_into("<QQQQ", shdrs, off + 8, 0, 0, shstr_off, len(shstr))
    struct.pack_into("<QQ", shdrs, off + 48, 1, 0)

    blob = bytearray(shstr_off + len(shstr))
    blob[0:ehsize] = hdr
    blob[phoff : phoff + phentsize] = phdr
    blob[text_off : text_off + len(text)] = text
    blob[shoff : shoff + len(shdrs)] = shdrs
    blob[shstr_off:] = shstr
    path.write_bytes(blob)


# commit line: core   0: 3 0x80000000 (0x00a00293) x5  0x0000000a
_COMMIT_RE = re.compile(
    r"core\s+\d+:\s+\d+\s+0x([0-9a-fA-F]+)\s+\(0x[0-9a-fA-F]+\)(?:\s+x(\d+)\s+0x([0-9a-fA-F]+))?"
)


@dataclass
class SpikeResult:
    retires: list[RetireEvent]
    log: str


def isa_string(width: int, depth: int) -> str:
    base = "RV64I" if width >= 64 else "RV32I"
    if depth <= 16:
        base = "RV64E" if width >= 64 else "RV32E"
    return base


def run_spike_retires(
    words: list[int],
    *,
    width: int = 32,
    depth: int = 32,
    max_instructions: int | None = None,
    base: int = 0x80000000,
) -> SpikeResult:
    spike = _find_spike()
    n_insns = max_instructions if max_instructions is not None else max(8, len(words) * 64)
    mask = (1 << width) - 1
    with tempfile.TemporaryDirectory(prefix="tinymoa_spike_") as td:
        elf = Path(td) / "prog.elf"
        write_flat_elf(elf, words, base=base, width=width)
        cmd = [
            spike,
            f"--isa={isa_string(width, depth)}",
            f"--pc={base:#x}",
            "-m0x80000000:0x200000",
            f"--instructions={n_insns}",
            "-l",
            "--log-commits",
            str(elf),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
        log = (proc.stderr or "") + (proc.stdout or "")
        if "core" not in log:
            raise RuntimeError(
                f"spike produced no commit log ({proc.returncode}): {' '.join(cmd)}\n{log[-2000:]}"
            )

    retires: list[RetireEvent] = []
    for line in log.splitlines():
        m = _COMMIT_RE.search(line)
        if not m:
            continue
        pc = (int(m.group(1), 16) - base) & mask
        if m.group(2) is not None:
            rd = int(m.group(2))
            val = int(m.group(3), 16) & mask
            retires.append(RetireEvent(pc, rd, val))
        else:
            retires.append(RetireEvent(pc, None, None))
    return SpikeResult(retires=retires, log=log)


def compare_spike_to_arch(
    words: list[int],
    arch_retires: list[RetireEvent],
    *,
    width: int = 32,
    depth: int = 32,
) -> None:
    n = max(len(arch_retires) + 2, 4)
    spike = run_spike_retires(words, width=width, depth=depth, max_instructions=n)
    got = spike.retires[: len(arch_retires)]
    if len(got) < len(arch_retires):
        raise AssertionError(
            f"spike produced {len(got)} retires, need {len(arch_retires)}\n"
            f"tail log:\n{spike.log[-1500:]}"
        )
    for i, (g, e) in enumerate(zip(got, arch_retires)):
        if g.pc != e.pc:
            raise AssertionError(f"spike retire[{i}] pc {g.pc:#x} != arch {e.pc:#x}")
        if g.rd != e.rd:
            raise AssertionError(f"spike retire[{i}] rd {g.rd} != arch {e.rd}")
        if g.rd is not None and g.value != e.value:
            raise AssertionError(
                f"spike retire[{i}] x{e.rd} {g.value:#x} != arch {e.value:#x}"
            )
