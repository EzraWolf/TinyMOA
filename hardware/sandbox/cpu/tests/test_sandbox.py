"""Sandbox unit + property tests."""

from tinymoa_cpu.arch import ArchCore
from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    imem_from_words,
    run_fibonacci,
)
from tinymoa_cpu.regfile import RegFile
from tinymoa_cpu.top import Core


def test_regfile_x0_hardwired_on_read():
    rf = RegFile()
    rf.poison(0, 0xDEADBEEF)
    assert rf.read(0) == 0
    rf.write(0, 0xCAFEBABE)
    assert rf.read(0) == 0


def test_fibonacci_arch_iss():
    r = ArchCore(imem=imem_from_words(FIBONACCI)).run()
    assert r.dmem.get(FIB_RESULT_ADDR) == FIB_RESULT


def test_fibonacci_cycle_model():
    r = run_fibonacci()
    assert r.dmem.get(FIB_RESULT_ADDR) == FIB_RESULT
    assert r.stores[-1][0] == FIB_RESULT_ADDR


def test_pipeline_matches_arch_architectural_state():
    imem = imem_from_words(FIBONACCI)
    arch = ArchCore(imem=dict(imem)).run()
    pipe = Core(imem=dict(imem)).run(halt_pc=FIB_HALT_PC)
    assert pipe.dmem.get(FIB_RESULT_ADDR) == arch.dmem.get(FIB_RESULT_ADDR)
    assert pipe.dmem.get(FIB_RESULT_ADDR) == FIB_RESULT


def test_raw_hazard_extends_runtime_vs_arch():
    """No-forwarding pipe must take more cycles than the arch ISS on fibonacci."""
    arch = ArchCore(imem=imem_from_words(FIBONACCI)).run()
    pipe = run_fibonacci()
    assert pipe.cycles > arch.cycles
