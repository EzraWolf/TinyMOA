// DCIM 32x32 unit test bench

`default_nettype none
`timescale 1ns / 1ps

module tb_dcim (
    input clk,
    input nrst,

    // TODO
);
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_dcim.fst");
        $dumpvars(0, tb_dcim);
        #1;
    end
    `endif

    tinymoa_dcim dut_dcim (
        // TODO
    );
endmodule
