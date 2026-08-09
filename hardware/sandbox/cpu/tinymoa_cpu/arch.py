"""Architectural (non-pipelined) ISS using the same decode/ALU/LSU as the cycle model."""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.alu import alu
from tinymoa_cpu.bru import bru
from tinymoa_cpu.isa import decode
from tinymoa_cpu.lsu import apply_store, lsu
from tinymoa_cpu.regfile import RegFile
from tinymoa_cpu.types import FuSrc1, FuSrc2, WbSel


@dataclass
class ArchResult:
    cycles: int
    dmem: dict[int, int]
    regs: list[int]
    stores: list[tuple[int, int, int]]


@dataclass
class ArchCore:
    width: int = 32
    depth: int = 32
    imem: dict[int, int] = field(default_factory=dict)
    dmem: dict[int, int] = field(default_factory=dict)
    pc: int = 0
    cycles: int = 0
    stores: list[tuple[int, int, int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self._mask = (1 << self.width) - 1
        self.rf = RegFile(self.width, self.depth)

    def _ext_imm(self, imm32: int) -> int:
        if imm32 & 0x80000000:
            return (imm32 | (~0xFFFFFFFF)) & self._mask
        return imm32 & self._mask

    def step(self) -> bool:
        instr = self.imem.get(self.pc, 0x0000006F)
        dec = decode(instr, width=self.width, reg_num=self.depth)
        pc = self.pc
        next_pc = (pc + 4) & self._mask
        imm = self._ext_imm(dec.imm)

        if dec.fu_src1 == FuSrc1.PC:
            a = pc
        elif dec.fu_src1 == FuSrc1.REG:
            a = self.rf.read(dec.rf_src1)
        else:
            a = 0
        if dec.fu_src2 == FuSrc2.IMM:
            b = imm
        elif dec.fu_src2 == FuSrc2.REG:
            b = self.rf.read(dec.rf_src2)
        else:
            b = 0

        fu = alu(dec.fu_op, a, b, self.width)
        store_data = self.rf.read(dec.rf_src2)

        if dec.mem_ren or dec.mem_wen:
            bus_word = self.dmem.get(fu & ~((self.width // 8) - 1), 0)
            res = lsu(fu, store_data, dec.funct3, dec.mem_ren, dec.mem_wen, bus_word, self.width)
            if dec.mem_wen and not res.error:
                apply_store(self.dmem, res.bus_addr, res.wdata, res.wmask, self.width)
                self.stores.append((res.bus_addr, res.wdata, res.wmask))
            load_data = res.load_data
            mem_error = res.error
        else:
            load_data = 0
            mem_error = False

        exception = dec.is_ecall or dec.is_ebreak or dec.is_illegal or mem_error
        if dec.rf_wen and not exception:
            if dec.wb_sel == WbSel.FU:
                self.rf.write(dec.rf_dst, fu)
            elif dec.wb_sel == WbSel.PC:
                self.rf.write(dec.rf_dst, next_pc)
            elif dec.wb_sel == WbSel.MEM:
                self.rf.write(dec.rf_dst, load_data)

        if dec.is_jump:
            next_pc = (fu & ~1) & self._mask
        elif dec.is_branch:
            br = bru(True, dec.funct3, pc, a, b, imm, self.width)
            if br.taken:
                next_pc = br.target

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
            regs=self.rf.snapshot(),
            stores=list(self.stores),
        )
