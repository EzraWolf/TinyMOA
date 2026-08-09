"""Sandbox unit + property tests."""

from tinymoa_cpu.arch import ArchCore
from tinymoa_cpu.lockstep import compare_retires
from tinymoa_cpu.mem import IdealMem, imem_from_words
from tinymoa_cpu.programs import (
    BRANCH_RESULT,
    BRANCH_RESULT_ADDR,
    BRANCH_STORM,
    E_HALT_PC,
    E_RESULT_ADDR,
    E_RESULT_E,
    E_RESULT_I,
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    LOAD_STORE_PARTIAL,
    LSU_RESULT,
    LSU_RESULT_ADDR,
    RAW_CHAIN,
    RAW_RESULT,
    RAW_RESULT_ADDR,
    RV32E_HIGHREG,
    RV64_W,
    W64_HALT_PC,
    W64_RESULT,
    W64_RESULT_ADDR,
    run_branch_storm,
    run_fibonacci,
    run_load_store_partial,
    run_raw_chain,
    run_rv32e_highreg,
    run_rv64_w,
    xlen_addr,
)
from tinymoa_cpu.regfile import RegFile
from tinymoa_cpu.spike import compare_spike_to_arch
from tinymoa_cpu.top import Core, RetireEvent


def test_regfile_x0_hardwired_on_read():
    rf = RegFile()
    rf.poison(0, 0xDEADBEEF)
    assert rf.read(0) == 0
    rf.write(0, 0xCAFEBABE)
    assert rf.read(0) == 0


def test_fibonacci_arch_iss():
    r = ArchCore(mem=IdealMem(imem=imem_from_words(FIBONACCI))).run()
    assert r.dmem.get(xlen_addr(FIB_RESULT_ADDR, 32)) == FIB_RESULT


def test_fibonacci_cycle_model():
    r = run_fibonacci()
    assert r.dmem.get(xlen_addr(FIB_RESULT_ADDR, 32)) == FIB_RESULT
    assert r.stores[-1][0] == xlen_addr(FIB_RESULT_ADDR, 32)


def test_pipeline_matches_arch_architectural_state():
    mem = IdealMem(imem=imem_from_words(FIBONACCI))
    arch = ArchCore(mem=IdealMem(imem=dict(mem.imem))).run()
    pipe = Core(mem=IdealMem(imem=dict(mem.imem))).run(halt_pc=FIB_HALT_PC)
    addr = xlen_addr(FIB_RESULT_ADDR, 32)
    assert pipe.dmem.get(addr) == arch.dmem.get(addr)
    assert pipe.dmem.get(addr) == FIB_RESULT


def test_raw_hazard_extends_runtime_vs_arch():
    arch = ArchCore(mem=IdealMem(imem=imem_from_words(FIBONACCI))).run()
    pipe = run_fibonacci()
    assert pipe.cycles > arch.cycles


def test_directed_programs_dmem():
    assert run_raw_chain().dmem.get(xlen_addr(RAW_RESULT_ADDR, 32)) == RAW_RESULT
    assert run_branch_storm().dmem.get(xlen_addr(BRANCH_RESULT_ADDR, 32)) == BRANCH_RESULT
    assert run_load_store_partial().dmem.get(xlen_addr(LSU_RESULT_ADDR, 32)) == LSU_RESULT


def test_rv32e_highreg_depth_sensitive():
    addr = xlen_addr(E_RESULT_ADDR, 32)
    e = run_rv32e_highreg(depth=16)
    i = run_rv32e_highreg(depth=32)
    assert e.dmem.get(addr, 0) == E_RESULT_E
    assert i.dmem.get(addr, 0) == E_RESULT_I
    assert not any(r.rd == 16 for r in e.retires)
    assert any(r.rd == 16 and r.value == 8 for r in i.retires)


def test_rv64_addiw_width_sensitive():
    w32 = run_rv64_w(width=32)
    w64 = run_rv64_w(width=64)
    assert w32.regs[3] == 0
    assert not any(r.rd == 3 for r in w32.retires)
    assert w64.regs[3] == W64_RESULT
    assert w64.dmem.get(xlen_addr(W64_RESULT_ADDR, 64)) == W64_RESULT


def test_pipe_retire_matches_arch_on_fib():
    arch = ArchCore(mem=IdealMem(imem=imem_from_words(FIBONACCI))).run()
    pipe = run_fibonacci()
    compare_retires(pipe.retires, arch.retires)


def test_spike_matches_arch_fibonacci():
    arch = ArchCore(mem=IdealMem(imem=imem_from_words(FIBONACCI))).run()
    compare_spike_to_arch(FIBONACCI, arch.retires, width=32, depth=32)


def test_spike_matches_arch_raw_and_branch():
    for words in (RAW_CHAIN, BRANCH_STORM, LOAD_STORE_PARTIAL):
        arch = ArchCore(mem=IdealMem(imem=imem_from_words(words))).run()
        compare_spike_to_arch(words, arch.retires, width=32, depth=32)


def test_spike_compare_rejects_arch_missing_write():
    """Regression: arch rd=None must not skip a Spike GPR write."""
    words = [0x00A00293, 0x0000006F]  # addi t0,x0,10; halt
    fake = [RetireEvent(0, None, None), RetireEvent(4, None, None)]
    try:
        compare_spike_to_arch(words, fake, width=32, depth=32)
    except AssertionError as e:
        assert "rd" in str(e)
    else:
        raise AssertionError("expected spike/arch rd mismatch")
