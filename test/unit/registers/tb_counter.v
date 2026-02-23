`default_nettype none
`timescale 1ns / 1ps

module tb_counter (
    input clk,
    input rstn,
    input increment,
    output reg [31:0] val,
    output reg cy
);

`ifdef COCOTB_SIM
initial begin
    $dumpfile("tb_counter.fst");
    $dumpvars(0, tb_counter);
end
`endif

    reg [4:0] counter;
    always @(posedge clk) begin
        if (!rstn)
            counter <= 0;
        else
            counter <= counter + 4;
    end

    wire [2:0] nibble_counter = counter[4:2];
    wire [3:0] data;
    wire carry_out;

    tinymoa_counter dut (
        .clk(clk),
        .nrst(rstn),
        .nibble_counter(nibble_counter),
        .increment(increment),
        .data(data),
        .carry_out(carry_out)
    );

    always @(posedge clk) begin
        val[counter+:4] <= data;
        if (nibble_counter == 3'b111)
            cy <= carry_out;
    end

endmodule
