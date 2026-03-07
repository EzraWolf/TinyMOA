`default_nettype none
`timescale 1ns / 1ps

module tb_counter (
    input  wire        clk,
    input  wire        tb_nrst,
    input  wire        load_en,
    input  wire        increment,
    input  wire        decrement,
    input  wire [31:0] load_data,
    output wire [31:0] result
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_counter.fst");
        $dumpvars(0, tb_counter);
        #1;
    end
    `endif

    reg [2:0] nibble_counter;
    wire active = load_en | increment | decrement;

    always @(posedge clk or negedge tb_nrst) begin
        if (!tb_nrst)
            nibble_counter <= 3'd0;
        else if (active)
            nibble_counter <= nibble_counter + 3'd1;
        else
            nibble_counter <= 3'd0;
    end

    wire       start  = (nibble_counter == 3'd0);
    wire [3:0] bus_in = load_data[nibble_counter * 4 +: 4];
    wire [3:0] data_out;

    tinymoa_counter dut (
        .clk(clk),
        .load_en(load_en),
        .increment(increment),
        .decrement(decrement),
        .start(start),
        .bus_in(bus_in),
        .data_out(data_out)
    );

    assign result = dut.pc_reg;
endmodule