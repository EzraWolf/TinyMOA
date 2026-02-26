/*  TinyMOA ALU shifter based on:
    https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/alu.v

    Shift instructions (handled by the shifter below):
        0001 SLL: Data = A << B
        0101 SRL: Data = A >> B
        1101 SRA: Data = A >> B (signed)
*/

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
