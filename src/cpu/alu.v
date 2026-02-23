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

    Shift instructions (handled by the shifter below):
        0001 SLL: Data = A << B
        0101 SRL: Data = A >> B
        1101 SRA: Data = A >> B (signed)

    Multiply:
        1010 MUL: Data = B[15:0] * A

    Conditional zero (not implemented here)
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


module tinymoa_multiplier #(parameter B_IN_WIDTH = 16) (
    input clk,
    input nrst,

    input [3:0] a_in,
    input [B_IN_WIDTH-1:0] b_in,

    output [3:0] product
);
    reg [B_IN_WIDTH-1:0] accumulator;

    // https://xkcd.com/759/
    wire [B_IN_WIDTH+3:0] partial_product = {4'b0, accumulator} + {{B_IN_WIDTH{1'b0}}, a_in} * {4'd0, b_in};

    always @(posedge clk) begin
        if (!nrst)
            accumulator <= {B_IN_WIDTH{1'b0}};
        else
            accumulator <= (a_in != 4'b0000) ? partial_product[B_IN_WIDTH+3:4] : {4'b0000, accumulator[B_IN_WIDTH-1:4]};
    end

    assign product = partial_product[3:0];
endmodule


module tinymoa_shifter (
    input [3:2]  opcode, // [3]=arithmetic, [2]=shift_right
    input [2:0]  nibble_counter,
    input [31:0] data_in,
    input [4:0]  shift_amnt,
    
    output [3:0] result
);

    // Determine if to fill bit for arithmetic shifts
    wire fill_bit = opcode[3] ? data_in[31] : 1'b0;
    wire is_shift_right = opcode[2];

    // For left shift: bit-reverse the input, shift right, then bit-reverse output
    // This reuses right-shift logic for both directions
    wire [31:0] data_for_right_shift = is_shift_right ? data_in : {
        data_in[ 0], data_in[ 1], data_in[ 2], data_in[ 3], 
        data_in[ 4], data_in[ 5], data_in[ 6], data_in[ 7],
        data_in[ 8], data_in[ 9], data_in[10], data_in[11], 
        data_in[12], data_in[13], data_in[14], data_in[15],
        data_in[16], data_in[17], data_in[18], data_in[19], 
        data_in[20], data_in[21], data_in[22], data_in[23],
        data_in[24], data_in[25], data_in[26], data_in[27], 
        data_in[28], data_in[29], data_in[30], data_in[31]
    };

    // Set the counter direction (forward for right shift, backward for left)
    // Then return the total shift = base shift amount + (counter * 4)
    wire [2:0]  adjusted_counter = is_shift_right ? nibble_counter : ~nibble_counter;
    wire [5:0]  total_shift = {1'b0, shift_amnt} + {1'b0, adjusted_counter, 2'b00};
    wire [5:0]  shift_index = {1'b0, total_shift[4:0]};
    wire [34:0] padded_data = {{3{fill_bit}}, data_for_right_shift};

    // Extract 4b nibble at shift position
    reg [3:0] shifted_nibble;
    always @(*) begin
        if (total_shift[5])  // Shift amount >= 32, all fill bits
            shifted_nibble = {4{fill_bit}};
        else
            shifted_nibble = padded_data[shift_index +: 4];
    end

    // For left shift, we bit-reverse the output nibble
    assign result = is_shift_right ? shifted_nibble : {
        shifted_nibble[0], shifted_nibble[1], shifted_nibble[2], shifted_nibble[3]
    };
endmodule
