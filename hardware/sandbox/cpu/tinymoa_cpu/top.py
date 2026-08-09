"""
ecore_top cycle-accurate model.

NBA-style step: sample registered state → evaluate comb → update all flops together.
Ideal imem/dmem (always ready), matching the fibonacci cocotb harness.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.alu import alu
from tinymoa_cpu.bru import bru
from tinymoa_cpu.isa import decode
from tinymoa_cpu.lsu import apply_store, lsu
from tinymoa_cpu.pipe import DecodeReg, ExecuteReg, FetchReg, MemoryReg
from tinymoa_cpu.regfile import RegFile
from tinymoa_cpu.types import FuSrc1, FuSrc2, WbSel


@dataclass
class RunResult:
    cycles: int
    dmem: dict[int, int]
    regs: list[int]
    retires: list[tuple[int, int | None, int | None]]
    stores: list[tuple[int, int, int]]  # (addr, wdata, wmask)


@dataclass
class Core:
    width: int = 32
    depth: int = 32
    imem: dict[int, int] = field(default_factory=dict)
    dmem: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._mask = (1 << self.width) - 1
        self.rf = RegFile(self.width, self.depth)
        self.fetch_pc_next = 0  # architectural fetch PC register (u_fetch.pc)
        self.fetch = FetchReg()
        self.decode = DecodeReg()
        self.execute = ExecuteReg()
        self.memory = MemoryReg()
        self.cycles = 0
        self.retires: list[tuple[int, int | None, int | None]] = []
        self.stores: list[tuple[int, int, int]] = []

    def _ext_imm(self, imm32: int) -> int:
        if imm32 & 0x80000000:
            return (imm32 | (~0xFFFFFFFF)) & self._mask
        return imm32 & self._mask

    def _raw_hazard(self, rf_src1: int, rf_src2: int) -> bool:
        """ecore_stage_decode hazard: stall vs D/E/M destinations (no forwarding)."""
        for src in (rf_src1, rf_src2):
            if src == 0:
                continue
            if self.decode.valid and self.decode.dec and self.decode.dec.rf_wen and self.decode.dec.rf_dst == src:
                return True
            if self.execute.valid and self.execute.dec and self.execute.dec.rf_wen and self.execute.dec.rf_dst == src:
                return True
            if self.memory.valid and self.memory.dec and self.memory.dec.rf_wen and self.memory.dec.rf_dst == src:
                return True
        return False

    def _writeback_comb(self) -> tuple[bool, int, int, bool]:
        """Combinational WB from MEM. Returns (wen, dst, data, halt)."""
        if not self.memory.valid or self.memory.dec is None:
            return False, 0, 0, False
        dec = self.memory.dec
        exception = dec.is_ecall or dec.is_ebreak or dec.is_illegal or self.memory.mem_error
        halt = (
            dec.is_jump
            and dec.rf_dst == 0
            and ((self.memory.fu_data & ~1) & self._mask) == self.memory.pc
        )
        if not (dec.rf_wen and not exception):
            return False, 0, 0, halt
        if dec.wb_sel == WbSel.FU:
            return True, dec.rf_dst, self.memory.fu_data & self._mask, halt
        if dec.wb_sel == WbSel.PC:
            return True, dec.rf_dst, (self.memory.pc + 4) & self._mask, halt
        if dec.wb_sel == WbSel.MEM:
            return True, dec.rf_dst, self.memory.load_data & self._mask, halt
        return False, 0, 0, halt

    def step(self) -> bool:
        """One clock edge. Returns False when halt has been observed at WB this edge."""
        redirect = self.execute.valid and self.execute.redirect_valid
        redirect_pc = self.execute.redirect_pc

        wb_wen, wb_dst, wb_data, halted = self._writeback_comb()
        if self.memory.valid:
            if wb_wen:
                self.retires.append((self.memory.pc, wb_dst, wb_data))
            else:
                self.retires.append((self.memory.pc, None, None))

        # ---- next-state for MEM (from EX) ----
        next_m = MemoryReg()
        if self.execute.valid and self.execute.dec is not None:
            ed = self.execute.dec
            mem_error = False
            load_data = 0
            if ed.mem_ren or ed.mem_wen:
                # Probe aligned word for load data path
                nbytes = self.width // 8
                probe_addr = self.execute.fu_data & ~(nbytes - 1)
                bus_word = self.dmem.get(probe_addr, 0)
                res = lsu(
                    addr=self.execute.fu_data,
                    store_data=self.execute.store_data,
                    funct3=ed.funct3,
                    is_load=bool(ed.mem_ren),
                    is_store=bool(ed.mem_wen),
                    rdata=bus_word,
                    width=self.width,
                )
                mem_error = res.error
                load_data = res.load_data
                if ed.mem_wen and not res.error:
                    apply_store(self.dmem, res.bus_addr, res.wdata, res.wmask, self.width)
                    self.stores.append((res.bus_addr, res.wdata, res.wmask))
            next_m = MemoryReg(
                valid=True,
                pc=self.execute.pc,
                dec=ed,
                fu_data=self.execute.fu_data,
                load_data=load_data,
                mem_error=mem_error,
            )

        # ---- next-state for EX (from D); killed when redirect ----
        next_e = ExecuteReg()
        if self.decode.valid and self.decode.dec is not None and not redirect:
            dd = self.decode.dec
            fu = alu(dd.fu_op, self.decode.fu_data1, self.decode.fu_data2, self.width)
            redirect_valid = False
            redirect_tgt = 0
            if dd.is_jump:
                redirect_valid = True
                redirect_tgt = (fu & ~1) & self._mask
            elif dd.is_branch:
                br = bru(
                    True,
                    dd.funct3,
                    self.decode.pc,
                    self.decode.fu_data1,
                    self.decode.fu_data2,
                    self.decode.imm,
                    self.width,
                )
                if br.taken:
                    redirect_valid = True
                    redirect_tgt = br.target
            next_e = ExecuteReg(
                valid=True,
                pc=self.decode.pc,
                dec=dd,
                fu_data=fu,
                store_data=self.decode.store_data,
                redirect_valid=redirect_valid,
                redirect_pc=redirect_tgt,
            )

        # ---- next-state for D (from fetch); flush on redirect; stall on RAW ----
        next_d = DecodeReg()
        fetch_ready = True
        if redirect:
            fetch_ready = True
        elif self.fetch.valid:
            dec = decode(self.fetch.instr, width=self.width, reg_num=self.depth)
            if self._raw_hazard(dec.rf_src1, dec.rf_src2):
                fetch_ready = False
            else:
                imm = self._ext_imm(dec.imm)
                if dec.fu_src1 == FuSrc1.PC:
                    a = self.fetch.pc
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
                next_d = DecodeReg(
                    valid=True,
                    pc=self.fetch.pc,
                    dec=dec,
                    fu_data1=a & self._mask,
                    fu_data2=b & self._mask,
                    imm=imm,
                    store_data=self.rf.read(dec.rf_src2),
                )
                fetch_ready = True

        # ---- next-state for fetch (ideal imem always ready) ----
        # o_imem_valid = !o_valid || i_ready || redirect
        imem_req = (not self.fetch.valid) or fetch_ready or redirect
        next_fetch = FetchReg(valid=self.fetch.valid, pc=self.fetch.pc, instr=self.fetch.instr)
        next_fetch_pc = self.fetch_pc_next
        if imem_req:
            req_pc = redirect_pc if redirect else self.fetch_pc_next
            # always ready
            next_fetch = FetchReg(
                valid=True,
                pc=req_pc,
                instr=self.imem.get(req_pc, 0x0000006F) & 0xFFFFFFFF,
            )
            next_fetch_pc = (req_pc + 4) & self._mask

        # ---- commit NBA: RF write from comb WB, then pipe regs ----
        if wb_wen:
            self.rf.write(wb_dst, wb_data)

        self.memory = next_m
        self.execute = next_e
        self.decode = next_d
        self.fetch = next_fetch
        self.fetch_pc_next = next_fetch_pc

        if halted:
            return False
        self.cycles += 1
        return True

    def run(self, halt_pc: int | None = None, max_cycles: int = 100_000) -> RunResult:
        for _ in range(max_cycles):
            before = len(self.retires)
            cont = self.step()
            if halt_pc is not None:
                for pc, _, _ in self.retires[before:]:
                    if pc == halt_pc:
                        return self._result()
            if not cont:
                return self._result()
        raise TimeoutError(f"core exceeded {max_cycles} cycles")

    def _result(self) -> RunResult:
        return RunResult(
            cycles=self.cycles,
            dmem=dict(self.dmem),
            regs=self.rf.snapshot(),
            retires=list(self.retires),
            stores=list(self.stores),
        )
