/*  TinyMOA ALU multiplier based on:
    https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/alu.v

    Multiply:
        1010 MUL: Data = B[15:0] * A
*/

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
