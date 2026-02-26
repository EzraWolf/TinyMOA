`default_nettype none
`timescale 1ns / 1ps

module tb_shifter (
    input clk,
    input nrst,

    input [3:2]  opcode, // [3]=arithmetic, [2]=shift_right
    input [31:0] data_in,
    input [4:0]  shift_amnt,
    
    output reg [31:0] result
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_shifter.fst");
        $dumpvars(0, tb_shifter);
        #1;
    end
    `endif

    // Cycles through nibbles: 0, 1, 2, 3, 4, 5, 6, 7, 0, ...
    reg [2:0] nibble_counter;
    
    wire [3:0] result_nibble;
    
    always @(posedge clk) begin
        if (!nrst) begin
            nibble_counter <= 0;
            result <= 0;
        end else begin
            nibble_counter <= nibble_counter + 1;
            result[{nibble_counter, 2'b00} +: 4] <= result_nibble;
        end
    end

    tinymoa_shifter dut_shifter (
        .opcode(opcode),
        .nibble_counter(nibble_counter),
        .data_in(data_in),
        .shift_amnt(shift_amnt),
        .result(result_nibble)
    );

endmodule