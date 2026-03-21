// TinyMOA ALU — 4-bit nibble-serial with shifter and multiplier
//
// Three datapaths, selected by core FSM based on decoded opcode:
//   1. Nibble-serial ALU — carry-chained ADD/SUB/AND/OR/XOR/SLT/SLTU/CZERO
//   2. Shifter           — SLL/SRL/SRA (needs full operand + shift amount)
//   3. Multiplier        — C.MUL: 16x16 signed → 32-bit (combinational)
//
// C.MUL uses non-standard Zcb encoding (Q2 funct3=101, ALU opcode 4'b1010).
// This is NOT the standard Zcb c.mul (CA-type, Q1, funct6=100111).
//
// ALU Opcode Table (from decoder):
//   0000  ADD             0100  XOR             1000  SUB
//   0001  SLL             0101  SRL             1010  MUL (C.MUL)
//   0010  SLT (signed)    0110  OR              1101  SRA
//   0011  SLTU (unsigned) 0111  AND             1110  CZERO.EQZ
//                                               1111  CZERO.NEZ
//
// Comparison outputs (cmp_out) used for branches:
//   opcode[0]=1: unsigned compare (SLTU/BGEU/BLTU)
//   opcode[1]=1: signed compare (SLT/BGE/BLT)
//   else:        equality (XOR == 0, for BEQ/BNE)

`default_nettype none
`timescale 1ns / 1ps

module tinymoa_alu (
    input [3:0] opcode,

    input [3:0] a_in,
    input [3:0] b_in,
    input       c_in,

    output reg [3:0] result,
    output     c_out,

    input      cmp_in,
    output reg cmp_out
);

    // Conditional invert for SUB (opcode[3]) and compares (opcode[1])
    wire [3:0] b_inv   = (opcode[1] || opcode[3]) ? ~b_in : b_in;
    wire [4:0] sum     = {1'b0, a_in} + {1'b0, b_inv} + {4'b0, c_in};
    wire [3:0] xor_out = a_in ^ b_in;

    assign c_out = sum[4];

    always @(*) begin
        result  = 4'd0;
        cmp_out = cmp_in;

        case (opcode)
            4'b0000: result = sum[3:0];    // ADD or SUB (b_inv handles inversion, same adder)
            4'b0100: result = xor_out;     // XOR
            4'b0110: result = a_in | b_in; // OR
            4'b0111: result = a_in & b_in; // AND
            4'b1110: result = a_in;        // CZERO.EQZ (zeroes rd if rs2==0)
            4'b1111: result = a_in;        // CZERO.NEZ (zeroes rd if rs2!=0)
            default: result = 4'd0;
        endcase

        // Comparison logic (valid for SLT/SLTU/BEQ/BNE/BLT/BGE etc.)
        // NOTE: While this "falsely" updates on unintended instructions like AND/OR, cmp_out is simply ignored.
        if      (opcode[0]) cmp_out = ~sum[4];                     // SLTU
        else if (opcode[1]) cmp_out = a_in[3] ^ b_inv[3] ^ sum[4]; // SLT
        else                cmp_out = cmp_in && (xor_out == 4'd0); // EQ
    end

endmodule


// Shifter -- barrel shift on full 32-bit value, output nibble-by-nibble.
// Core collects full rs1 then reads result_nibble for nibble_ct 0..7.
// opcode: 0001=SLL, 0101=SRL, 1101=SRA.
module tinymoa_shifter (
    input  [3:0]  opcode,

    input  [2:0]  nibble_ct,
    
    input  [31:0] data_in,
    input  [4:0]  shift_amnt,

    output [3:0]  result
);

    wire [31:0] sll = data_in << shift_amnt;
    wire [31:0] srl = data_in >> shift_amnt;
    wire signed [31:0] sra = $signed(data_in) >>> shift_amnt;

    wire [31:0] shifted = (!opcode[2]) ? sll :
                           opcode[3]   ? sra : srl;

    assign result = shifted[{nibble_ct, 2'b00} +: 4];

endmodule


// Multiplier -- 16x16 signed -> 32-bit result
// Core feeds rs1[15:0] and rs2[15:0], then reads product nibble-by-nibble via nibble_ct.
module tinymoa_multiplier (
    input  signed [15:0] a_in,
    input  signed [15:0] b_in,

    output signed [31:0] product
);

    assign product = a_in * b_in;

endmodule
