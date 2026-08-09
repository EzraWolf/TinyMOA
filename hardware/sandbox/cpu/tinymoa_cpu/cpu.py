"""
5-stage in-order e-core model.

Mirrors hardware/rtl/ecore staging, RAW stall rules in ecore_stage_decode,
and execute redirect for branches/jumps. Ideal imem/dmem (always ready),
matching the fibonacci cocotb harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.alu import alu, branch_taken
from tinymoa_cpu.isa import Decoded, decode
from tinymoa_cpu.types import FuSrc1, FuSrc2, WbSel


@dataclass
class RunResult:
    cycles: int
    dmem: dict[int, int]
    regs: list[int]
    retires: list[tuple[int, int | None, int | None]]
    stores: list[tuple[int, int]]


@dataclass
class _D:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data1: int = 0
    fu_data2: int = 0
    imm: int = 0
    store_data: int = 0


@dataclass
class _E:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data: int = 0
    store_data: int = 0
    redirect: bool = False
    redirect_pc: int = 0


@dataclass
class _M:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data: int = 0
    load_data: int = 0


@dataclass
class Core:
    width: int = 32
    depth: int = 32
    imem: dict[int, int] = field(default_factory=dict)
    dmem: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._mask = (1 << self.width) - 1
        self.regs = [0] * self.depth
        self.pc = 0
        self.fetch_valid = False
        self.fetch_pc = 0
        self.fetch_instr = 0
        self.d = _D()
        self.e = _E()
        self.m = _M()
        self.cycles = 0
        self.retires: list[tuple[int, int | None, int | None]] = []
        self.stores: list[tuple[int, int]] = []

    def _r(self, idx: int) -> int:
        if idx == 0 or idx >= self.depth:
            return 0
        return self.regs[idx] & self._mask

    def _w(self, idx: int, val: int) -> None:
        if idx == 0 or idx >= self.depth:
            return
        self.regs[idx] = val & self._mask

    def _ext_imm(self, imm32: int) -> int:
        if self.width == 32:
            return imm32 & self._mask
        if imm32 & 0x80000000:
            return (imm32 | (~0xFFFFFFFF)) & self._mask
        return imm32 & self._mask

    def _hazard(self, dec: Decoded) -> bool:
        """RAW stall vs insn in D/E/M (no forwarding) — ecore_stage_decode."""
        for src in (dec.rf_src1, dec.rf_src2):
            if src == 0:
                continue
            if self.d.valid and self.d.dec and self.d.dec.rf_wen and self.d.dec.rf_dst == src:
                return True
            if self.e.valid and self.e.dec and self.e.dec.rf_wen and self.e.dec.rf_dst == src:
                return True
            if self.m.valid and self.m.dec and self.m.dec.rf_wen and self.m.dec.rf_dst == src:
                return True
        return False

    def step(self) -> bool:
        """One clock. Returns False once halt has retired through WB."""
        redirect = self.e.valid and self.e.redirect
        redirect_pc = self.e.redirect_pc

        # --- writeback (comb from MEM) + RF write this edge ---
        halted = False
        if self.m.valid and self.m.dec is not None:
            dec = self.m.dec
            exception = dec.is_ecall or dec.is_ebreak or dec.is_illegal
            rd_val = None
            if dec.rf_wen and not exception:
                if dec.wb_sel == WbSel.FU:
                    rd_val = self.m.fu_data
                elif dec.wb_sel == WbSel.PC:
                    rd_val = (self.m.pc + 4) & self._mask
                elif dec.wb_sel == WbSel.MEM:
                    rd_val = self.m.load_data
            if rd_val is not None:
                self._w(dec.rf_dst, rd_val)
                self.retires.append((self.m.pc, dec.rf_dst, rd_val))
            else:
                self.retires.append((self.m.pc, None, None))
            # halt: jal x0, 0 — target == pc
            if dec.is_jump and ((self.m.fu_data & ~1) & self._mask) == self.m.pc and dec.rf_dst == 0:
                halted = True

        # MEM captures EX (ideal dmem always ready). Redirect does not kill EX→MEM.
        new_m = _M()
        if self.e.valid and self.e.dec is not None:
            ed = self.e.dec
            load_data = 0
            if ed.mem_wen:
                addr = self.e.fu_data & self._mask
                aligned = addr & ~0x3
                data = self.e.store_data & 0xFFFFFFFF
                self.dmem[aligned] = data
                self.stores.append((aligned, data))
            if ed.mem_ren:
                addr = self.e.fu_data & self._mask
                aligned = addr & ~0x3
                load_data = self.dmem.get(aligned, 0) & self._mask
            new_m = _M(
                valid=True,
                pc=self.e.pc,
                dec=ed,
                fu_data=self.e.fu_data,
                load_data=load_data,
            )

        # EX captures D (killed if redirect this cycle — RTL: i_valid && !redirect)
        new_e = _E()
        if self.d.valid and self.d.dec is not None and not redirect:
            dd = self.d.dec
            fu = alu(dd.fu_op, self.d.fu_data1, self.d.fu_data2, self.width)
            take = False
            tgt = 0
            if dd.is_jump:
                take = True
                tgt = (fu & ~1) & self._mask
            elif dd.is_branch and branch_taken(dd.funct3, self.d.fu_data1, self.d.fu_data2, self.width):
                take = True
                tgt = (self.d.pc + self.d.imm) & self._mask
            new_e = _E(
                valid=True,
                pc=self.d.pc,
                dec=dd,
                fu_data=fu,
                store_data=self.d.store_data,
                redirect=take,
                redirect_pc=tgt,
            )

        # Decode: accept fetch unless hazard / flush
        new_d = _D(valid=False)
        if redirect:
            new_d = _D(valid=False)
            fetch_accept = True  # flush frees fetch
        else:
            if self.fetch_valid:
                dec = decode(self.fetch_instr, width=self.width, reg_num=self.depth)
                if self._hazard(dec):
                    new_d = _D(valid=False)
                    fetch_accept = False
                else:
                    imm = self._ext_imm(dec.imm)
                    if dec.fu_src1 == FuSrc1.PC:
                        a = self.fetch_pc
                    elif dec.fu_src1 == FuSrc1.REG:
                        a = self._r(dec.rf_src1)
                    else:
                        a = 0
                    if dec.fu_src2 == FuSrc2.IMM:
                        b = imm
                    elif dec.fu_src2 == FuSrc2.REG:
                        b = self._r(dec.rf_src2)
                    else:
                        b = 0
                    new_d = _D(
                        valid=True,
                        pc=self.fetch_pc,
                        dec=dec,
                        fu_data1=a & self._mask,
                        fu_data2=b & self._mask,
                        imm=imm,
                        store_data=self._r(dec.rf_src2),
                    )
                    fetch_accept = True
            else:
                fetch_accept = True
                new_d = _D(valid=False)

        # Fetch
        if redirect:
            req_pc = redirect_pc
        else:
            req_pc = self.pc

        # When fetch not accepted (hazard), hold fetch outputs (RTL: o_imem_valid gating)
        if redirect or fetch_accept or not self.fetch_valid:
            instr = self.imem.get(req_pc, 0x0000006F)
            self.fetch_valid = True
            self.fetch_pc = req_pc
            self.fetch_instr = instr
            self.pc = (req_pc + 4) & self._mask
        # else hold fetch_* and pc

        self.d = new_d
        self.e = new_e
        self.m = new_m
        if halted:
            # Halt retired this edge (WB); do not count an extra trailing cycle.
            return False
        self.cycles += 1
        return True

    def run(self, halt_pc: int | None = None, max_cycles: int = 100_000) -> RunResult:
        for _ in range(max_cycles):
            # Prefer detecting halt via retired jal-to-self; also allow halt_pc retire
            before = len(self.retires)
            cont = self.step()
            if halt_pc is not None and self.retires[before:]:
                for pc, _, _ in self.retires[before:]:
                    if pc == halt_pc:
                        return RunResult(
                            cycles=self.cycles,
                            dmem=dict(self.dmem),
                            regs=list(self.regs),
                            retires=list(self.retires),
                            stores=list(self.stores),
                        )
            if not cont:
                return RunResult(
                    cycles=self.cycles,
                    dmem=dict(self.dmem),
                    regs=list(self.regs),
                    retires=list(self.retires),
                    stores=list(self.stores),
                )
        raise TimeoutError(f"core exceeded {max_cycles} cycles")
