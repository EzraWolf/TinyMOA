`default_nettype none
`timescale 1ns / 1ps

module tb_counter (
    input clk,
    input nrst,
    input increment,
    output reg [31:0] result,
    output reg carry_out
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_counter.fst");
        $dumpvars(0, tb_counter);
        #1;
    end
    `endif

    reg [4:0] counter;
    always @(posedge clk) begin
        if (!nrst)
            counter <= 0;
        else
            counter <= counter + 4;
    end

    wire [2:0] nibble_counter = counter[4:2];
    wire [3:0] data;
    wire carry_bit;

    tinymoa_counter dut_counter (
        .clk(clk),
        .nrst(nrst),
        .nibble_counter(nibble_counter),
        .increment(increment),
        .data(data),
        .carry_out(carry_bit)
    );

    always @(posedge clk) begin
        result[counter+:4] <= data;
        if (nibble_counter == 3'b111)
            carry_out <= carry_bit;
    end

endmodule
