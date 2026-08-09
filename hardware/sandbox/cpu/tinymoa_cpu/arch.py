"""Architectural (non-pipelined) RV32I ISS — golden reference for the cycle model."""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.alu import alu, branch_taken
from tinymoa_cpu.isa import decode
from tinymoa_cpu.types import FuSrc1, FuSrc2, WbSel


@dataclass
class ArchResult:
    cycles: int
    dmem: dict[int, int]
    regs: list[int]
    retires: list[tuple[int, int | None, int | None]]  # (pc, rd|None, value|None)
    stores: list[tuple[int, int]]  # (addr, data)


@dataclass
class ArchCore:
    width: int = 32
    depth: int = 32
    imem: dict[int, int] = field(default_factory=dict)
    dmem: dict[int, int] = field(default_factory=dict)
    regs: list[int] = field(default_factory=list)
    pc: int = 0
    cycles: int = 0
    retires: list[tuple[int, int | None, int | None]] = field(default_factory=list)
    stores: list[tuple[int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.regs:
            self.regs = [0] * self.depth
        self._mask = (1 << self.width) - 1

    def _ext_imm(self, imm32: int) -> int:
        if imm32 & 0x80000000:
            return (imm32 | ~0xFFFFFFFF) & self._mask if self.width > 32 else imm32 & self._mask
        return imm32 & self._mask

    def _r(self, idx: int) -> int:
        if idx == 0 or idx >= self.depth:
            return 0
        return self.regs[idx] & self._mask

    def _w(self, idx: int, val: int) -> None:
        if idx == 0 or idx >= self.depth:
            return
        self.regs[idx] = val & self._mask

    def step(self) -> bool:
        """Execute one instruction. Returns False if halt (jal x0, 0 to self)."""
        instr = self.imem.get(self.pc, 0x0000006F)  # jal x0, 0
        dec = decode(instr, width=self.width, reg_num=self.depth)
        pc = self.pc
        next_pc = (pc + 4) & self._mask

        if dec.is_illegal or dec.is_ecall or dec.is_ebreak:
            self.cycles += 1
            self.retires.append((pc, None, None))
            self.pc = next_pc
            return True

        rs1 = self._r(dec.rf_src1)
        rs2 = self._r(dec.rf_src2)
        imm = self._ext_imm(dec.imm)

        if dec.fu_src1 == FuSrc1.PC:
            a = pc
        elif dec.fu_src1 == FuSrc1.REG:
            a = rs1
        else:
            a = 0
        if dec.fu_src2 == FuSrc2.IMM:
            b = imm
        elif dec.fu_src2 == FuSrc2.REG:
            b = rs2
        else:
            b = 0

        fu = alu(dec.fu_op, a, b, self.width)
        store_data = rs2

        rd_val = None
        if dec.wb_sel == WbSel.FU:
            rd_val = fu
        elif dec.wb_sel == WbSel.PC:
            rd_val = next_pc
        elif dec.wb_sel == WbSel.MEM:
            addr = fu & self._mask
            word = self.dmem.get(addr & ~0x3, 0) if self.width == 32 else self.dmem.get(addr, 0)
            # word loads only for fibonacci path; full LSU later
            rd_val = word & self._mask

        if dec.mem_wen:
            addr = fu & self._mask
            aligned = addr & ~0x3
            # SW only for the programs we care about first
            self.dmem[aligned] = store_data & 0xFFFFFFFF
            self.stores.append((aligned, store_data & 0xFFFFFFFF))

        if dec.is_jump:
            next_pc = (fu & ~1) & self._mask
        elif dec.is_branch and branch_taken(dec.funct3, a, b, self.width):
            next_pc = (pc + imm) & self._mask

        if dec.rf_wen and rd_val is not None:
            self._w(dec.rf_dst, rd_val)
            self.retires.append((pc, dec.rf_dst, rd_val))
        else:
            self.retires.append((pc, None, None))

        self.cycles += 1
        halt = dec.is_jump and next_pc == pc and dec.rf_dst == 0
        self.pc = next_pc
        return not halt

    def run(self, max_steps: int = 100_000) -> ArchResult:
        for _ in range(max_steps):
            if not self.step():
                break
        else:
            raise TimeoutError(f"arch ISS exceeded {max_steps} steps")
        return ArchResult(
            cycles=self.cycles,
            dmem=dict(self.dmem),
            regs=list(self.regs),
            retires=list(self.retires),
            stores=list(self.stores),
        )
