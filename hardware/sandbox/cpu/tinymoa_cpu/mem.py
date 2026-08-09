"""Ideal always-ready imem/dmem model shared by sandbox Core and cocotb harnesses."""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.encode import encode_jal
from tinymoa_cpu.lsu import apply_store


# Missing imem returns jal x0,0 (self-loop) — TB policy, not Core.
FILL_INSTR = encode_jal(0, 0)

# Shared Spike/sandbox DRAM window (ELF load + -m map + program data addresses).
DRAM_BASE = 0x80000000
DRAM_SIZE = 0x200000


@dataclass
class IdealMem:
    imem: dict[int, int] = field(default_factory=dict)
    dmem: dict[int, int] = field(default_factory=dict)
    fill_instr: int = FILL_INSTR

    def imem_read(self, addr: int) -> int:
        return self.imem.get(addr, self.fill_instr) & 0xFFFFFFFF

    def dmem_read(self, addr: int) -> int:
        return self.dmem.get(addr, 0)

    def dmem_store(self, addr: int, wdata: int, wmask: int, width: int) -> None:
        apply_store(self.dmem, addr, wdata, wmask, width)


def imem_from_words(words: list[int], base: int = 0) -> dict[int, int]:
    return {base + i * 4: w & 0xFFFFFFFF for i, w in enumerate(words)}
