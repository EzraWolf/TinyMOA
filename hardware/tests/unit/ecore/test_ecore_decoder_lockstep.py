"""Exhaustive sandbox isa.decode ↔ Verilator ecore_decoder field lockstep."""

from __future__ import annotations

import os

import cocotb
import pytest
from cocotb.triggers import Timer

from tests import CHECK_DELAY_NS
from tests.common import encode_rv32i as rv32i
from tests.runner import run
from tinymoa_cpu.isa import decode


WIDTH = int(os.environ.get("WIDTH", 32))
REG_NUM = int(os.environ.get("REG_NUM", 32))


def _corpus() -> list[int]:
    """Systematic legal encodings + dense illegal grid for this WIDTH/REG_NUM."""
    words: list[int] = []

    # Legal R-type
    for enc in (
        rv32i.encode_add,
        rv32i.encode_sub,
        rv32i.encode_and,
        rv32i.encode_or,
        rv32i.encode_xor,
        rv32i.encode_sll,
        rv32i.encode_srl,
        rv32i.encode_sra,
        rv32i.encode_slt,
        rv32i.encode_sltu,
    ):
        words.append(enc(3, 1, 2))

    # Legal I-type ALU / shifts
    words.extend(
        [
            rv32i.encode_addi(5, 0, 10),
            rv32i.encode_andi(5, 1, 7),
            rv32i.encode_ori(5, 1, 7),
            rv32i.encode_xori(5, 1, 7),
            rv32i.encode_slti(5, 1, -3),
            rv32i.encode_sltiu(5, 1, 3),
            rv32i.encode_slli(2, 1, 5, width=WIDTH),
            rv32i.encode_srli(2, 1, 5, width=WIDTH),
            rv32i.encode_srai(2, 1, 5, width=WIDTH),
        ]
    )
    if WIDTH >= 64:
        words.extend(
            [
                rv32i.encode_slli(2, 1, 40, width=64),
                rv32i.encode_addiw(3, 2, 3),
                rv32i.encode_slliw(3, 2, 4),
                rv32i.encode_srliw(3, 2, 4),
                rv32i.encode_sraiw(3, 2, 4),
                rv32i.encode_addw(3, 1, 2),
                rv32i.encode_subw(3, 1, 2),
                rv32i.encode_sllw(3, 1, 2),
                rv32i.encode_srlw(3, 1, 2),
                rv32i.encode_sraw(3, 1, 2),
                rv32i.encode_ld(5, 1, 16),
                rv32i.encode_lwu(5, 1, 8),
                rv32i.encode_sd(1, 5, 16),
            ]
        )

    words.extend(
        [
            rv32i.encode_lw(5, 1, 8),
            rv32i.encode_lh(5, 1, 4),
            rv32i.encode_lb(5, 1, 1),
            rv32i.encode_lbu(5, 1, 1),
            rv32i.encode_lhu(5, 1, 2),
            rv32i.encode_sw(1, 5, 8),
            rv32i.encode_sh(1, 5, 4),
            rv32i.encode_sb(1, 5, 1),
            rv32i.encode_jal(1, 16),
            rv32i.encode_jalr(1, 2, 4),
            rv32i.encode_beq(1, 2, 8),
            rv32i.encode_bne(1, 2, 8),
            rv32i.encode_blt(1, 2, 8),
            rv32i.encode_bge(1, 2, 8),
            rv32i.encode_bltu(1, 2, 8),
            rv32i.encode_bgeu(1, 2, 8),
            rv32i.encode_lui(9, 0x80001),
            rv32i.encode_auipc(9, 0x12345),
            rv32i.encode_ecall(),
            rv32i.encode_ebreak(),
            rv32i.encode_fence(0xF, 0xF),
        ]
    )

    # Illegal: compressed / bad quadrant
    for q in (0, 1, 2):
        words.append((0x12345 << 2) | q)

    # Illegal major opcodes (op = instr[6:2])
    valid = {0x00, 0x03, 0x04, 0x05, 0x08, 0x0C, 0x0D, 0x18, 0x19, 0x1B, 0x1C}
    if WIDTH >= 64:
        valid |= {0x06, 0x0E}
    for op in sorted(set(range(32)) - valid):
        words.append((0 << 25) | (1 << 20) | (2 << 15) | (0 << 12) | (3 << 7) | (op << 2) | 0b11)

    # Illegal R-type funct
    words.append(rv32i.encode_r_type(0x01, 2, 1, 0b000, 3, 0x33))
    # Illegal shift
    words.append(rv32i.encode_i_type(0x200 | 5, 1, 0b001, 2, 0x13))

    # RV32: OP-IMM-32 / OP-32 / LD / SD are illegal
    if WIDTH < 64:
        words.append(rv32i.encode_addiw(3, 2, 3))
        words.append(rv32i.encode_addw(3, 1, 2))
        words.append(rv32i.encode_ld(5, 1, 0))
        words.append(rv32i.encode_sd(1, 5, 0))

    # RV32E: high regs illegal
    if REG_NUM == 16:
        words.append(rv32i.encode_add(16, 1, 2))
        words.append(rv32i.encode_add(1, 16, 2))
        words.append(rv32i.encode_add(1, 2, 16))
        words.append(rv32i.encode_sw(1, 16, 0))

    # Dedup while preserving order
    seen: set[int] = set()
    out: list[int] = []
    for w in words:
        w &= 0xFFFFFFFF
        if w not in seen:
            seen.add(w)
            out.append(w)
    return out


async def _assert_lockstep(dut, instr: int) -> None:
    d = decode(instr, width=WIDTH, reg_num=REG_NUM)
    dut.i_instr.value = instr
    await Timer(CHECK_DELAY_NS, "ns")
    assert int(dut.i_instr.value) == instr
    assert int(dut.o_is_illegal.value) == int(d.is_illegal), f"illegal instr={instr:#010x}"
    assert int(dut.o_rf_wen.value) == int(d.rf_wen), f"rf_wen instr={instr:#010x}"
    assert int(dut.o_rf_dst.value) == d.rf_dst, f"rf_dst instr={instr:#010x}"
    assert int(dut.o_rf_src1.value) == d.rf_src1, f"rf_src1 instr={instr:#010x}"
    assert int(dut.o_rf_src2.value) == d.rf_src2, f"rf_src2 instr={instr:#010x}"
    assert int(dut.o_fu_op.value) == int(d.fu_op), f"fu_op instr={instr:#010x}"
    assert int(dut.o_fu_src1.value) == int(d.fu_src1), f"fu_src1 instr={instr:#010x}"
    assert int(dut.o_fu_src2.value) == int(d.fu_src2), f"fu_src2 instr={instr:#010x}"
    assert int(dut.o_imm.value) == (d.imm & 0xFFFFFFFF), f"imm instr={instr:#010x}"
    assert int(dut.o_mem_ren.value) == int(d.mem_ren), f"mem_ren instr={instr:#010x}"
    assert int(dut.o_mem_wen.value) == int(d.mem_wen), f"mem_wen instr={instr:#010x}"
    assert int(dut.o_wb_sel.value) == int(d.wb_sel), f"wb_sel instr={instr:#010x}"
    assert int(dut.o_funct3.value) == d.funct3, f"funct3 instr={instr:#010x}"
    assert int(dut.o_is_load.value) == int(d.is_load), f"is_load instr={instr:#010x}"
    assert int(dut.o_is_store.value) == int(d.is_store), f"is_store instr={instr:#010x}"
    assert int(dut.o_is_jump.value) == int(d.is_jump), f"is_jump instr={instr:#010x}"
    assert int(dut.o_is_branch.value) == int(d.is_branch), f"is_branch instr={instr:#010x}"
    assert int(dut.o_is_fence.value) == int(d.is_fence), f"is_fence instr={instr:#010x}"
    assert int(dut.o_is_ecall.value) == int(d.is_ecall), f"is_ecall instr={instr:#010x}"
    assert int(dut.o_is_ebreak.value) == int(d.is_ebreak), f"is_ebreak instr={instr:#010x}"


@cocotb.test()
async def decoder_lockstep_corpus(dut):
    corpus = _corpus()
    assert len(corpus) >= 40
    for instr in corpus:
        await _assert_lockstep(dut, instr)


@pytest.mark.parametrize(
    "p",
    [
        pytest.param({"WIDTH": 32, "REG_NUM": 32}, id="rv32i"),
        pytest.param({"WIDTH": 32, "REG_NUM": 16}, id="rv32e"),
        pytest.param({"WIDTH": 64, "REG_NUM": 32}, id="rv64i"),
        pytest.param({"WIDTH": 64, "REG_NUM": 16}, id="rv64e"),
    ],
)
def test_ecore_decoder_lockstep(p):
    run(
        "ecore",
        "decoder",
        [
            "~ecore/pkgs/ecore_pkg_cfg.sv",
            "~ecore/pkgs/ecore_pkg_alu.sv",
            "~ecore/ecore_decoder.sv",
        ],
        test_name="lockstep",
        params=p,
    )
