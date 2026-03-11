`default_nettype none
`timescale 1ns / 1ps

module tb_csr (
    input clk,
    input nrst,

    input [11:0]      csr_addr,
    input             csr_read,
    output reg [31:0] csr_rdata,
    output [2:0]      nibble_counter_out
);
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_csr.fst");
        $dumpvars(0, tb_csr);
        #1;
    end
    `endif

    reg [2:0] nibble_counter;
    wire [3:0] csr_rdata_nibble;
    wire [4:0] nibble_bit = {nibble_counter, 2'b00};

    assign nibble_counter_out = nibble_counter;

    always @(posedge clk) begin
        if (!nrst) begin
            nibble_counter <= 3'd0;
            csr_rdata      <= 32'd0;
        end else begin
            nibble_counter <= nibble_counter + 3'd1;
            if (csr_read)
                csr_rdata[nibble_bit +: 4] <= csr_rdata_nibble;
        end
    end

    tinymoa_csr dut (
        .clk(clk),
        .nrst(nrst),
        .nibble_counter(nibble_counter),
        .csr_addr(csr_addr),
        .csr_read(csr_read),
        .csr_rdata_nibble(csr_rdata_nibble)
    );
endmodule
