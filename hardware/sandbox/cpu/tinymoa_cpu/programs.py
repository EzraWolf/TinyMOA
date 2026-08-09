"""Directed programs for sandbox + RTL lockstep (built via tinymoa_cpu.encode)."""

from __future__ import annotations

from tinymoa_cpu import encode as enc
from tinymoa_cpu.mem import IdealMem, imem_from_words  # noqa: F401 — re-exported


def xlen_addr(addr: int, width: int) -> int:
    """Canonical XLEN address for a 32-bit lui-built pointer (RV64 sign-extends bit 31)."""
    addr &= 0xFFFFFFFF
    if width > 32 and (addr & 0x80000000):
        return addr | (((1 << width) - 1) ^ 0xFFFFFFFF)
    return addr


# Keep data in the Spike DRAM window at 0x80000000 so arch/spike/RTL share one image.
FIB_RESULT_ADDR = 0x80001000
FIB_RESULT = 55

FIBONACCI = [
    enc.encode_addi(5, 0, 10),
    enc.encode_addi(6, 0, 0),
    enc.encode_addi(7, 0, 1),
    enc.encode_beq(5, 0, 24),
    enc.encode_add(8, 6, 7),
    enc.encode_addi(6, 7, 0),
    enc.encode_addi(7, 8, 0),
    enc.encode_addi(5, 5, -1),
    enc.encode_jal(0, -20),
    enc.encode_lui(9, 0x80001),  # 0x80001000
    enc.encode_sw(9, 6, 0),
    enc.encode_jal(0, 0),
]

FIB_HALT_PC = (len(FIBONACCI) - 1) * 4

RAW_RESULT_ADDR = 0x80002000
RAW_CHAIN = [
    enc.encode_addi(1, 0, 1),
    enc.encode_addi(2, 1, 1),
    enc.encode_addi(3, 2, 1),
    enc.encode_addi(4, 3, 1),
    enc.encode_addi(5, 4, 1),
    enc.encode_lui(6, 0x80002),
    enc.encode_sw(6, 5, 0),
    enc.encode_jal(0, 0),
]
RAW_HALT_PC = (len(RAW_CHAIN) - 1) * 4
RAW_RESULT = 5

BRANCH_RESULT_ADDR = 0x80003000
BRANCH_STORM = [
    enc.encode_addi(1, 0, 3),
    enc.encode_addi(2, 0, 0),
    enc.encode_beq(1, 0, 12),
    enc.encode_addi(2, 2, 1),
    enc.encode_bne(1, 0, 8),
    enc.encode_addi(2, 2, 7),
    enc.encode_addi(2, 2, 1),
    enc.encode_blt(0, 1, 8),
    enc.encode_addi(2, 2, 7),
    enc.encode_addi(2, 2, 1),
    enc.encode_lui(3, 0x80003),
    enc.encode_sw(3, 2, 0),
    enc.encode_jal(0, 0),
]
BRANCH_HALT_PC = (len(BRANCH_STORM) - 1) * 4
BRANCH_RESULT = 3

LSU_RESULT_ADDR = 0x80005000
LOAD_STORE_PARTIAL = [
    enc.encode_lui(1, 0x80004),  # scratch 0x80004000
    enc.encode_addi(2, 0, 0xA1),
    enc.encode_addi(3, 0, 0xB2),
    enc.encode_sb(1, 2, 0),
    enc.encode_sb(1, 3, 1),
    enc.encode_addi(4, 0, 0x321),
    enc.encode_sh(1, 4, 2),
    enc.encode_lw(5, 1, 0),
    enc.encode_lui(6, 0x80005),
    enc.encode_sw(6, 5, 0),
    enc.encode_jal(0, 0),
]
LSU_HALT_PC = (len(LOAD_STORE_PARTIAL) - 1) * 4
LSU_RESULT = 0x0321B2A1

E_RESULT_ADDR = 0x80006000
# DEPTH=16: addi/sw involving x16 are illegal → no store. DEPTH=32: store x16==8.
RV32E_HIGHREG = [
    enc.encode_addi(1, 0, 7),
    enc.encode_addi(16, 1, 1),  # x16 = 8 on I; illegal on E
    enc.encode_lui(2, 0x80006),
    enc.encode_sw(2, 16, 0),  # store x16 — illegal on E (rs2 high); writes 8 on I
    enc.encode_jal(0, 0),
]
E_HALT_PC = (len(RV32E_HIGHREG) - 1) * 4
E_RESULT_E = 0  # no architectural store on RV32E
E_RESULT_I = 8

W64_RESULT_ADDR = 0x80007000
W64_RESULT = 5  # addiw x3, x2, 3 with x2=2
RV64_W = [
    enc.encode_addi(2, 0, 2),
    enc.encode_addiw(3, 2, 3),  # RV64 only; illegal on RV32 → x3 stays 0
    enc.encode_lui(4, 0x80007),
    enc.encode_sw(4, 3, 0),
    enc.encode_jal(0, 0),
]
W64_HALT_PC = (len(RV64_W) - 1) * 4

def _run_words(words: list[int], halt_pc: int, width: int = 32, depth: int = 32):
    from tinymoa_cpu.top import Core

    mem = IdealMem(imem=imem_from_words(words))
    return Core(width=width, depth=depth, mem=mem).run(halt_pc=halt_pc)


def run_fibonacci(width: int = 32, depth: int = 32):
    return _run_words(FIBONACCI, FIB_HALT_PC, width, depth)


def run_raw_chain(width: int = 32, depth: int = 32):
    return _run_words(RAW_CHAIN, RAW_HALT_PC, width, depth)


def run_branch_storm(width: int = 32, depth: int = 32):
    return _run_words(BRANCH_STORM, BRANCH_HALT_PC, width, depth)


def run_load_store_partial(width: int = 32, depth: int = 32):
    return _run_words(LOAD_STORE_PARTIAL, LSU_HALT_PC, width, depth)


def run_rv32e_highreg(width: int = 32, depth: int = 16):
    return _run_words(RV32E_HIGHREG, E_HALT_PC, width, depth)


def run_rv64_w(width: int = 64, depth: int = 32):
    return _run_words(RV64_W, W64_HALT_PC, width, depth)
