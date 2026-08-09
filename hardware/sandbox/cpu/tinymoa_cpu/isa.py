"""RV32I/RV64I decode matching hardware/rtl/ecore/ecore_decoder.veryl."""

from __future__ import annotations

from dataclasses import dataclass

from tinymoa_cpu.types import AluOp, FuSrc1, FuSrc2, WbSel


def _sext32(imm: int, bits: int) -> int:
    imm &= (1 << bits) - 1
    if imm & (1 << (bits - 1)):
        imm -= 1 << bits
    return imm & 0xFFFFFFFF


@dataclass(frozen=True)
class Decoded:
    raw: int
    rf_wen: bool
    rf_dst: int
    rf_src1: int
    rf_src2: int
    fu_op: AluOp
    fu_src1: FuSrc1
    fu_src2: FuSrc2
    imm: int  # 32-bit pattern; sign-extended to XLEN at use
    mem_ren: bool
    mem_wen: bool
    wb_sel: WbSel
    funct3: int
    is_load: bool
    is_store: bool
    is_jump: bool
    is_branch: bool
    is_fence: bool
    is_ecall: bool
    is_ebreak: bool
    is_illegal: bool


def decode(instr: int, width: int = 32, reg_num: int = 32) -> Decoded:
    instr &= 0xFFFFFFFF
    funct7 = (instr >> 25) & 0x7F
    funct6 = (instr >> 26) & 0x3F
    rs2 = (instr >> 20) & 0x1F
    rs1 = (instr >> 15) & 0x1F
    funct3 = (instr >> 12) & 0x7
    rd = (instr >> 7) & 0x1F
    op = (instr >> 2) & 0x1F
    quad = instr & 0x3

    imm_i = _sext32(instr >> 20, 12)
    imm_s = _sext32(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
    imm_b = _sext32(
        ((instr >> 31) << 12)
        | (((instr >> 7) & 1) << 11)
        | (((instr >> 25) & 0x3F) << 5)
        | (((instr >> 8) & 0xF) << 1),
        13,
    )
    imm_j = _sext32(
        ((instr >> 31) << 20)
        | (((instr >> 12) & 0xFF) << 12)
        | (((instr >> 20) & 1) << 11)
        | (((instr >> 21) & 0x3FF) << 1),
        21,
    )
    imm_u = instr & 0xFFFFF000

    fu_op = AluOp.ADD
    fu_src1 = FuSrc1.NONE
    fu_src2 = FuSrc2.NONE
    imm = 0
    wb_sel = WbSel.NONE
    is_load = False
    is_store = False
    is_jump = False
    is_branch = False
    is_fence = False
    is_ecall = False
    is_ebreak = False
    is_illegal = False
    out_funct3 = 0

    if quad != 0b11:
        is_illegal = True
    else:
        fu_src1 = FuSrc1.REG
        fu_src2 = FuSrc2.REG
        wb_sel = WbSel.FU
        out_funct3 = funct3

        if op == 0b01100:  # R-type
            key = (funct3, funct7)
            table = {
                (0b000, 0b0000000): AluOp.ADD,
                (0b000, 0b0100000): AluOp.SUB,
                (0b111, 0b0000000): AluOp.AND,
                (0b110, 0b0000000): AluOp.OR,
                (0b100, 0b0000000): AluOp.XOR,
                (0b001, 0b0000000): AluOp.SLL,
                (0b101, 0b0000000): AluOp.SRL,
                (0b101, 0b0100000): AluOp.SRA,
                (0b010, 0b0000000): AluOp.SLT,
                (0b011, 0b0000000): AluOp.SLTU,
            }
            if key in table:
                fu_op = table[key]
            else:
                is_illegal = True
        elif op == 0b00100:  # I-type ALU
            fu_src2 = FuSrc2.IMM
            imm = imm_i
            if funct3 == 0b000:
                fu_op = AluOp.ADD
            elif funct3 == 0b111:
                fu_op = AluOp.AND
            elif funct3 == 0b110:
                fu_op = AluOp.OR
            elif funct3 == 0b100:
                fu_op = AluOp.XOR
            elif funct3 == 0b010:
                fu_op = AluOp.SLT
            elif funct3 == 0b011:
                fu_op = AluOp.SLTU
            elif funct3 in (0b001, 0b101):
                if width >= 64:
                    key6 = (funct3, funct6)
                    table6 = {
                        (0b001, 0b000000): AluOp.SLL,
                        (0b101, 0b000000): AluOp.SRL,
                        (0b101, 0b010000): AluOp.SRA,
                    }
                    if key6 in table6:
                        fu_op = table6[key6]
                    else:
                        is_illegal = True
                else:
                    key = (funct3, funct7)
                    table = {
                        (0b001, 0b0000000): AluOp.SLL,
                        (0b101, 0b0000000): AluOp.SRL,
                        (0b101, 0b0100000): AluOp.SRA,
                    }
                    if key in table:
                        fu_op = table[key]
                    else:
                        is_illegal = True
            else:
                is_illegal = True
        elif op == 0b00000:  # load
            fu_src2 = FuSrc2.IMM
            imm = imm_i
            wb_sel = WbSel.MEM
            is_load = True
            if funct3 in (0b011, 0b110) and width <= 32:
                is_illegal = True
            elif funct3 not in (0b000, 0b001, 0b010, 0b100, 0b101, 0b011, 0b110):
                is_illegal = True
        elif op == 0b01000:  # store
            fu_src2 = FuSrc2.IMM
            imm = imm_s
            wb_sel = WbSel.NONE
            is_store = True
            if funct3 == 0b011 and width < 64:
                is_illegal = True
            elif funct3 not in (0b000, 0b001, 0b010, 0b011):
                is_illegal = True
        elif op == 0b11011:  # JAL
            fu_src1 = FuSrc1.PC
            fu_src2 = FuSrc2.IMM
            imm = imm_j
            wb_sel = WbSel.PC
            is_jump = True
        elif op == 0b11001:  # JALR
            fu_src1 = FuSrc1.REG
            fu_src2 = FuSrc2.IMM
            imm = imm_i
            wb_sel = WbSel.PC
            is_jump = True
            if funct3 != 0:
                is_illegal = True
        elif op == 0b11000:  # branch
            wb_sel = WbSel.NONE
            imm = imm_b
            is_branch = True
            if funct3 not in (0b000, 0b001, 0b100, 0b101, 0b110, 0b111):
                is_illegal = True
        elif op in (0b00101, 0b01101):  # AUIPC / LUI
            fu_src1 = FuSrc1.PC if ((op >> 3) & 1) == 0 else FuSrc1.NONE
            fu_src2 = FuSrc2.IMM
            wb_sel = WbSel.FU
            imm = imm_u
        elif op == 0b00011:  # FENCE
            fu_src1 = FuSrc1.NONE
            fu_src2 = FuSrc2.NONE
            wb_sel = WbSel.NONE
            if funct3 == 0:
                is_fence = True
            else:
                is_illegal = True
        elif op == 0b11100:  # SYSTEM
            fu_src1 = FuSrc1.NONE
            fu_src2 = FuSrc2.NONE
            wb_sel = WbSel.NONE
            if instr == 0x00000073:
                is_ecall = True
            elif instr == 0x00100073:
                is_ebreak = True
            else:
                is_illegal = True
        elif op == 0b00110:  # OP-IMM-32
            if width < 64:
                is_illegal = True
            else:
                fu_src2 = FuSrc2.IMM
                imm = imm_i
                if funct3 == 0b000:
                    fu_op = AluOp.ADDW
                elif funct3 in (0b001, 0b101):
                    key = (funct3, funct7)
                    table = {
                        (0b001, 0b0000000): AluOp.SLLW,
                        (0b101, 0b0000000): AluOp.SRLW,
                        (0b101, 0b0100000): AluOp.SRAW,
                    }
                    if key in table:
                        fu_op = table[key]
                    else:
                        is_illegal = True
                else:
                    is_illegal = True
        elif op == 0b01110:  # OP-32
            if width < 64:
                is_illegal = True
            else:
                key = (funct3, funct7)
                table = {
                    (0b000, 0b0000000): AluOp.ADDW,
                    (0b000, 0b0100000): AluOp.SUBW,
                    (0b001, 0b0000000): AluOp.SLLW,
                    (0b101, 0b0000000): AluOp.SRLW,
                    (0b101, 0b0100000): AluOp.SRAW,
                }
                if key in table:
                    fu_op = table[key]
                else:
                    is_illegal = True
        else:
            is_illegal = True

    if reg_num == 16:
        uses_rs1 = fu_src1 == FuSrc1.REG and (rs1 & 0x10)
        uses_rs2 = (fu_src2 == FuSrc2.REG or is_store) and (rs2 & 0x10)
        uses_rd = wb_sel != WbSel.NONE and (rd & 0x10)
        if uses_rs1 or uses_rs2 or uses_rd:
            is_illegal = True

    if is_illegal:
        fu_op = AluOp.ADD
        fu_src1 = FuSrc1.NONE
        fu_src2 = FuSrc2.NONE
        imm = 0
        wb_sel = WbSel.NONE
        is_load = is_store = is_jump = is_branch = False

    mem_ren = is_load or wb_sel == WbSel.MEM
    mem_wen = is_store
    rf_src1 = rs1 if fu_src1 == FuSrc1.REG else 0
    rf_src2 = rs2 if (fu_src2 == FuSrc2.REG or is_store) else 0
    rf_dst = rd if wb_sel != WbSel.NONE else 0
    rf_wen = wb_sel != WbSel.NONE

    return Decoded(
        raw=instr,
        rf_wen=rf_wen,
        rf_dst=rf_dst,
        rf_src1=rf_src1,
        rf_src2=rf_src2,
        fu_op=fu_op,
        fu_src1=fu_src1,
        fu_src2=fu_src2,
        imm=imm,
        mem_ren=mem_ren,
        mem_wen=mem_wen,
        wb_sel=wb_sel,
        # Match RTL: o_funct3 is whatever was assigned before illegal clear (0 if never entered a legal op path).
        funct3=out_funct3,
        is_load=is_load,
        is_store=is_store,
        is_jump=is_jump,
        is_branch=is_branch,
        is_fence=is_fence,
        is_ecall=is_ecall,
        is_ebreak=is_ebreak,
        is_illegal=is_illegal,
    )
