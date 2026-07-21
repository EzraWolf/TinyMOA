import cocotb

from tests.runner import run


@cocotb.test()
async def xlen_is_valid(dut):
    assert int(dut.o_xlen.value) in (32, 64)


@cocotb.test()
async def flen_is_valid(dut):
    flen = int(dut.o_flen.value)
    assert flen in (0, 32, 64)
    assert (
        flen == 64
        if bool(dut.o_use_ext_d.value)
        else 32
        if bool(dut.o_use_ext_f.value)
        else 0
    )


@cocotb.test()
async def ialign_is_valid(dut):
    ialign = int(dut.o_ialign.value)
    assert ialign in (16, 32)
    assert ialign == 16 if bool(dut.o_use_ext_zca.value) else 32


@cocotb.test()
async def base_isa_is_valid(dut):
    assert bool(dut.o_use_base_i.value) != bool(dut.o_use_base_e.value)


@cocotb.test()
async def register_count_matches_base(dut):
    assert (
        int(dut.o_arch_regfile_num.value) == 16 if bool(dut.o_use_base_e.value) else 32
    )


@cocotb.test()
async def mmus_are_mutually_exclusive(dut):
    assert not (bool(dut.o_use_mmu_sv32.value) and bool(dut.o_use_mmu_sv39.value))


@cocotb.test()
async def rv32_requires_sv32(dut):
    assert not bool(dut.o_use_mmu_sv32.value) or int(dut.o_xlen.value) == 32


@cocotb.test()
async def rv64_requires_sv39(dut):
    assert not bool(dut.o_use_mmu_sv39.value) or int(dut.o_xlen.value) == 64


@cocotb.test()
async def linux_selects_sv32_for_rv32(dut):
    assert bool(dut.o_use_mmu_sv32.value) == (
        bool(dut.o_use_linux.value) and int(dut.o_xlen.value) == 32
    )


@cocotb.test()
async def linux_selects_sv39_for_rv64(dut):
    assert bool(dut.o_use_mmu_sv39.value) == (
        bool(dut.o_use_linux.value) and int(dut.o_xlen.value) == 64
    )


@cocotb.test()
async def d_requires_f(dut):
    assert not bool(dut.o_use_ext_d.value) or bool(dut.o_use_ext_f.value)


@cocotb.test()
async def zfbfmin_requires_f(dut):
    assert not bool(dut.o_use_ext_zfbfmin.value) or bool(dut.o_use_ext_f.value)


@cocotb.test()
async def f_requires_zicsr(dut):
    assert not bool(dut.o_use_ext_f.value) or bool(dut.o_use_ext_zicsr.value)


@cocotb.test()
async def zca_matches_compressed_extensions(dut):
    assert bool(dut.o_use_ext_zca.value) == bool(dut.o_use_ext_c.value) or bool(
        dut.o_use_ext_zcb.value
    )


@cocotb.test()
async def linux_requires_base_i(dut):
    assert not bool(dut.o_use_linux.value) or bool(dut.o_use_base_i.value)


@cocotb.test()
async def linux_enables_required_extensions(dut):
    if bool(dut.o_use_linux.value):
        assert bool(dut.o_use_ext_zfbfmin.value)
        assert bool(dut.o_use_ext_zifencei.value)
        assert bool(dut.o_use_ext_zicond.value)
        assert bool(dut.o_use_ext_zcb.value)
        assert bool(dut.o_use_ext_zbb.value)
        assert bool(dut.o_use_ext_c.value)
        assert bool(dut.o_use_ext_d.value)
        assert bool(dut.o_use_ext_f.value)
        assert bool(dut.o_use_ext_zicsr.value)
        assert bool(dut.o_use_ext_a.value)
        assert bool(dut.o_use_ext_m.value)


def test_ecore_cfg():
    run(
        "ecore",
        "cfg",
        ["~ecore/pkgs/ecore_pkg_cfg.sv"],
    )
