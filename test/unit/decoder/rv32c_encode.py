# ============================================================================
# RV32C Compressed (16b) Instruction Encoding Functions
# ============================================================================


def encode_cr_type(funct4, rd_rs1, rs2, op):
    """
    Encode CR-Type (Compressed Register):
    funct4[15:12] | rd/rs1[11:7] | rs2[6:2] | op[1:0]
    """
    return (funct4 << 12) | (rd_rs1 << 7) | (rs2 << 2) | op


def encode_ci_type(funct3, imm_hi, rd_rs1, imm_lo, op):
    """
    Encode CI-Type (Compressed Immediate):
    funct3[15:13] | imm[12] | rd/rs1[11:7] | imm[6:2] | op[1:0]
    """
    return (funct3 << 13) | (imm_hi << 12) | (rd_rs1 << 7) | (imm_lo << 2) | op


def encode_css_type(funct3, imm, rs2, op):
    """
    Encode CSS-Type (Compressed Stack-relative Store):
    funct3[15:13] | imm[12:7] | rs2[6:2] | op[1:0]
    """
    return (funct3 << 13) | (imm << 7) | (rs2 << 2) | op


def encode_ciw_type(funct3, imm, rd_p, op):
    """
    Encode CIW-Type (Compressed Wide Immediate):
    funct3[15:13] | imm[12:5] | rd'[4:2] | op[1:0]
    rd' indicates compressed register (x8-x15)
    """
    return (funct3 << 13) | (imm << 5) | (rd_p << 2) | op


def encode_cl_type(funct3, imm_hi, rs1_p, imm_lo, rd_p, op):
    """
    Encode CL-Type (Compressed Load):
    funct3[15:13] | imm[12:10] | rs1'[9:7] | imm[6:5] | rd'[4:2] | op[1:0]
    rd', rs1' indicate compressed registers (x8-x15)
    """
    return (
        (funct3 << 13)
        | (imm_hi << 10)
        | (rs1_p << 7)
        | (imm_lo << 5)
        | (rd_p << 2)
        | op
    )


def encode_cs_type(funct3, imm_hi, rs1_p, imm_lo, rs2_p, op):
    """
    Encode CS-Type (Compressed Store):
    funct3[15:13] | imm[12:10] | rs1'[9:7] | imm[6:5] | rs2'[4:2] | op[1:0]
    rs1', rs2' indicate compressed registers (x8-x15)
    """
    return (
        (funct3 << 13)
        | (imm_hi << 10)
        | (rs1_p << 7)
        | (imm_lo << 5)
        | (rs2_p << 2)
        | op
    )


def encode_ca_type(funct6, rd_rs1_p, funct2, rs2_p, op):
    """
    Encode CA-Type (Compressed Arithmetic):
    funct6[15:10] | rd'/rs1'[9:7] | funct2[6:5] | rs2'[4:2] | op[1:0]
    rd'/rs1', rs2' indicate compressed registers (x8-x15)
    """
    return (funct6 << 10) | (rd_rs1_p << 7) | (funct2 << 5) | (rs2_p << 2) | op


def encode_cb_type(funct3, offset_hi, rs1_p, offset_lo, op):
    """
    Encode CB-Type (Compressed Conditional Branch):
    funct3[15:13] | offset[12:10] | rs1'[9:7] | offset[6:2] | op[1:0]
    rs1' indicates compressed register (x8-x15)
    """
    return (funct3 << 13) | (offset_hi << 10) | (rs1_p << 7) | (offset_lo << 2) | op


def encode_cj_type(funct3, jump_target, op):
    """
    Encode CJ-Type (Compressed Unconditional Jump):
    funct3[15:13] | jump_target[12:2] | op[1:0]
    """
    return (funct3 << 13) | (jump_target << 2) | op


# ============================================================================
# RV32C Compressed Instructions (16-bit)
# Organized by Quadrant (bits [1:0])
# ============================================================================

# ----------------------------------------------------------------------------
# Quadrant 00 (bits [1:0] = 00)
# ----------------------------------------------------------------------------


def encode_c_addi4spn(rd, imm):
    """
    Compressed Add Immediate to Stack Pointer scaled by 4 (CIW-Type)
    C.ADDI4SPN rd', imm
    Decoder: c_addi4sp_imm = {22'b0, instr[10:7], instr[12:11], instr[5], instr[6], 2'b0}
    So imm[9:6]→bits[10:7], imm[5:4]→bits[12:11], imm[3]→bit[5], imm[2]→bit[6]
    CIW format places scrambled at bits[12:5], so:
    scrambled[7:6]=imm[5:4], scrambled[5:2]=imm[9:6], scrambled[1]=imm[2], scrambled[0]=imm[3]
    """
    scrambled = (
        ((imm & 0x030) << 2)  # imm[5:4] -> scrambled[7:6]
        | ((imm & 0x3C0) >> 4)  # imm[9:6] -> scrambled[5:2]
        | ((imm & 0x004) >> 1)  # imm[2] -> scrambled[1]
        | ((imm & 0x008) >> 3)  # imm[3] -> scrambled[0]
    )
    return encode_ciw_type(0b000, scrambled, rd & 0x7, 0b00)


def encode_c_lw(rd, rs1, imm):
    """
    Compressed Load Word (CL-Type)
    C.LW rd', imm(rs1')
    """
    # imm[5:3] to [12:10], imm[2|6] to [6:5]
    imm_hi = (imm >> 3) & 0x7
    imm_lo = ((imm >> 6) & 0x1) | ((imm >> 1) & 0x2)
    return encode_cl_type(0b010, imm_hi, rs1 & 0x7, imm_lo, rd & 0x7, 0b00)


def encode_c_sw(rs1, rs2, imm):
    """
    Compressed Store Word (CS-Type)
    C.SW rs2', imm(rs1')
    """
    # imm[5:3] to [12:10], imm[2|6] to [6:5]
    imm_hi = (imm >> 3) & 0x7
    imm_lo = ((imm >> 6) & 0x1) | ((imm >> 1) & 0x2)
    return encode_cs_type(0b110, imm_hi, rs1 & 0x7, imm_lo, rs2 & 0x7, 0b00)


def encode_c_lbu(rd, rs1, imm):
    """
    Compressed Load Byte Unsigned (CL-Type variant)
    C.LBU rd', imm(rs1')
    bits[12:10]=000 (load byte), imm[1:0] → bits[6:5]
    Decoder: c_lsb_imm = {30'b0, instr[5], instr[6]} = {30'b0, imm[1], imm[0]}
    So imm[1]→bit5, imm[0]→bit6, requiring bit swap
    """
    imm_lo = ((imm >> 1) & 0x1) | ((imm & 0x1) << 1)
    return encode_cl_type(0b100, 0b000, rs1 & 0x7, imm_lo, rd & 0x7, 0b00)


def encode_c_lhu(rd, rs1, imm):
    """
    Compressed Load Halfword Unsigned (CL-Type variant)
    C.LHU rd', imm(rs1')
    bits[12:10]: bit[11]=0 (load), bit[10]=1 (halfword) → imm_hi=0b001
    """
    imm_lo = (imm >> 1) & 0x1
    return encode_cl_type(0b100, 0b001, rs1 & 0x7, imm_lo, rd & 0x7, 0b00)


def encode_c_lh(rd, rs1, imm):
    """
    Compressed Load Halfword Signed (CL-Type variant)
    C.LH rd', imm(rs1')
    bits[12:10]: bit[11]=0 (load), bit[10]=1 (halfword) → imm_hi=0b001
    bit[6]=1 (signed) via imm_lo bit 1
    """
    imm_lo = ((imm >> 1) & 0x1) | 0x2
    return encode_cl_type(0b100, 0b001, rs1 & 0x7, imm_lo, rd & 0x7, 0b00)


def encode_c_sb(rs1, rs2, imm):
    """
    Compressed Store Byte (CS-Type variant)
    C.SB rs2', imm(rs1')
    bits[12:10]: bit[11]=1 (store), bit[10]=0 (byte) → imm_hi=0b010
    Decoder: c_lsb_imm = {30'b0, instr[5], instr[6]} = {30'b0, imm[1], imm[0]}
    So imm[1]→bit5, imm[0]→bit6, requiring bit swap
    """
    imm_lo = ((imm >> 1) & 0x1) | ((imm & 0x1) << 1)
    return encode_cs_type(0b100, 0b010, rs1 & 0x7, imm_lo, rs2 & 0x7, 0b00)


def encode_c_sh(rs1, rs2, imm):
    """
    Compressed Store Halfword (CS-Type variant)
    C.SH rs2', imm(rs1')
    bits[12:10]: bit[11]=1 (store), bit[10]=1 (halfword) → imm_hi=0b011
    """
    imm_lo = (imm >> 1) & 0x1
    return encode_cs_type(0b100, 0b011, rs1 & 0x7, imm_lo, rs2 & 0x7, 0b00)


# ----------------------------------------------------------------------------
# Quadrant 01 (bits [1:0] = 01)
# ----------------------------------------------------------------------------


def encode_c_nop():
    """
    Compressed No Operation (CI-Type)
    C.NOP
    """
    return encode_ci_type(0b000, 0, 0, 0, 0b01)  # 0x0001


def encode_c_addi(rd, imm):
    """
    Compressed Add Immediate (CI-Type)
    C.ADDI rd, imm
    """
    imm_hi = (imm >> 5) & 0x1
    imm_lo = imm & 0x1F
    return encode_ci_type(0b000, imm_hi, rd, imm_lo, 0b01)


def encode_c_jal(imm):
    """
    Compressed Jump and Link (CJ-Type, RV32 only)
    C.JAL offset
    """
    # offset[11|4|9:8|10|6|7|3:1|5] to [12:2]
    scrambled = (
        ((imm & 0x800) << 1)
        | ((imm & 0x010) << 7)
        | ((imm & 0x300) << 1)
        | ((imm & 0x400) >> 2)
        | ((imm & 0x040) << 1)
        | ((imm & 0x080) >> 1)
        | ((imm & 0x00E) << 2)
        | ((imm & 0x020) >> 3)
    )
    return encode_cj_type(0b001, scrambled, 0b01)


def encode_c_li(rd, imm):
    """
    Compressed Load Immediate (CI-Type)
    C.LI rd, imm
    """
    imm_hi = (imm >> 5) & 0x1
    imm_lo = imm & 0x1F
    return encode_ci_type(0b010, imm_hi, rd, imm_lo, 0b01)


def encode_c_addi16sp(imm):
    """
    Compressed Add Immediate to Stack Pointer scaled by 16 (CI-Type)
    C.ADDI16SP imm
    """
    # imm[9] to [12], imm[4|6|8:7|5] to [6:2]
    imm_hi = (imm >> 9) & 0x1
    imm_lo = (
        ((imm >> 2) & 0x10)
        | ((imm >> 1) & 0x8)
        | ((imm >> 1) & 0x6)
        | ((imm >> 3) & 0x1)
    )
    return encode_ci_type(0b011, imm_hi, 2, imm_lo, 0b01)  # rd=2 is sp


def encode_c_lui(rd, imm):
    """
    Compressed Load Upper Immediate (CI-Type)
    C.LUI rd, imm
    """
    # imm[17] to [12], imm[16:12] to [6:2]
    imm_hi = (imm >> 17) & 0x1
    imm_lo = (imm >> 12) & 0x1F
    return encode_ci_type(0b011, imm_hi, rd, imm_lo, 0b01)


def encode_c_srli(rd, shamt):
    """
    Compressed Shift Right Logical Immediate (CB-Type)
    C.SRLI rd', shamt
    """
    offset_hi = (shamt >> 5) & 0x1
    offset_lo = shamt & 0x1F
    return encode_cb_type(0b100, offset_hi, rd & 0x7, offset_lo, 0b01)


def encode_c_srai(rd, shamt):
    """
    Compressed Shift Right Arithmetic Immediate (CB-Type)
    C.SRAI rd', shamt
    """
    offset_hi = (shamt >> 5) & 0x1
    offset_lo = shamt & 0x1F
    # Needs funct2=01 in offset_lo[4:3]
    offset_lo_with_funct = offset_lo | 0x10
    return encode_cb_type(0b100, offset_hi, rd & 0x7, offset_lo_with_funct, 0b01)


def encode_c_andi(rd, imm):
    """
    Compressed AND Immediate (CB-Type)
    C.ANDI rd', imm
    """
    offset_hi = (imm >> 5) & 0x1
    offset_lo = imm & 0x1F
    # Needs funct2=10 in offset_lo[4:3]
    offset_lo_with_funct = offset_lo | 0x10
    return encode_cb_type(0b100, offset_hi, rd & 0x7, offset_lo_with_funct, 0b01)


def encode_c_sub(rd, rs2):
    """
    Compressed Subtract (CA-Type)
    C.SUB rd', rs2'
    """
    return encode_ca_type(0b100011, rd & 0x7, 0b00, rs2 & 0x7, 0b01)


def encode_c_xor(rd, rs2):
    """
    Compressed XOR (CA-Type)
    C.XOR rd', rs2'
    """
    return encode_ca_type(0b100011, rd & 0x7, 0b01, rs2 & 0x7, 0b01)


def encode_c_or(rd, rs2):
    """
    Compressed OR (CA-Type)
    C.OR rd', rs2'
    """
    return encode_ca_type(0b100011, rd & 0x7, 0b10, rs2 & 0x7, 0b01)


def encode_c_and(rd, rs2):
    """
    Compressed AND (CA-Type)
    C.AND rd', rs2'
    """
    return encode_ca_type(0b100011, rd & 0x7, 0b11, rs2 & 0x7, 0b01)


def encode_c_j(imm):
    """
    Compressed Jump (CJ-Type)
    C.J offset
    """

    # Impressive but absurd.
    # offset[11|4|9:8|10|6|7|3:1|5] to [12:2]
    scrambled = (
        ((imm & 0x800) << 1)
        | ((imm & 0x010) << 7)
        | ((imm & 0x300) << 1)
        | ((imm & 0x400) >> 2)
        | ((imm & 0x040) << 1)
        | ((imm & 0x080) >> 1)
        | ((imm & 0x00E) << 2)
        | ((imm & 0x020) >> 3)
    )
    return encode_cj_type(0b101, scrambled, 0b01)


def encode_c_beqz(rs1, imm):
    """
    Compressed Branch if Equal to Zero (CB-Type)
    C.BEQZ rs1', offset
    """
    # offset[8|4:3] to [12:10], offset[7:6|2:1|5] to [6:2]
    offset_hi = ((imm >> 6) & 0x4) | ((imm >> 3) & 0x3)
    offset_lo = ((imm >> 1) & 0x18) | ((imm << 2) & 0x6) | ((imm >> 3) & 0x1)
    return encode_cb_type(0b110, offset_hi, rs1 & 0x7, offset_lo, 0b01)


def encode_c_bnez(rs1, imm):
    """
    Compressed Branch if Not Equal to Zero (CB-Type)
    C.BNEZ rs1', offset
    """
    # offset[8|4:3] to [12:10], offset[7:6|2:1|5] to [6:2]
    offset_hi = ((imm >> 6) & 0x4) | ((imm >> 3) & 0x3)
    offset_lo = ((imm >> 1) & 0x18) | ((imm << 2) & 0x6) | ((imm >> 3) & 0x1)
    return encode_cb_type(0b111, offset_hi, rs1 & 0x7, offset_lo, 0b01)


# ----------------------------------------------------------------------------
# Quadrant 10 (bits [1:0] = 10)
# ----------------------------------------------------------------------------


def encode_c_slli(rd, shamt):
    """
    Compressed Shift Left Logical Immediate (CI-Type)
    C.SLLI rd, shamt
    """
    imm_hi = (shamt >> 5) & 0x1
    imm_lo = shamt & 0x1F
    return encode_ci_type(0b000, imm_hi, rd, imm_lo, 0b10)


def encode_c_lwsp(rd, imm):
    """
    Compressed Load Word from Stack Pointer (CI-Type)
    C.LWSP rd, imm(sp)
    Decoder: c_lwsp_imm = {24'b0, instr[3:2], instr[12], instr[6:4], 2'b00}
    So imm[7:6]→bits[3:2], imm[5]→bit[12], imm[4:2]→bits[6:4]
    CI format: bit[12]=imm_hi, bits[6:2]=(imm_lo<<2)[6:2]=imm_lo[4:0]
    Need: imm_lo[4:2]=imm[4:2], imm_lo[1:0]=imm[7:6]
    """
    imm_hi = (imm >> 5) & 0x1
    imm_lo = (imm & 0x1C) | ((imm >> 6) & 0x3)
    return encode_ci_type(0b010, imm_hi, rd, imm_lo, 0b10)


def encode_c_swsp(rs2, imm):
    """
    Compressed Store Word to Stack Pointer (CSS-Type)
    C.SWSP rs2, imm(sp)
    Decoder: c_swsp_imm = {24'b0, instr[8:7], instr[12:9], 2'b00}
    So imm[7:6]→bits[8:7], imm[5:2]→bits[12:9]
    CSS format: bits[12:7]=scrambled[5:0]
    Need: bits[12:9]=imm[5:2], bits[8:7]=imm[7:6]
    """
    scrambled = (imm & 0x3C) | ((imm >> 6) & 0x3)
    return encode_css_type(0b110, scrambled, rs2, 0b10)


def encode_c_jr(rs1):
    """
    Compressed Jump Register (CR-Type)
    C.JR rs1
    """
    return encode_cr_type(0b1000, rs1, 0, 0b10)


def encode_c_mv(rd, rs2):
    """
    Compressed Move (CR-Type)
    C.MV rd, rs2
    """
    return encode_cr_type(0b1000, rd, rs2, 0b10)


def encode_c_ebreak():
    """
    Compressed Environment Break (CR-Type)
    C.EBREAK
    """
    return encode_cr_type(0b1001, 0, 0, 0b10)


def encode_c_jalr(rs1):
    """
    Compressed Jump and Link Register (CR-Type)
    C.JALR rs1
    """
    return encode_cr_type(0b1001, rs1, 0, 0b10)


def encode_c_add(rd, rs2):
    """
    Compressed Add (CR-Type)
    C.ADD rd, rs2
    """
    return encode_cr_type(0b1001, rd, rs2, 0b10)
