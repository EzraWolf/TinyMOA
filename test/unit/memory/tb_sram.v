`default_nettype none
`timescale 1ns / 1ps

module tb_sram (
    input clk,
    input nrst,

    // Write port (Port B - boot loader)
    input [8:0] write_addr,
    input [31:0] write_data,
    input write_en,

    // Read port (Port A - CPU)
    input [8:0] read_addr,
    output [31:0] read_data,
    input read_en,
    output reg read_ready
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_sram.fst");
        $dumpvars(0, tb_sram);
        #1;
    end
    `endif

    // SRAM behavioral model
    reg [31:0] sram_mem [0:511];

    // Combinational read
    assign read_data = sram_mem[read_addr];

    // Synchronous write
    always @(posedge clk) begin
        if (!nrst) begin
            read_ready <= 1'b0;
        end else begin
            if (write_en) begin
                sram_mem[write_addr] <= write_data;
            end
            read_ready <= read_en;
        end
    end

endmodule
