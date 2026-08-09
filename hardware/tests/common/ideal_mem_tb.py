"""Shared IdealMem protocol helpers for cocotb ecore harnesses."""

from __future__ import annotations

from tinymoa_cpu.encode import encode_jal
from tinymoa_cpu.mem import FILL_INSTR


def load_imem(program: list[int]) -> dict[int, int]:
    return {i * 4: instr & 0xFFFFFFFF for i, instr in enumerate(program)}


def drive_imem(dut, instr_mem: dict[int, int], fill: int = FILL_INSTR) -> None:
    pc = int(dut.o_imem_addr.value)
    dut.i_imem_rdata.value = instr_mem.get(pc, fill)


def service_dmem(dut, data_mem: dict[int, int], *, width: int = 32) -> None:
    if not dut.o_dmem_valid.value:
        return
    addr = int(dut.o_dmem_addr.value)
    nbytes = width // 8
    if dut.o_dmem_wen.value:
        data = int(dut.o_dmem_wdata.value)
        mask = int(dut.o_dmem_wmask.value)
        word = data_mem.get(addr, 0)
        for i in range(nbytes):
            if mask & (1 << i):
                word &= ~(0xFF << (i * 8))
                word |= ((data >> (i * 8)) & 0xFF) << (i * 8)
        data_mem[addr] = word
    if dut.o_dmem_ren.value:
        dut.i_dmem_rdata.value = data_mem.get(addr, 0)


# keep encode_jal import used if callers want the fill symbol
assert encode_jal(0, 0) == FILL_INSTR
