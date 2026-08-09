"""Register file — sync write, async read, x0 hardwired on read (matches ecore_regfile)."""

from __future__ import annotations


class RegFile:
    def __init__(self, width: int = 32, depth: int = 32) -> None:
        self.width = width
        self.depth = depth
        self._mask = (1 << width) - 1
        self._regs = [0] * depth

    def read(self, addr: int) -> int:
        if addr == 0 or addr >= self.depth:
            return 0
        return self._regs[addr] & self._mask

    def write(self, addr: int, data: int) -> None:
        """Posedge write; writes to x0 are suppressed."""
        if addr == 0 or addr >= self.depth:
            return
        self._regs[addr] = data & self._mask

    def poison(self, addr: int, data: int) -> None:
        """Direct storage poke (bypasses x0 write-suppress) — for model tests only."""
        if 0 <= addr < self.depth:
            self._regs[addr] = data & self._mask

    def snapshot(self) -> list[int]:
        return [self.read(i) for i in range(self.depth)]
