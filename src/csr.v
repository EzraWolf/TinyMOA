`default_nettype none
`timescale 1ns / 1ps

// Minimal CSR module for RV32EC
// Currently implements:
// 0xC00 - cycle (read-only): clock cycle counter
module tinymoa_csr (
    input wire        clk,
    input wire        nrst,

    input wire [2:0]  nibble_counter,

    input wire [11:0] csr_addr,
    input wire        csr_read,
    output wire [3:0] csr_rdata_nibble
);

    reg [31:0] cycle_counter;

    always @(posedge clk) begin
        if (!nrst)
            cycle_counter <= 32'd0;
        else
            cycle_counter <= cycle_counter + 32'd1;
    end

    // Nibble-serial read mux
    wire [4:0] nibble_offset = {nibble_counter, 2'b00};
    wire [3:0] cycle_nibble  = cycle_counter[nibble_offset +: 4];

    // Address decode
    assign csr_rdata_nibble = (csr_read && csr_addr == 12'hC00) ? cycle_nibble : 4'h0;
endmodule
