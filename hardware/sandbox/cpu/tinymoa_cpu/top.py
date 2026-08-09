"""
ecore_top cycle-accurate model.

NBA-style step: sample registered state → evaluate comb → update all flops together.
Ideal imem/dmem via IdealMem (always ready), matching the cocotb harness.

CycleSample is post-edge (matches cocotb FallingEdge after the posedge that committed the NBA).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from tinymoa_cpu.alu import alu
from tinymoa_cpu.bru import bru
from tinymoa_cpu.isa import decode
from tinymoa_cpu.lsu import lsu
from tinymoa_cpu.mem import IdealMem
from tinymoa_cpu.pipe import DecodeReg, ExecuteReg, FetchReg, MemoryReg
from tinymoa_cpu.regfile import RegFile
from tinymoa_cpu.types import FuSrc1, FuSrc2, WbSel


@dataclass
class RetireEvent:
    pc: int
    rd: int | None
    value: int | None


@dataclass
class CycleSample:
    """Post-edge observables (aligned with cocotb FallingEdge + CHECK_DELAY)."""

    cycle: int
    imem_valid: bool
    imem_addr: int
    dmem_valid: bool
    dmem_ren: bool
    dmem_wen: bool
    dmem_addr: int
    dmem_wdata: int
    dmem_wmask: int
    retire_valid: bool
    retire_pc: int
    rf: tuple[int, ...]


@dataclass
class RunResult:
    cycles: int
    dmem: dict[int, int]
    regs: list[int]
    retires: list[RetireEvent]
    stores: list[tuple[int, int, int]]
    samples: list[CycleSample] = field(default_factory=list)


@dataclass
class Core:
    width: int = 32
    depth: int = 32
    mem: IdealMem = field(default_factory=IdealMem)
    imem: dict[int, int] | None = None
    dmem: dict[int, int] | None = None

    def __post_init__(self) -> None:
        if self.imem is not None or self.dmem is not None:
            self.mem = IdealMem(
                imem=dict(self.imem or self.mem.imem),
                dmem=dict(self.dmem or self.mem.dmem),
                fill_instr=self.mem.fill_instr,
            )
        self._mask = (1 << self.width) - 1
        self.rf = RegFile(self.width, self.depth)
        self.fetch_pc_next = 0
        self.fetch = FetchReg()
        self.decode = DecodeReg()
        self.execute = ExecuteReg()
        self.memory = MemoryReg()
        self.cycles = 0
        self.retires: list[RetireEvent] = []
        self.stores: list[tuple[int, int, int]] = []
        self.samples: list[CycleSample] = []

    def _ext_imm(self, imm32: int) -> int:
        if imm32 & 0x80000000:
            return (imm32 | (~0xFFFFFFFF)) & self._mask
        return imm32 & self._mask

    def _raw_hazard(self, rf_src1: int, rf_src2: int) -> bool:
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

    def _writeback_comb(self) -> tuple[bool, int, int]:
        if not self.memory.valid or self.memory.dec is None:
            return False, 0, 0
        dec = self.memory.dec
        exception = dec.is_ecall or dec.is_ebreak or dec.is_illegal or self.memory.mem_error
        if not (dec.rf_wen and not exception):
            return False, 0, 0
        if dec.wb_sel == WbSel.FU:
            return True, dec.rf_dst, self.memory.fu_data & self._mask
        if dec.wb_sel == WbSel.PC:
            return True, dec.rf_dst, (self.memory.pc + 4) & self._mask
        if dec.wb_sel == WbSel.MEM:
            return True, dec.rf_dst, self.memory.load_data & self._mask
        return False, 0, 0

    def _dmem_comb(self) -> tuple[bool, bool, bool, int, int, int]:
        """o_dmem_* from execute stage (matches ecore_stage_memory comb)."""
        if not self.execute.valid or self.execute.dec is None:
            return False, False, False, 0, 0, 0
        ed = self.execute.dec
        if not (ed.mem_ren or ed.mem_wen):
            return False, False, False, 0, 0, 0
        nbytes = self.width // 8
        probe_addr = self.execute.fu_data & ~(nbytes - 1)
        bus_word = self.mem.dmem_read(probe_addr)
        res = lsu(
            addr=self.execute.fu_data,
            store_data=self.execute.store_data,
            funct3=ed.funct3,
            is_load=bool(ed.mem_ren),
            is_store=bool(ed.mem_wen),
            rdata=bus_word,
            width=self.width,
        )
        if res.error:
            return False, False, False, 0, 0, 0
        return (
            True,
            bool(ed.mem_ren),
            bool(ed.mem_wen),
            res.bus_addr & self._mask,
            res.wdata & self._mask,
            res.wmask,
        )

    def _imem_comb(self, redirect: bool, fetch_ready: bool) -> tuple[bool, int]:
        imem_valid = (not self.fetch.valid) or fetch_ready or redirect
        addr = (self.execute.redirect_pc if redirect else self.fetch_pc_next) & self._mask
        return imem_valid, addr

    def step(self) -> CycleSample:
        redirect = self.execute.valid and self.execute.redirect_valid
        redirect_pc = self.execute.redirect_pc

        # Architectural retire / RF write uses pre-edge memory (sync RF write).
        wb_wen, wb_dst, wb_data = self._writeback_comb()
        if self.memory.valid:
            if wb_wen and wb_dst != 0:
                self.retires.append(RetireEvent(self.memory.pc, wb_dst, wb_data))
            else:
                self.retires.append(RetireEvent(self.memory.pc, None, None))

        # MEM next from EX — apply store side effect when EX presents a store
        next_m = MemoryReg()
        if self.execute.valid and self.execute.dec is not None:
            ed = self.execute.dec
            mem_error = False
            load_data = 0
            if ed.mem_ren or ed.mem_wen:
                nbytes = self.width // 8
                probe_addr = self.execute.fu_data & ~(nbytes - 1)
                bus_word = self.mem.dmem_read(probe_addr)
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
                    self.mem.dmem_store(res.bus_addr, res.wdata, res.wmask, self.width)
                    self.stores.append((res.bus_addr, res.wdata, res.wmask))
            next_m = MemoryReg(
                valid=True,
                pc=self.execute.pc,
                dec=ed,
                fu_data=self.execute.fu_data,
                load_data=load_data,
                mem_error=mem_error,
            )

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

        imem_req = (not self.fetch.valid) or fetch_ready or redirect
        next_fetch = FetchReg(valid=self.fetch.valid, pc=self.fetch.pc, instr=self.fetch.instr)
        next_fetch_pc = self.fetch_pc_next
        if imem_req:
            req_pc = redirect_pc if redirect else self.fetch_pc_next
            next_fetch = FetchReg(
                valid=True,
                pc=req_pc,
                instr=self.mem.imem_read(req_pc),
            )
            next_fetch_pc = (req_pc + 4) & self._mask

        if wb_wen:
            self.rf.write(wb_dst, wb_data)

        self.memory = next_m
        self.execute = next_e
        self.decode = next_d
        self.fetch = next_fetch
        self.fetch_pc_next = next_fetch_pc

        # Post-edge comb (what cocotb sees after FallingEdge)
        post_redirect = self.execute.valid and self.execute.redirect_valid
        # fetch_ready for post-edge imem: stall if decode would stall on current fetch
        post_fetch_ready = True
        if not post_redirect and self.fetch.valid:
            dec = decode(self.fetch.instr, width=self.width, reg_num=self.depth)
            if self._raw_hazard(dec.rf_src1, dec.rf_src2):
                post_fetch_ready = False
        imem_valid, imem_addr = self._imem_comb(post_redirect, post_fetch_ready)
        dmem_valid, dmem_ren, dmem_wen, dmem_addr, dmem_wdata, dmem_wmask = self._dmem_comb()

        self.cycles += 1
        sample = CycleSample(
            cycle=self.cycles,
            imem_valid=imem_valid,
            imem_addr=imem_addr if imem_valid else 0,
            dmem_valid=dmem_valid,
            dmem_ren=dmem_ren,
            dmem_wen=dmem_wen,
            dmem_addr=dmem_addr,
            dmem_wdata=dmem_wdata,
            dmem_wmask=dmem_wmask,
            retire_valid=self.memory.valid,
            retire_pc=self.memory.pc if self.memory.valid else 0,
            rf=tuple(self.rf.snapshot()),
        )
        self.samples.append(sample)
        return sample

    def run(self, halt_pc: int | None = None, max_cycles: int = 100_000) -> RunResult:
        """Stop when post-edge o_valid shows halt_pc (same predicate as cocotb)."""
        for _ in range(max_cycles):
            sample = self.step()
            if halt_pc is not None and sample.retire_valid and sample.retire_pc == halt_pc:
                # Halt is visible on o_valid one edge before its (no-op) RF write.
                # Record it so the retire stream matches ArchCore/Spike including the halt.
                if not self.retires or self.retires[-1].pc != halt_pc:
                    wb_wen, wb_dst, wb_data = self._writeback_comb()
                    if wb_wen and wb_dst != 0:
                        self.retires.append(RetireEvent(halt_pc, wb_dst, wb_data))
                    else:
                        self.retires.append(RetireEvent(halt_pc, None, None))
                return self._result()
        raise TimeoutError(f"core exceeded {max_cycles} cycles")

    def _result(self) -> RunResult:
        return RunResult(
            cycles=self.cycles,
            dmem=dict(self.mem.dmem),
            regs=self.rf.snapshot(),
            retires=list(self.retires),
            stores=list(self.stores),
            samples=list(self.samples),
        )
