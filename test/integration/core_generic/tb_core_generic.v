`default_nettype none
`timescale 1ns / 1ps

module tb_core_generic (
    input clk,
    input nrst,

    output [2:0]  dbg_state,
    output [31:0] dbg_pc,

    // Register probe: set reg_probe_sel, read reg_probe_val after 8 clocks
    input  [3:0]  reg_probe_sel,
    output [31:0] reg_probe_val
);
    `ifdef COCOTB_SIM
    initial begin
        $dumpfile("tb_core_generic.fst");
        $dumpvars(0, tb_core_generic);
        #1;
    end
    `endif

    reg [31:0] mem [0:255]; // 1KB word addressable
    initial $readmemh("program.hex", mem);

    wire [31:0] mem_addr;
    wire        mem_read, mem_write;
    wire [31:0] mem_wdata;
    wire [1:0]  mem_size;

    reg [31:0] mem_rdata;
    reg        mem_ready;

    // Single cycle memory, always ready
    always @(posedge clk) begin
        if (!nrst) begin
            mem_rdata <= 32'd0;
            mem_ready <= 1'b0;
        end else begin
            mem_ready <= mem_read || mem_write;
            if (mem_read)
                mem_rdata <= mem[mem_addr[9:2]]; // word-aligned
            if (mem_write)
                mem[mem_addr[9:2]] <= mem_wdata;
        end
    end

    tinymoa_core_generic core (
        .clk(clk),
        .nrst(nrst),
        .mem_addr(mem_addr),
        .mem_read(mem_read),
        .mem_write(mem_write),
        .mem_wdata(mem_wdata),
        .mem_size(mem_size),
        .mem_rdata(mem_rdata),
        .mem_ready(mem_ready),
        .dbg_state(dbg_state),
        .dbg_pc(dbg_pc)
    );

    // Register probe: use the regfile's read port A during FETCH to sample a register
    // The nibble_counter in the core rotates 0-7, and the regfile outputs one nibble
    // per clock. We accumulate 8 nibbles to reconstruct the full 32-bit value.
    wire [3:0] probe_nibble = core.regfile.register_access[reg_probe_sel];
    wire [2:0] probe_nc = core.nibble_counter;
    reg [31:0] probe_accum;

    always @(posedge clk) begin
        if (!nrst)
            probe_accum <= 32'd0;
        else
            probe_accum[{probe_nc, 2'b00} +: 4] <= probe_nibble;
    end

    assign reg_probe_val = probe_accum;
endmodule
