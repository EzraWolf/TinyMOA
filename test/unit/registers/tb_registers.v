`default_nettype none
`timescale 1ns / 1ps

module tb_registers (
    input clk,
    input nrst,

    input write_en,
    input [3:0] write_dest,
    input [31:0] data_in,

    input [3:0] read_addr_a,
    input [3:0] read_addr_b,
    output reg [31:0] data_port_a,
    output reg [31:0] data_port_b
);
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_registers.fst");
        $dumpvars(0, tb_registers);
        #1;
    end
    `endif

    // Cycles through nibbles: 0, 4, 8, 12, 16, 20, 24, 28, 0, ...
    reg [4:0] nibble_counter;
    
    // Connect to register file
    wire [3:0] data_port_a_nibble;
    wire [3:0] data_port_b_nibble;
    wire [23:1] return_addr;
    
    always @(posedge clk) begin
        if (!nrst) begin
            nibble_counter <= 0;
            data_port_a <= 0;
            data_port_b <= 0;
        end else begin
            nibble_counter <= nibble_counter + 4;
            data_port_a[nibble_counter +: 4] <= data_port_a_nibble;
            data_port_b[nibble_counter +: 4] <= data_port_b_nibble;
        end
    end

    tinymoa_register_file #(
        .REG_COUNT(16)
    ) dut_regfile (
        .clk(clk),

        .nibble_counter(nibble_counter[4:2]),

        .write_en(write_en),
        .write_dest(write_dest),
        .data_in(data_in[nibble_counter +: 4]),

        .read_addr_a(read_addr_a),
        .read_addr_b(read_addr_b),
        .data_port_a(data_port_a_nibble),
        .data_port_b(data_port_b_nibble),
        
        .return_addr(return_addr)
    );
endmodule
