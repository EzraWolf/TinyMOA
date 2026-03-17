
`default_nettype none
`timescale 1ns / 1ps

module tinymoa_core (
    input wire        clk,
    input wire        nrst,

    output wire [23:0] mem_addr,
    output reg        mem_read,
    output reg        mem_write,
    output reg [31:0] mem_wdata,
    output reg [1:0]  mem_size, // 00=byte, 01=half, 10=word
    input wire [31:0] mem_rdata,
    input wire        mem_ready,

    output wire [2:0] dbg_state,
    output wire [23:0] dbg_pc
);
    localparam S_FETCH     = 3'd0;
    localparam S_DECODE    = 3'd1;
    localparam S_EXECUTE   = 3'd2;
    localparam S_WRITEBACK = 3'd3;
    localparam S_MEM       = 3'd4;
    localparam S_LOAD_WB   = 3'd5;

    // S_EX2: second 8-cycle execute pass for instructions that need fully-assembled
    // rs1_full / rs2_full / alu_cmp. Selects operation via ex2_type latch
    localparam S_EX2       = 3'd6;

    // ex2_type selects what S_EX2 computes
    localparam EX2_MUL   = 2'd0; // C.MUL: multiplier with b_in=rs2_full[15:0]
    localparam EX2_SHIFT = 2'd1; // SLL/SRL/SRA/SLLI/SRLI/SRAI: barrel shifter with rs1_full
    localparam EX2_SLT   = 2'd2; // SLT/SLTU/SLTI/SLTIU: write {3'b0, alu_cmp} at nc=0

    reg [2:0] state;
    reg [1:0] ex2_type;
    reg [2:0] nibble_counter;

    assign dbg_state = state;

    reg [23:0] pc; // 24b = 16 MB address space
    wire [3:0] pc_nibble = (nibble_counter < 3'd6) ? pc[{nibble_counter, 2'b00} +: 4] : 4'd0;
    assign dbg_pc = pc;

    reg [31:0] instr_reg;

    reg [23:0] mem_addr_reg;
    assign mem_addr = mem_addr_reg;

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
        .a_in(dec_is_auipc ? pc_nibble : alu_a_nibble),
        .b_in(alu_b_nibble),
        .cmp_in(alu_cmp),
        .carry_in(alu_carry),
        .result(alu_result_nibble),
        .cmp_out(alu_cmp_out),
        .carry_out(alu_carry_out)
    );

    // rs1_full / rs2_full are assembled nibble-by-nibble during S_EXECUTE.
    // Required by the shifter (needs complete rs1), multiplier (needs complete rs2),
    // and store data path. Not valid until S_EXECUTE completes (nc=7).
    reg [31:0] rs1_full;
    reg [31:0] rs2_full;

    // Instruction classification (combinational on decoder outputs)
    wire is_shift = (dec_alu_opcode[2:0] == 3'b001) || (dec_alu_opcode[2:0] == 3'b101);
    wire is_mul   = (dec_alu_opcode == 4'b1010);
    wire is_slt   = (dec_alu_opcode[2:1] == 2'b01); // SLT or SLTU

    // Instructions that need a second execute pass (S_EX2) because their result
    // depends on rs1_full / rs2_full / alu_cmp which are only complete after nc=7.
    wire is_ex2_needed = is_mul
        || (is_shift && (dec_is_alu_reg || dec_is_alu_imm))
        || (is_slt   && (dec_is_alu_reg || dec_is_alu_imm));

    // Shifter: shift amount from rs2 value (R-type) or immediate (I-type).
    // Both rs2_full and dec_imm are correct sources; rs2_full is only valid in S_EX2.
    wire [4:0] shift_amnt_w = (is_shift && dec_is_alu_reg) ? rs2_full[4:0] : dec_imm[4:0];
    wire [3:0] shifter_result_nibble;

    tinymoa_shifter shifter (
        .opcode(dec_alu_opcode[3:2]),
        .nibble_counter(nibble_counter),
        .data_in(rs1_full),
        .shift_amnt(shift_amnt_w),
        .result(shifter_result_nibble)
    );

    // Multiplier: reset accumulator at the nc=7 boundary of S_EXECUTE→S_EX2(MUL).
    // S_EX2 starts at nc=0 with a clean accumulator and correct b_in=rs2_full[15:0].
    wire mul_clr = (state == S_EXECUTE) && (nibble_counter == 3'd7) && is_mul;
    wire [3:0] mul_result_nibble;

    tinymoa_multiplier #(.B_IN_WIDTH(16)) multiplier (
        .clk(clk),
        .nrst(nrst),
        .mul_clr(mul_clr),
        .a_in(reg_rs1_nibble),
        .b_in(rs2_full[15:0]),
        .product(mul_result_nibble)
    );

    reg [31:0] load_data;       // Latched mem_rdata for WB
    reg        load_top_bit;    // Sign extension bit
    reg [2:0]  load_wb_count;   // Count for S_LOAD_WB

    // Sign extension fills upper nibbles with sign bit for byte/half loads
    wire load_past_boundary = (dec_mem_opcode[1:0] == 2'b00 && nibble_counter > 3'd1)   // byte: nibbles 2-7
                           || (dec_mem_opcode[1:0] == 2'b01 && nibble_counter > 3'd3);  // half: nibbles 4-7
    wire [3:0] load_nibble = load_past_boundary ? {4{load_top_bit}}
                                                : load_data[{nibble_counter, 2'b00} +: 4];

    // ALU result mux for the standard (non-EX2) writeback path
    // Only used during S_EXECUTE when is_ex2_needed=0
    reg [31:0] alu_result_full;
    reg [3:0] result_nibble;
    always @(*) begin
        if (dec_is_lui)
            result_nibble = dec_imm[{nibble_counter, 2'b00} +: 4];
        else
            result_nibble = alu_result_nibble;
    end

    // S_EX2 result mux: selects output nibble based on ex2_type latch.
    reg [3:0] ex2_nibble;
    always @(*) begin
        case (ex2_type)
            EX2_MUL:   ex2_nibble = mul_result_nibble;
            EX2_SHIFT: ex2_nibble = shifter_result_nibble;
            EX2_SLT:   ex2_nibble = (nibble_counter == 3'd0) ? {3'b0, alu_cmp} : 4'd0;
            default:   ex2_nibble = 4'd0;
        endcase
    end

    // Writeback control:
    // - Standard ALU/LUI/AUIPC/JAL/JALR write during S_EXECUTE (excluding ex2 cases)
    // - Load writeback uses S_LOAD_WB
    // - MUL/SHIFT/SLT writeback uses S_EX2
    wire writes_rd = dec_is_alu_reg || dec_is_alu_imm || dec_is_lui || dec_is_auipc
                   || dec_is_jal || dec_is_jalr || dec_is_load;
    assign reg_write_en = ((state == S_EXECUTE) && writes_rd && !dec_is_load && !is_ex2_needed)
                        || (state == S_LOAD_WB)
                        || (state == S_EX2);

    // JAL/JALR link address: PC + instruction byte length
    wire [23:0] pc_plus_ilen = pc + {21'd0, dec_instr_len, 1'b0};
    wire [3:0] pc_plus_ilen_nibble = (nibble_counter < 3'd6)
                                   ? pc_plus_ilen[{nibble_counter, 2'b00} +: 4] : 4'd0;

    assign reg_wdata_nibble = (state == S_LOAD_WB)              ? load_nibble
                            : (state == S_EX2)                  ? ex2_nibble
                            : (dec_is_jal || dec_is_jalr)       ? pc_plus_ilen_nibble
                            : result_nibble;

    // Branch condition
    wire branch_taken = dec_is_jal || dec_is_jalr || dec_is_ret
                      || (dec_is_branch && (dec_mem_opcode[0] ^ alu_cmp));

    // State machine
    always @(posedge clk) begin
        if (!nrst) begin
            state           <= S_FETCH;
            ex2_type        <= EX2_MUL;
            pc              <= 24'd0;
            nibble_counter  <= 3'd0;
            instr_reg       <= 32'd0;
            alu_carry       <= 1'b0;
            alu_cmp         <= 1'b1; // EQ starts true
            rs1_full        <= 32'd0;
            alu_result_full <= 32'd0;
            rs2_full        <= 32'd0;
            load_data       <= 32'd0;
            load_top_bit    <= 1'b0;
            load_wb_count   <= 3'd0;
            mem_addr_reg    <= 24'd0;
            mem_read        <= 1'b0;
            mem_write       <= 1'b0;
            mem_wdata       <= 32'd0;
            mem_size        <= 2'b10;
        end else begin
            nibble_counter <= nibble_counter + 3'd1;

            case (state)

                S_FETCH: begin
                    mem_addr_reg <= pc;
                    mem_read <= 1'b1;
                    mem_write <= 1'b0;
                    mem_size <= 2'b10; // word fetch
                    if (mem_ready) begin
                        // When PC[1]=1, the 16b compressed instruction sits in
                        // the upper half of the fetched word — shift it into place.
                        instr_reg <= pc[1] ? {16'd0, mem_rdata[31:16]} : mem_rdata;
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
                    // Accumulate full register values and ALU result nibble-by-nibble.
                    // These are used by S_EX2 (shifts/mul/slt) and S_MEM (address/store data).
                    rs1_full[{nibble_counter, 2'b00} +: 4] <= reg_rs1_nibble;
                    rs2_full[{nibble_counter, 2'b00} +: 4] <= reg_rs2_nibble;
                    alu_result_full[{nibble_counter, 2'b00} +: 4] <= alu_result_nibble;
                    alu_carry <= alu_carry_out;
                    alu_cmp   <= alu_cmp_out;

                    if (nibble_counter == 3'd7) begin
                        if (dec_is_load || dec_is_store) begin
                            state <= S_MEM;
                        end else if (is_ex2_needed) begin
                            state <= S_EX2;
                            if (is_mul)        ex2_type <= EX2_MUL;
                            else if (is_shift) ex2_type <= EX2_SHIFT;
                            else               ex2_type <= EX2_SLT;
                        end else begin
                            state <= S_WRITEBACK;
                        end
                    end
                end

                S_WRITEBACK: begin
                    if (branch_taken) begin
                        if (dec_is_jalr || dec_is_ret)
                            pc <= alu_result_full[23:0] & 24'hFFFFFE;
                        else
                            pc <= pc + dec_imm[23:0];
                    end else begin
                        pc <= pc + {21'd0, dec_instr_len, 1'b0};
                    end
                    state <= S_FETCH;
                end

                S_MEM: begin
                    mem_addr_reg <= alu_result_full[23:0];
                    mem_size <= dec_mem_opcode[1:0];
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
                            load_data <= mem_rdata;
                            case (dec_mem_opcode[1:0])
                                2'b00: load_top_bit <= ~dec_mem_opcode[2] & mem_rdata[7];   // LB sign
                                2'b01: load_top_bit <= ~dec_mem_opcode[2] & mem_rdata[15];  // LH sign
                                default: load_top_bit <= 1'b0;                              // LW
                            endcase
                            load_wb_count <= 3'd0;
                            state <= S_LOAD_WB;
                        end else begin
                            state <= S_WRITEBACK;
                        end
                    end
                end

                S_LOAD_WB: begin
                    load_wb_count <= load_wb_count + 3'd1;
                    if (load_wb_count == 3'd7)
                        state <= S_WRITEBACK;
                end

                // Second 8 cycle execute pass. rs1_full, rs2_full, and alu_cmp are all
                // fully assembled from S_EXECUTE. reg_write_en is active; reg_wdata_nibble
                // selects ex2_nibble which dispatches on ex2_type.
                S_EX2: begin
                    if (nibble_counter == 3'd7)
                        state <= S_WRITEBACK;
                end
            endcase
        end
    end
endmodule
