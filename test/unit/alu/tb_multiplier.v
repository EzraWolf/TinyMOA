
`default_nettype none
`timescale 1ns / 1ps

module tb_multiplier (
    input clk,
    input nrst,

    input [31:0] a_in,
    input [15:0] b_in,
    output reg [31:0] result
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_multiplier.fst");
        $dumpvars(0, tb_multiplier);
        #1;
    end
    `endif

    // Cycles through nibbles: 0, 4, 8, 12, 16, 20, 24, 28, 0, ...
    reg [4:0] nibble_counter;
    
    wire [3:0] product_nibble;
    
    always @(posedge clk) begin
        if (!nrst) begin
            nibble_counter <= 0;
            result <= 0;
        end else begin
            nibble_counter <= nibble_counter + 4;
            result[nibble_counter +: 4] <= product_nibble;
        end
    end

    tinymoa_multiplier #(
        .B_IN_WIDTH(16)
    ) dut_multiplier (
        .clk(clk),
        .nrst(nrst),
        .a_in(a_in[nibble_counter +: 4]),
        .b_in(b_in),
        .product(product_nibble)
    );

endmodule
