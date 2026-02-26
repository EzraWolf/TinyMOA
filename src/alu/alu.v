/*  TinyMOA ALU based on:
    https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/alu.v

    RISC-V ALU instructions:
        0000 ADD:     Data =  A + B
        1000 SUB:     Data =  A - B
        0010 SLT:     Data = (A < B) ? 1 : 0 (signed)
        0011 SLTU:    Data = (A < B) ? 1 : 0 (unsigned)
        0111 AND:     Data =  A & B
        0110 OR:      Data =  A | B
        0100 XOR/EQ:  Data =  A ^ B

    === From shifter.v ===
    Shift instructions:
        0001 SLL: Data = A << B
        0101 SRL: Data = A >> B
        1101 SRA: Data = A >> B (signed)

    === From multiplier.v ===
    Multiply:
        1010 MUL: Data = B[15:0] * A

    === From ??? ===
    Conditional zero
        1110 CZERO.eqz
        1111 CZERO.nez
*/

module tinymoa_alu (
    input [3:0] opcode,
    
    input [3:0] a_in,
    input [3:0] b_in,
    input       cmp_in,
    input       carry_in,

    output reg [3:0] result,
    output reg       cmp_out,
    output           carry_out
);
    // Instead of duplicating add/sub logic, we conditionally invert b_in
    // for subtraction and comparison operations.
    wire [4:0] b_cond_invert = {1'b0, (opcode[1] || opcode[3]) ? ~b_in : b_in};
    wire [4:0] sum_result = {1'b0, a_in} + b_cond_invert + {4'b0, carry_in};
    wire [3:0] xor_result = a_in ^ b_in;

    always @(*) begin
        case (opcode[2:0])
            3'b000: result = sum_result[3:0];   // ADD or SUB based on opcode[3]
            3'b111: result = a_in & b_in;       // AND
            3'b110: result = a_in | b_in;       // OR
            3'b100: result = xor_result;        // XOR (used for SLT/SLTU as well)
            default: result = 4'b0;
        endcase

        // Note that we do trigger compares on unintended instructions like AND/OR but simply don't use it then
        if      (opcode[0]) cmp_out = ~sum_result[4]; // SLTU
        else if (opcode[1]) cmp_out = a_in[3] ^ b_cond_invert[3] ^ sum_result[4]; // SLT 
        else                cmp_out = cmp_in && xor_result == 0; // EQ
    end

    assign carry_out = sum_result[4];
endmodule
