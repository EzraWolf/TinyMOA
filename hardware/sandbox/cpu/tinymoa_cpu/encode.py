"""Sandbox-owned RV32I/I-family encoder (production encode path for tinymoa_cpu programs)."""


def encode_r_type(funct7, rs2, rs1, funct3, rd, opcode):
    """funct7[31:25] | rs2[24:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0]"""
    return (
        (funct7 << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode
    )


def encode_i_type(imm, rs1, funct3, rd, opcode):
    """imm[31:20] | rs1[19:15] | funct3[14:12] | rd[11:7] | opcode[6:0]"""
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def encode_s_type(imm, rs2, rs1, funct3, opcode):
    """imm[31:25] | rs2[24:20] | rs1[19:15] | funct3[14:12] | imm[11:7] | opcode[6:0]"""
    return (
        (((imm >> 5) & 0x7F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | ((imm & 0x1F) << 7)
        | opcode
    )


def encode_b_type(imm, rs2, rs1, funct3, opcode):
    """imm[12|10:5] | rs2 | rs1 | funct3 | imm[4:1|11] | opcode"""
    return (
        (((imm >> 12) & 1) << 31)
        | (((imm >> 5) & 0x3F) << 25)
        | (rs2 << 20)
        | (rs1 << 15)
        | (funct3 << 12)
        | (((imm >> 1) & 0xF) << 8)
        | (((imm >> 11) & 1) << 7)
        | opcode
    )


def encode_u_type(imm, rd, opcode):
    """imm[31:12] | rd[11:7] | opcode[6:0]"""
    return ((imm & 0xFFFFF) << 12) | (rd << 7) | opcode


def encode_j_type(imm, rd, opcode):
    """imm[20|10:1|11|19:12] | rd | opcode"""
    return (
        (((imm >> 20) & 1) << 31)
        | (((imm >> 1) & 0x3FF) << 21)
        | (((imm >> 11) & 1) << 20)
        | (((imm >> 12) & 0xFF) << 12)
        | (rd << 7)
        | opcode
    )


### R-Type ALU ops ###


def encode_add(rd, rs1, rs2):
    """R-Type; ADD rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x0, rd, 0x33)


def encode_sub(rd, rs1, rs2):
    """R-Type; SUB rd, rs1, rs2"""
    return encode_r_type(0x20, rs2, rs1, 0x0, rd, 0x33)


def encode_and(rd, rs1, rs2):
    """R-Type; AND rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x7, rd, 0x33)


def encode_or(rd, rs1, rs2):
    """R-Type; OR rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x6, rd, 0x33)


def encode_xor(rd, rs1, rs2):
    """R-Type; XOR rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x4, rd, 0x33)


def encode_sll(rd, rs1, rs2):
    """R-Type; SLL rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x1, rd, 0x33)


def encode_srl(rd, rs1, rs2):
    """R-Type; SRL rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x5, rd, 0x33)


def encode_sra(rd, rs1, rs2):
    """R-Type; SRA rd, rs1, rs2"""
    return encode_r_type(0x20, rs2, rs1, 0x5, rd, 0x33)


def encode_slt(rd, rs1, rs2):
    """R-Type; SLT rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x2, rd, 0x33)


def encode_sltu(rd, rs1, rs2):
    """R-Type; SLTU rd, rs1, rs2"""
    return encode_r_type(0x00, rs2, rs1, 0x3, rd, 0x33)


### I-Type ALU ops ###


def encode_addi(rd, rs1, imm):
    """I-Type; ADDI rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x0, rd, 0x13)


def encode_andi(rd, rs1, imm):
    """I-Type; ANDI rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x7, rd, 0x13)


def encode_ori(rd, rs1, imm):
    """I-Type; ORI rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x6, rd, 0x13)


def encode_xori(rd, rs1, imm):
    """I-Type; XORI rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x4, rd, 0x13)


def encode_slti(rd, rs1, imm):
    """I-Type; SLTI rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x2, rd, 0x13)


def encode_sltiu(rd, rs1, imm):
    """I-Type; SLTIU rd, rs1, imm"""
    return encode_i_type(imm, rs1, 0x3, rd, 0x13)


def encode_slli(rd, rs1, shamt):
    """I-Type; SLLI rd, rs1, shamt"""
    return encode_i_type(shamt & 0x1F, rs1, 0x1, rd, 0x13)


def encode_srli(rd, rs1, shamt):
    """I-Type; SRLI rd, rs1, shamt"""
    return encode_i_type(shamt & 0x1F, rs1, 0x5, rd, 0x13)


def encode_srai(rd, rs1, shamt):
    """I-Type; SRAI rd, rs1, shamt"""
    return encode_i_type(0x400 | (shamt & 0x1F), rs1, 0x5, rd, 0x13)


def encode_addiw(rd, rs1, imm):
    """I-Type; ADDIW rd, rs1, imm (RV64 OP-IMM-32). Illegal on RV32."""
    return encode_i_type(imm, rs1, 0x0, rd, 0x1B)


### load ops ###


def encode_lw(rd, rs1, imm):
    """I-Type; LW rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x2, rd, 0x03)


def encode_lh(rd, rs1, imm):
    """I-Type; LH rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x1, rd, 0x03)


def encode_lb(rd, rs1, imm):
    """I-Type; LB rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x0, rd, 0x03)


def encode_lbu(rd, rs1, imm):
    """I-Type; LBU rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x4, rd, 0x03)


def encode_lhu(rd, rs1, imm):
    """I-Type; LHU rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x5, rd, 0x03)


### store ops ###


def encode_sw(rs1, rs2, imm):
    """S-Type; SW rs2, imm(rs1)"""
    return encode_s_type(imm, rs2, rs1, 0x2, 0x23)


def encode_sh(rs1, rs2, imm):
    """S-Type; SH rs2, imm(rs1)"""
    return encode_s_type(imm, rs2, rs1, 0x1, 0x23)


def encode_sb(rs1, rs2, imm):
    """S-Type; SB rs2, imm(rs1)"""
    return encode_s_type(imm, rs2, rs1, 0x0, 0x23)


### jump ops ###


def encode_jal(rd, imm):
    """J-Type; JAL rd, imm"""
    return encode_j_type(imm, rd, 0x6F)


def encode_jalr(rd, rs1, imm):
    """I-Type; JALR rd, imm(rs1)"""
    return encode_i_type(imm, rs1, 0x0, rd, 0x67)


### branch ops ###


def encode_beq(rs1, rs2, imm):
    """B-Type; BEQ rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x0, 0x63)


def encode_bne(rs1, rs2, imm):
    """B-Type; BNE rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x1, 0x63)


def encode_blt(rs1, rs2, imm):
    """B-Type; BLT rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x4, 0x63)


def encode_bge(rs1, rs2, imm):
    """B-Type; BGE rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x5, 0x63)


def encode_bltu(rs1, rs2, imm):
    """B-Type; BLTU rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x6, 0x63)


def encode_bgeu(rs1, rs2, imm):
    """B-Type; BGEU rs1, rs2, imm"""
    return encode_b_type(imm, rs2, rs1, 0x7, 0x63)


### upper immediate ops ###


def encode_lui(rd, imm):
    """U-Type; LUI rd, imm"""
    return encode_u_type(imm, rd, 0x37)


def encode_auipc(rd, imm):
    """U-Type; AUIPC rd, imm"""
    return encode_u_type(imm, rd, 0x17)


### system ops ###


def encode_ecall():
    """ECALL"""
    return 0x00000073


def encode_ebreak():
    """EBREAK"""
    return 0x00100073


def encode_fence(pred, succ):
    """I-Type; FENCE pred, succ"""
    return encode_i_type((pred << 4) | succ, 0, 0x0, 0, 0x0F)
