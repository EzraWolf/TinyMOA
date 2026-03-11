// Generic RV32EC nibble-serial CPU core
// **NOT **instantiated by tinymoa.v
// this is the "ideal" 32b-addressed version
// used to verify correctness before creating the area-optimized core.v
`default_nettype none
`timescale 1ns / 1ps

module tinymoa_core_generic (
    input wire        clk,
    input wire        nrst,

    output reg [31:0] mem_addr,
    output reg        mem_read,
    output reg        mem_write,
    output reg [31:0] mem_wdata,
    output reg [1:0]  mem_size, // 00=byte, 01=half, 10=word
    input wire [31:0] mem_rdata,
    input wire        mem_ready,

    output wire [2:0] dbg_state,
    output wire [31:0] dbg_pc
);

    // State machine
    localparam S_FETCH    = 3'd0;
    localparam S_DECODE   = 3'd1;
    localparam S_EXECUTE  = 3'd2;
    localparam S_WRITEBACK = 3'd3;
    localparam S_MEM      = 3'd4;

    reg [2:0] state;
    reg [2:0] nibble_counter;

    assign dbg_state = state;

    // PC
    reg [31:0] pc;
    assign dbg_pc = pc;

    // IR
    reg [31:0] instr_reg;

    // Decoder
    wire [31:0] dec_imm;
    wire        dec_is_load, dec_is_store, dec_is_lui;
    wire        dec_is_alu_reg, dec_is_alu_imm;
    wire        dec_is_branch, dec_is_jal, dec_is_jalr, dec_is_ret;
    wire        dec_is_system, dec_is_auipc, dec_is_compressed;
    wire [2:1]  dec_instr_len;
    wire [3:0]  dec_alu_opcode;
    wire [2:0]  dec_mem_opcode;
    wire [3:0]  dec_rs1, dec_rs2, dec_rd;
    wire [2:0]  dec_additional_mem_opcode;
    wire        dec_mem_op_increment_reg;

    tinymoa_decoder decoder (
        .instr(instr_reg),
        .imm(dec_imm),
        .is_load(dec_is_load),
        .is_store(dec_is_store),
        .is_lui(dec_is_lui),
        .is_alu_reg(dec_is_alu_reg),
        .is_alu_imm(dec_is_alu_imm),
        .is_branch(dec_is_branch),
        .is_jal(dec_is_jal),
        .is_jalr(dec_is_jalr),
        .is_ret(dec_is_ret),
        .is_system(dec_is_system),
        .is_auipc(dec_is_auipc),
        .is_compressed(dec_is_compressed),
        .instr_len(dec_instr_len),
        .alu_opcode(dec_alu_opcode),
        .mem_opcode(dec_mem_opcode),
        .read_addr_a(dec_rs1),
        .read_addr_b(dec_rs2),
        .write_dest(dec_rd),
        .additional_mem_opcode(dec_additional_mem_opcode),
        .mem_op_increment_reg(dec_mem_op_increment_reg)
    );

    // Register file
    wire        reg_write_en;
    wire [3:0]  reg_wdata_nibble;
    wire [3:0]  reg_rs1_nibble, reg_rs2_nibble;
    wire [23:1] reg_return_addr;

    tinymoa_register_file #(.REG_COUNT(16)) regfile (
        .clk(clk),
        .nibble_counter(nibble_counter),
        .write_en(reg_write_en),
        .write_dest(dec_rd),
        .data_in(reg_wdata_nibble),
        .read_addr_a(dec_rs1),
        .read_addr_b(dec_rs2),
        .data_port_a(reg_rs1_nibble),
        .data_port_b(reg_rs2_nibble),
        .return_addr(reg_return_addr)
    );

    // ALU
    wire [3:0] alu_a_nibble = reg_rs1_nibble;
    wire [3:0] alu_b_nibble = (dec_is_alu_imm || dec_is_load || dec_is_store || dec_is_auipc)
                               ? dec_imm[{nibble_counter, 2'b00} +: 4]
                               : reg_rs2_nibble;
    wire [3:0] alu_result_nibble;
    wire       alu_cmp_out;
    wire       alu_carry_out;
    reg        alu_carry, alu_cmp;

    tinymoa_alu alu (
        .opcode(dec_alu_opcode),
        .a_in(dec_is_auipc ? pc[{nibble_counter, 2'b00} +: 4] : alu_a_nibble),
        .b_in(alu_b_nibble),
        .cmp_in(alu_cmp),
        .carry_in(alu_carry),
        .result(alu_result_nibble),
        .cmp_out(alu_cmp_out),
        .carry_out(alu_carry_out)
    );

    // Shifter needs full 32b input, accumulated during EXECUTE
    reg [31:0] rs1_full;
    reg [31:0] rs2_full;
    wire [3:0] shifter_result_nibble;

    tinymoa_shifter shifter (
        .opcode(dec_alu_opcode[3:2]),
        .nibble_counter(nibble_counter),
        .data_in(rs1_full),
        .shift_amnt(dec_imm[4:0]),
        .result(shifter_result_nibble)
    );

    // Multiplier
    wire [3:0] mul_result_nibble;
    tinymoa_multiplier #(.B_IN_WIDTH(16)) multiplier (
        .clk(clk),
        .nrst(nrst),
        .a_in(reg_rs1_nibble),
        .b_in(rs1_full[15:0]),  // Uses rs2 lower 16 bits actually — will fix in ALU routing
        .product(mul_result_nibble)
    );

    // ALU result mux
    reg [31:0] alu_result_full;

    wire is_shift = (dec_alu_opcode[2:0] == 3'b001) || (dec_alu_opcode[2:0] == 3'b101);
    wire is_mul   = (dec_alu_opcode == 4'b1010);
    wire is_slt   = (dec_alu_opcode[2:1] == 2'b01);  // SLT or SLTU

    reg [3:0] result_nibble;
    always @(*) begin
        if (dec_is_lui)
            result_nibble = dec_imm[{nibble_counter, 2'b00} +: 4];
        else if (is_shift && (dec_is_alu_reg || dec_is_alu_imm))
            result_nibble = shifter_result_nibble;
        else if (is_mul)
            result_nibble = mul_result_nibble;
        else if (is_slt && (dec_is_alu_reg || dec_is_alu_imm))
            result_nibble = (nibble_counter == 3'd0) ? {3'b0, alu_cmp} : 4'd0;
        else
            result_nibble = alu_result_nibble;
    end

    // Writeback control
    // TODO: Could make this easier to read.
    wire writes_rd = dec_is_alu_reg || dec_is_alu_imm || dec_is_lui || dec_is_auipc
                   || dec_is_jal || dec_is_jalr || dec_is_load;
    assign reg_write_en = (state == S_EXECUTE) && writes_rd && !dec_is_load;

    // JAL/JALR link address: PC + instruction byte length
    // instr_len is in 16b parcels (1 or 2), shift left 1 to get bytes
    // TODO: Could make this easier to read.
    wire [31:0] pc_plus_ilen = pc + {29'd0, dec_instr_len, 1'b0};

    assign reg_wdata_nibble = (dec_is_jal || dec_is_jalr)
                              ? pc_plus_ilen[{nibble_counter, 2'b00} +: 4]
                              : result_nibble;

    // Branch condition
    // TODO: Could make this easier to read.
    wire branch_taken = dec_is_jal || dec_is_jalr || dec_is_ret
                      || (dec_is_branch && (dec_mem_opcode[0] ^ alu_cmp));

    // State machine
    always @(posedge clk) begin
        if (!nrst) begin
            state          <= S_FETCH;
            pc             <= 32'd0;
            nibble_counter <= 3'd0;
            instr_reg      <= 32'd0;
            alu_carry      <= 1'b0;
            alu_cmp        <= 1'b1; // EQ starts true
            rs1_full       <= 32'd0;
            alu_result_full <= 32'd0;
            rs2_full       <= 32'd0;
            mem_read       <= 1'b0;
            mem_write      <= 1'b0;
            mem_addr       <= 32'd0;
            mem_wdata      <= 32'd0;
            mem_size       <= 2'b10;
        end else begin
            nibble_counter <= nibble_counter + 3'd1;

            case (state)

                S_FETCH: begin
                    mem_addr <= pc;
                    mem_read <= 1'b1;
                    mem_write <= 1'b0;
                    mem_size <= 2'b10; // word fetch
                    if (mem_ready) begin
                        instr_reg <= mem_rdata;
                        mem_read  <= 1'b0;
                        state     <= S_DECODE;
                    end
                end

                S_DECODE: begin
                    alu_carry       <= (dec_alu_opcode[3] || dec_alu_opcode[1]); // SUB/SLT: carry=1 for invert+1
                    alu_cmp         <= 1'b1; // reset EQ accumulator
                    rs1_full        <= 32'd0;
                    rs2_full        <= 32'd0;
                    alu_result_full <= 32'd0;
                    if (nibble_counter == 3'd7)
                        state <= S_EXECUTE;
                end

                S_EXECUTE: begin
                    // Accumulate full values for shifter and memory ops
                    rs1_full[{nibble_counter, 2'b00} +: 4] <= reg_rs1_nibble;
                    rs2_full[{nibble_counter, 2'b00} +: 4] <= reg_rs2_nibble;

                    // Accumulate full ALU result (used as memory address for loads/stores)
                    alu_result_full[{nibble_counter, 2'b00} +: 4] <= alu_result_nibble;

                    // Track ALU carry/compare across nibbles
                    alu_carry <= alu_carry_out;
                    alu_cmp   <= alu_cmp_out;

                    if (nibble_counter == 3'd7) begin
                        if (dec_is_load || dec_is_store)
                            state <= S_MEM;
                        else
                            state <= S_WRITEBACK;
                    end
                end

                S_WRITEBACK: begin
                    if (branch_taken) begin
                        if (dec_is_jalr || dec_is_ret)
                            pc <= alu_result_full & 32'hFFFFFFFE;
                        else
                            pc <= pc + dec_imm;
                    end else begin
                        pc <= pc + {29'd0, dec_instr_len, 1'b0};
                    end
                    state <= S_FETCH;
                end

                S_MEM: begin
                    mem_addr <= alu_result_full;
                    mem_size <= dec_mem_opcode[2:1];
                    if (dec_is_store) begin
                        mem_write <= 1'b1;
                        mem_wdata <= rs2_full;
                    end else begin
                        mem_read <= 1'b1;
                    end

                    if (mem_ready) begin
                        mem_read  <= 1'b0;
                        mem_write <= 1'b0;
                        if (dec_is_load) begin
                            // Writeback loaded data — for now write nibble-serially in a sub-loop
                            // TODO: implement load writeback to regfile
                        end
                        state <= S_WRITEBACK;
                    end
                end
            endcase
        end
    end
endmodule
