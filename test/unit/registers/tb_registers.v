`default_nettype none
`timescale 1ns / 1ps

module tb_registers (
    input clk,
    input rstn,

    input wr_en,
    input [3:0] rd,
    input [31:0] rd_in,

    input [3:0] rs1,
    input [3:0] rs2,
    output reg [31:0] rs1_out,
    output reg [31:0] rs2_out
);

    // Dump signals for waveform viewing
    initial begin
        $dumpfile("tb_registers.fst");
        $dumpvars(0, tb_registers);
        #1;
    end

    // Cycles through nibbles: 0, 4, 8, 12, 16, 20, 24, 28, 0, ...
    reg [4:0] nibble_counter; 
    
    always @(posedge clk) begin
        if (!rstn) begin
            nibble_counter <= 0;
            rs1_out <= 0;
            rs2_out <= 0;
        end else begin
            nibble_counter <= nibble_counter + 4;
        end
    end
    
    // Connect to register file
    wire [3:0] data_rs1;
    wire [3:0] data_rs2;
    wire [23:1] return_addr;

    tinymoa_register_file #(
        .REG_COUNT(16)
    ) regfile (
        .clk(clk),

        .nibble_counter(nibble_counter[4:2]),

        .write_en(wr_en),
        .write_dest({1'b0, rd}),
        .data_in(rd_in[nibble_counter +: 4]),

        .read_addr_a({1'b0, rs1}),
        .read_addr_b({1'b0, rs2}),
        .data_port_a(data_rs1),
        .data_port_b(data_rs2),
        
        .return_addr(return_addr)
    );
    
    // Accumulate 4b outputs into 32b values
    always @(posedge clk) begin
        if (!rstn) begin
            rs1_out <= 0;
            rs2_out <= 0;
        end else begin
            rs1_out[nibble_counter +: 4] <= data_rs1;
            rs2_out[nibble_counter +: 4] <= data_rs2;
        end
    end

endmodule
