
// Nibble-series counter register used as the Program Counter (PC)
// Counts the 32b register 4b at a time over 8 cycles.
// 
// Based on: https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/counter.v
module tinymoa_counter #(parameter DATA_WIDTH = 4) (
    input clk,
    input nrst,

    input increment,
    input [2:0] nibble_counter,

    output [DATA_WIDTH-1:0] data,
    output carry_out
);
    reg [31:0] register;
    reg carry_bit;

    wire [4:0] increment_result = {1'b0, register[7:4]} + {4'b0, (nibble_counter == 0) ? increment : carry_bit};
    
    always @(posedge clk) begin
        if (!nrst) begin
            register[3:0] <= 4'h0;
            carry_bit <= 0;
        end else begin
            {carry_bit, register[3:0]} <= increment_result;
        end
    end

    wire [31:4] reg_buf;

    // On SG13G2 and generic FPGA, no buffer required
    // On Sky130A, need to use i_regbut using "sky130_fd_sc_hd__dlygate4sd3_1"
    assign reg_buf = {register[3:0], register[31:8]};

    always @(posedge clk) register[31:4] <= reg_buf;

    assign data = register[3 + DATA_WIDTH:4];
    assign carry_out = increment_result[4];
endmodule
