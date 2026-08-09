"""Spike driver: llvm-mc + ld.lld ELF + -l/--log-commits retire compare."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from tinymoa_cpu.llvm_tools import find_ld_lld, find_llvm_mc
from tinymoa_cpu.mem import DRAM_BASE, DRAM_SIZE
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


def write_flat_elf(path: Path, words: list[int], *, base: int = DRAM_BASE, width: int = 32) -> None:
    """Assemble program words into a Spike-loadable ELF via llvm-mc + ld.lld."""
    llvm_mc = find_llvm_mc()
    ld_lld = find_ld_lld()
    triple = "riscv64" if width >= 64 else "riscv32"
    emul = "elf64lriscv" if width >= 64 else "elf32lriscv"
    asm_lines = [
        ".section .text",
        ".globl _start",
        "_start:",
        *[f"  .word 0x{w & 0xFFFFFFFF:08x}" for w in words],
    ]
    with tempfile.TemporaryDirectory(prefix="tinymoa_elf_") as td:
        td_path = Path(td)
        src = td_path / "prog.s"
        obj = td_path / "prog.o"
        lds = td_path / "spike.ld"
        src.write_text("\n".join(asm_lines) + "\n")
        lds.write_text(
            "ENTRY(_start)\n"
            "SECTIONS {\n"
            f"  . = {base:#x};\n"
            "  .text : { *(.text .text.*) }\n"
            "}\n"
        )
        subprocess.run(
            [llvm_mc, f"-triple={triple}", "-filetype=obj", "-o", str(obj), str(src)],
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            [ld_lld, f"-m{emul}", "-T", str(lds), "-o", str(path), str(obj)],
            check=True,
            capture_output=True,
            text=True,
        )


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


def spike_mem_arg(base: int = DRAM_BASE, mem_size: int = DRAM_SIZE, *, width: int = 32) -> str:
    """Spike -m map. RV64 LUI of 0x8xxxx yields 0xffffffff8xxxxxxx — map both views."""
    low = f"{base:#x}:{mem_size:#x}"
    if width < 64:
        return f"-m{low}"
    hi = 0xFFFFFFFF00000000 | (base & 0xFFFFFFFF)
    return f"-m{low},{hi:#x}:{mem_size:#x}"


def run_spike_retires(
    words: list[int],
    *,
    width: int = 32,
    depth: int = 32,
    max_instructions: int | None = None,
    base: int = DRAM_BASE,
    mem_size: int = DRAM_SIZE,
) -> SpikeResult:
    spike = _find_spike()
    n_insns = max_instructions if max_instructions is not None else max(8, len(words) * 64)
    mask = (1 << width) - 1
    mem_arg = spike_mem_arg(base, mem_size, width=width)
    with tempfile.TemporaryDirectory(prefix="tinymoa_spike_") as td:
        elf = Path(td) / "prog.elf"
        write_flat_elf(elf, words, base=base, width=width)
        cmd = [
            spike,
            f"--isa={isa_string(width, depth)}",
            f"--pc={base:#x}",
            mem_arg,
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
    """Compare Spike commit stream to arch retires.

    On trap_illegal_instruction, Spike stops while the e-core ISS skips illegal
    ops and continues — compare the committed prefix and require the next word
    to decode as illegal under the same WIDTH/DEPTH.
    """
    from tinymoa_cpu.isa import decode

    n = max(len(arch_retires) + 2, 4)
    spike = run_spike_retires(words, width=width, depth=depth, max_instructions=n)
    got = spike.retires
    expect = arch_retires
    if len(got) < len(expect):
        if "trap_illegal_instruction" not in spike.log:
            raise AssertionError(
                f"spike produced {len(got)} retires, need {len(expect)}\n"
                f"tail log:\n{spike.log[-1500:]}"
            )
        # Prefix must match; next program word at arch[len(got)].pc must be illegal.
        expect = arch_retires[: len(got)]
        if not got:
            raise AssertionError(f"spike trapped with no retires\n{spike.log[-1500:]}")
        next_pc = arch_retires[len(got)].pc if len(arch_retires) > len(got) else None
        if next_pc is None:
            raise AssertionError("spike illegal trap but arch has no further retires")
        idx = next_pc // 4
        if idx >= len(words):
            raise AssertionError(f"spike trap pc {next_pc:#x} outside program")
        dec = decode(words[idx], width=width, reg_num=depth)
        if not dec.is_illegal:
            raise AssertionError(
                f"spike illegal trap at pc={next_pc:#x} but decode is legal "
                f"(word={words[idx]:#x})\n{spike.log[-800:]}"
            )
    got = got[: len(expect)]
    for i, (g, e) in enumerate(zip(got, expect)):
        if g.pc != e.pc:
            raise AssertionError(f"spike retire[{i}] pc {g.pc:#x} != arch {e.pc:#x}")
        if g.rd != e.rd:
            raise AssertionError(f"spike retire[{i}] rd {g.rd} != arch {e.rd}")
        if g.rd is not None and g.value != e.value:
            raise AssertionError(
                f"spike retire[{i}] x{e.rd} {g.value:#x} != arch {e.value:#x}"
            )
