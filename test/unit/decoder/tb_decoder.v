`default_nettype none
`timescale 1ns / 1ps

module tb_decoder (
    input clk,
    input nrst,

    input [31:0] instr,

    output [31:0] imm,

    output is_load,
    output is_alu_imm,
    output is_auipc,
    output is_store,
    output is_alu_reg,
    output is_lui,
    output is_branch,
    output is_jalr,
    output is_jal,
    output is_ret,
    output is_system,

    output [2:0] instr_len,

    output [3:0] alu_opcode,
    output [2:0] mem_opcode,

    output [3:0] rs1,
    output [3:0] rs2,
    output [3:0] rd,

    output [2:0] additional_mem_ops,
    output       mem_op_increment_reg
);

    `ifdef COCOTB_SIM
    initial begin
        $dumpfile ("tb_decoder.fst");
        $dumpvars (0, tb_decoder);
        #1;
    end
    `endif

    tinymoa_decoder decoder(
        .instr(instr), 
        .imm(imm),

        .is_load(is_load),
        .is_alu_imm(is_alu_imm),
        .is_auipc(is_auipc),
        .is_store(is_store),
        .is_alu_reg(is_alu_reg),
        .is_lui(is_lui),
        .is_branch(is_branch),
        .is_jalr(is_jalr),
        .is_jal(is_jal),
        .is_ret(is_ret),
        .is_system(is_system),

        .instr_len(instr_len[2:1]),

        .alu_opcode(alu_opcode),
        .mem_opcode(mem_opcode),

        .read_addr_a(rs1),
        .read_addr_b(rs2),
        .write_dest(rd),

        .additional_mem_opcode(additional_mem_ops),
        .mem_op_increment_reg(mem_op_increment_reg)
    );

    assign instr_len[0] = 1'b0;
endmodule
