"""Shared encode cases for riscv-opcodes + llvm-mc gates."""

from __future__ import annotations

from dataclasses import dataclass

from tinymoa_cpu import encode as enc


@dataclass(frozen=True)
class EncodeCase:
    mnemonic: str  # riscv-opcodes key
    word: int
    asm: str  # llvm-mc assembly (one instruction)
    xlen: int = 32  # llvm triple: 32 -> riscv32, 64 -> riscv64


def encode_gate_cases() -> list[EncodeCase]:
    """Representative encodings covering the public encode_* surface."""
    return [
        EncodeCase("add", enc.encode_add(3, 1, 2), "add x3, x1, x2"),
        EncodeCase("sub", enc.encode_sub(3, 1, 2), "sub x3, x1, x2"),
        EncodeCase("and", enc.encode_and(3, 1, 2), "and x3, x1, x2"),
        EncodeCase("or", enc.encode_or(3, 1, 2), "or x3, x1, x2"),
        EncodeCase("xor", enc.encode_xor(3, 1, 2), "xor x3, x1, x2"),
        EncodeCase("sll", enc.encode_sll(3, 1, 2), "sll x3, x1, x2"),
        EncodeCase("srl", enc.encode_srl(3, 1, 2), "srl x3, x1, x2"),
        EncodeCase("sra", enc.encode_sra(3, 1, 2), "sra x3, x1, x2"),
        EncodeCase("slt", enc.encode_slt(3, 1, 2), "slt x3, x1, x2"),
        EncodeCase("sltu", enc.encode_sltu(3, 1, 2), "sltu x3, x1, x2"),
        EncodeCase("addi", enc.encode_addi(5, 0, 10), "addi x5, x0, 10"),
        EncodeCase("andi", enc.encode_andi(5, 1, 7), "andi x5, x1, 7"),
        EncodeCase("ori", enc.encode_ori(5, 1, 7), "ori x5, x1, 7"),
        EncodeCase("xori", enc.encode_xori(5, 1, 7), "xori x5, x1, 7"),
        EncodeCase("slti", enc.encode_slti(5, 1, -3), "slti x5, x1, -3"),
        EncodeCase("sltiu", enc.encode_sltiu(5, 1, 3), "sltiu x5, x1, 3"),
        EncodeCase("slli", enc.encode_slli(2, 1, 5, width=32), "slli x2, x1, 5"),
        EncodeCase("srli", enc.encode_srli(2, 1, 5, width=32), "srli x2, x1, 5"),
        EncodeCase("srai", enc.encode_srai(2, 1, 5, width=32), "srai x2, x1, 5"),
        EncodeCase("slli", enc.encode_slli(2, 1, 40, width=64), "slli x2, x1, 40", 64),
        EncodeCase("srli", enc.encode_srli(2, 1, 40, width=64), "srli x2, x1, 40", 64),
        EncodeCase("srai", enc.encode_srai(2, 1, 40, width=64), "srai x2, x1, 40", 64),
        EncodeCase("addiw", enc.encode_addiw(3, 2, 3), "addiw x3, x2, 3", 64),
        EncodeCase("slliw", enc.encode_slliw(3, 2, 4), "slliw x3, x2, 4", 64),
        EncodeCase("srliw", enc.encode_srliw(3, 2, 4), "srliw x3, x2, 4", 64),
        EncodeCase("sraiw", enc.encode_sraiw(3, 2, 4), "sraiw x3, x2, 4", 64),
        EncodeCase("addw", enc.encode_addw(3, 1, 2), "addw x3, x1, x2", 64),
        EncodeCase("subw", enc.encode_subw(3, 1, 2), "subw x3, x1, x2", 64),
        EncodeCase("sllw", enc.encode_sllw(3, 1, 2), "sllw x3, x1, x2", 64),
        EncodeCase("srlw", enc.encode_srlw(3, 1, 2), "srlw x3, x1, x2", 64),
        EncodeCase("sraw", enc.encode_sraw(3, 1, 2), "sraw x3, x1, x2", 64),
        EncodeCase("lw", enc.encode_lw(5, 1, 8), "lw x5, 8(x1)"),
        EncodeCase("lh", enc.encode_lh(5, 1, 4), "lh x5, 4(x1)"),
        EncodeCase("lb", enc.encode_lb(5, 1, 1), "lb x5, 1(x1)"),
        EncodeCase("lbu", enc.encode_lbu(5, 1, 1), "lbu x5, 1(x1)"),
        EncodeCase("lhu", enc.encode_lhu(5, 1, 2), "lhu x5, 2(x1)"),
        EncodeCase("ld", enc.encode_ld(5, 1, 16), "ld x5, 16(x1)", 64),
        EncodeCase("lwu", enc.encode_lwu(5, 1, 8), "lwu x5, 8(x1)", 64),
        EncodeCase("sw", enc.encode_sw(1, 5, 8), "sw x5, 8(x1)"),
        EncodeCase("sh", enc.encode_sh(1, 5, 4), "sh x5, 4(x1)"),
        EncodeCase("sb", enc.encode_sb(1, 5, 1), "sb x5, 1(x1)"),
        EncodeCase("sd", enc.encode_sd(1, 5, 16), "sd x5, 16(x1)", 64),
        EncodeCase("jal", enc.encode_jal(1, 16), "jal x1, 16"),
        EncodeCase("jalr", enc.encode_jalr(1, 2, 4), "jalr x1, 4(x2)"),
        EncodeCase("beq", enc.encode_beq(1, 2, 8), "beq x1, x2, 8"),
        EncodeCase("bne", enc.encode_bne(1, 2, 8), "bne x1, x2, 8"),
        EncodeCase("blt", enc.encode_blt(1, 2, 8), "blt x1, x2, 8"),
        EncodeCase("bge", enc.encode_bge(1, 2, 8), "bge x1, x2, 8"),
        EncodeCase("bltu", enc.encode_bltu(1, 2, 8), "bltu x1, x2, 8"),
        EncodeCase("bgeu", enc.encode_bgeu(1, 2, 8), "bgeu x1, x2, 8"),
        EncodeCase("lui", enc.encode_lui(9, 0x80001), "lui x9, 0x80001"),
        EncodeCase("auipc", enc.encode_auipc(9, 0x12345), "auipc x9, 0x12345"),
        EncodeCase("ecall", enc.encode_ecall(), "ecall"),
        EncodeCase("ebreak", enc.encode_ebreak(), "ebreak"),
        EncodeCase("fence", enc.encode_fence(0xF, 0xF), "fence iorw, iorw"),
    ]
