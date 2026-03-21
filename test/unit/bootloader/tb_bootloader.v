// Physical bootloader FSM test bench

`default_nettype none
`timescale 1ns / 1ps

module tb_bootloader (
    input clk,
    input nrst,

    output boot_done,

    input             rom_ready,
    output reg        rom_read,
    input      [31:0] rom_dout,
    output reg [23:0] rom_addr,

    output reg        tcm_wen,
    output reg [31:0] tcm_wdata,
    output reg [9:0]  tcm_addr
);
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_bootloader.fst");
        $dumpvars(0, tb_bootloader);
        #1;
    end
    `endif

    tinymoa_bootloader dut_boot (
        .clk       (clk),
        .nrst      (nrst),
        .boot_done (boot_done),
        .rom_addr  (rom_addr),
        .rom_read  (rom_read),
        .rom_dout  (rom_dout),
        .rom_ready (rom_ready),
        .tcm_addr  (tcm_addr),
        .tcm_wdata (tcm_wdata),
        .tcm_wen   (tcm_wen)
    );

    always @(posedge clk) begin
        // Stimulus (rom_dout, rom_ready) driven via cocotb
    end
endmodule
