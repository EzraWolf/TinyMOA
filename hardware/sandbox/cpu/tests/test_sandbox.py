"""Sandbox unit tests — arch ISS vs cycle model, fibonacci golden."""

from tinymoa_cpu.arch import ArchCore
from tinymoa_cpu.cpu import Core
from tinymoa_cpu.isa import decode
from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    addi,
    imem_from_words,
)
from tinymoa_cpu.types import AluOp, WbSel


def test_decode_addi():
    d = decode(addi(5, 0, 10))
    assert d.fu_op == AluOp.ADD
    assert d.rf_dst == 5
    assert d.wb_sel == WbSel.FU
    assert not d.is_illegal


def test_fibonacci_arch_iss():
    r = ArchCore(imem=imem_from_words(FIBONACCI)).run()
    assert r.dmem.get(FIB_RESULT_ADDR) == FIB_RESULT
    assert r.stores == [(FIB_RESULT_ADDR, FIB_RESULT)]


def test_fibonacci_cycle_model():
    r = Core(imem=imem_from_words(FIBONACCI)).run(halt_pc=FIB_HALT_PC)
    assert r.dmem.get(FIB_RESULT_ADDR) == FIB_RESULT
    assert r.cycles == 117  # locked to ecore_top Verilator fibonacci (RV32I)


def test_pipeline_matches_arch_stores():
    imem = imem_from_words(FIBONACCI)
    arch = ArchCore(imem=dict(imem)).run()
    pipe = Core(imem=dict(imem)).run(halt_pc=FIB_HALT_PC)
    assert pipe.stores == arch.stores
    assert pipe.dmem.get(FIB_RESULT_ADDR) == arch.dmem.get(FIB_RESULT_ADDR)
