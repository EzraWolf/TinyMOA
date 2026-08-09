"""Pipeline register bundles for the e-core sandbox."""

from __future__ import annotations

from dataclasses import dataclass

from tinymoa_cpu.isa import Decoded


@dataclass
class FetchReg:
    valid: bool = False
    pc: int = 0
    instr: int = 0


@dataclass
class DecodeReg:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data1: int = 0
    fu_data2: int = 0
    imm: int = 0
    store_data: int = 0


@dataclass
class ExecuteReg:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data: int = 0
    store_data: int = 0
    redirect_valid: bool = False
    redirect_pc: int = 0


@dataclass
class MemoryReg:
    valid: bool = False
    pc: int = 0
    dec: Decoded | None = None
    fu_data: int = 0
    load_data: int = 0
    mem_error: bool = False
