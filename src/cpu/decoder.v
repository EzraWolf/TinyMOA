/*. Instruction decoder based on TinyQV
    https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/decode.v

    32-bit ALU instructions (opcode in bits [6:2])
    Part of the RV32E base instruction set.
    E stands for "embedded", meaning we only use registers x0-x15 instead of x0-x31
    The RV32E base ISA is compatible with all extensions as of Feb. 2026
    https://ww1.microchip.com/downloads/aemDocuments/documents/FPGA/ProductDocuments/UserGuides/ip_cores/directcores/riscvspec.pdf

    opcode[6:2]

    - ADD   01100, 000, 0
    - ADDI  00100, 000, -
    - SUB   01100, 000, 1
    - SLT   01100, 010, 0
    - SLTI  00100, 010, -
    - SLTU  01100, 011, 0
    - SLTIU 00100, 011, -
    - AND   01100, 111, 0
    - ANDI  00100, 111, -
    - OR    01100, 110, 0
    - ORI   00100, 110, -
    - XOR   01100, 100, 0
    - XORI  00100, 100, -
    - SLL   01100, 001, 0
    - SLLI  00100, 001, -
    - SRL   01100, 101, 0
    - SRLI  00100, 101, -
    - SRA   01100, 101, 1
    - SRAI  00100, 101, -




    16-bit instructions
    Organized into 3 quadrants based on bits [1:0]

    Quadrant 0 (bits [1:0] == 00)
    C.ADDI4SPN

    C.LW
    C.SW

    C.LBU
    C.LHU
    C.LH
    C.SB
    C.SH

    C.SCXT



    Quadrant 1 (bits [1:0] == 01)
    C.ADDI16SP  CI

    C.ADDI      CI
    C.LI        CI
    C.LUI       CI
    C.SRLI      CB
    C.SRAI      CB 
    C.ANDI      CB
    C.SUB       CR
    C.XOR       CR
    C.OR        CR
    C.AND       CR
    C.NOT       CZEXT
    C.ZEXT.B    CZEXT
    C.ZEXT.H    CZEXT

    C.JAL       CJ
    C.J         CJ
    C.BEQZ      CB
    C.BNEZ      CB



    Quadrant 2 (bits [1:0] == 10)
    C.LWSP      CI
    C.SWSP      CSS
    C.LWTP      CLWTP
    C.SWTP      CLWTP

    C.MV        CR
    C.ADD       CR
    C.SLLI      CI
    C.MUL16     CR

    C.JR        CR
    C.JALR      CR

    C.EBREAK    CR

    C.LCXT      CLCXT



    Quadrant 3 is does not exist, it is just 32b instructions.
*/


module tinymoa_decoder #(parameter REG_ADDR_WIDTH = 4) (
    input [31:0] instr,

    output reg [31:0] imm,

    // Data movement instructions
    output reg is_load,
    output reg is_store,
    output reg is_lui,

    // ALU instructions
    output reg is_alu_reg,
    output reg is_alu_imm,

    // Branch instructions
    output reg is_branch,
    output reg is_jal,
    output reg is_jalr,
    output reg is_ret,

    // System instruction
    output reg is_system,

    output reg is_auipc,

    output reg is_compressed,

    output [2:1] instr_len,

    output reg [3:0] alu_opcode,
    output reg [2:0] mem_opcode, // Bit 0 means branch condition is reversed

    output reg [REG_ADDR_WIDTH-1:0] read_addr_a, // rs1 (port A)
    output reg [REG_ADDR_WIDTH-1:0] read_addr_b, // rs2 (port B)
    output reg [REG_ADDR_WIDTH-1:0] write_dest,

    output reg [2:0] additional_mem_opcode,
    output reg mem_op_increment_reg
);

    assign instr_len = (instr[1:0] == 2'b11) ? 2'b10 : 2'b01;

    // 32b base immediates
    wire [31:0] u_imm = {    instr[31],   instr[30:12], {12{1'b0}}};
    wire [31:0] i_imm = {{21{instr[31]}}, instr[30:20]};
    wire [31:0] s_imm = {{21{instr[31]}}, instr[30:25],instr[11:7]};
    wire [31:0] b_imm = {{20{instr[31]}}, instr[7],instr[30:25],instr[11:8],1'b0};
    wire [31:0] j_imm = {{12{instr[31]}}, instr[19:12],instr[20],instr[30:21],1'b0};

    // TODO: Convert to purely 16b so go from 8 cycles/instruction to 4 cycles.
    // 16b compressed immediates
    wire [31:0] c_lwsp_imm     = {24'b0, instr[3:2], instr[12], instr[6:4], 2'b00};
    wire [31:0] c_swsp_imm     = {24'b0, instr[8:7], instr[12:9], 2'b00};
    wire [31:0] c_lsw_imm      = {25'b0, instr[5], instr[12:10], instr[6], 2'b00};  // LW and SW
    wire [31:0] c_lsh_imm      = {30'b0, instr[5], 1'b0};  // LH(U) and SH
    wire [31:0] c_lsb_imm      = {30'b0, instr[5], instr[6]};  // LBU and SB
    wire [31:0] c_j_imm        = {{21{instr[12]}}, instr[8], instr[10:9], instr[6], instr[7], instr[2], instr[11], instr[5:3], 1'b0};
    wire [31:0] c_b_imm        = {{24{instr[12]}}, instr[6:5], instr[2], instr[11:10], instr[4:3], 1'b0};
    wire [31:0] c_alu_imm      = {{27{instr[12]}}, instr[6:2]};          // ADDI, LI, shifts, ANDI
    wire [31:0] c_lui_imm      = {{15{instr[12]}}, instr[6:2], 12'b0};
    wire [31:0] c_addi16sp_imm = {{23{instr[12]}}, instr[4:3], instr[5], instr[2], instr[6], 4'b0};
    wire [31:0] c_addi4sp_imm  = {22'b0, instr[10:7], instr[12:11], instr[5], instr[6], 2'b0};
    wire [31:0] c_scxt_imm     = {{23{instr[12]}}, instr[9:7], instr[10], instr[11], 4'b0};

    // Quadrant detection for compressed instructions
    wire [1:0] c_quadrant = instr[1:0];
    wire [2:0] c_funct3 = instr[15:13];
    
    always @(*) begin
        additional_mem_opcode = 3'b000;
        mem_op_increment_reg = 1;
        is_ret = 0;
        is_compressed = 0;

        // ================================================================
        // 32-bit Base Instructions (8 cycles @ 4-bit/cycle)
        // ================================================================
        if (instr[1:0] == 2'b11) begin
            is_load    =  (instr[6:2] == 5'b00000); // rd <- mem[rs1+i_imm]
            is_alu_imm =  (instr[6:2] == 5'b00100); // rd <- rs1 OP i_imm
            is_auipc   =  (instr[6:2] == 5'b00101); // rd <- PC + u_imm
            is_store   =  (instr[6:2] == 5'b01000); // mem[rs1+s_imm] <- rs2
            is_alu_reg =  (instr[6:2] == 5'b01100); // rd <- rs1 OP rs2
            is_lui     =  (instr[6:2] == 5'b01101); // rd <- u_imm
            is_branch  =  (instr[6:2] == 5'b11000); // if(rs1 OP rs2) PC<-PC+b_imm
            is_jalr    =  (instr[6:2] == 5'b11001); // rd <- PC+4; PC<-rs1+i_imm
            is_jal     =  (instr[6:2] == 5'b11011); // rd <- PC+4; PC<-PC+j_imm
            is_system  =  (instr[6:2] == 5'b11100); // rd <- csr - NYI

            // Determine immediate. Hopefully muxing here is reasonable.
            if (is_auipc || is_lui) imm = u_imm;
            else if (is_store) imm = s_imm;
            else if (is_branch) imm = b_imm;
            else if (is_jal) imm = j_imm;
            else imm = i_imm;

            // Determine alu op
            if (is_load || is_auipc || is_store || is_jalr || is_jal) alu_opcode = 4'b0000;  // ADD
            else if (is_branch) alu_opcode = {1'b0, !instr[14], instr[14:13]};
            else if (instr[26] && is_alu_reg) alu_opcode = {1'b1, instr[27:26], instr[13]};  // MUL or CZERO
            else alu_opcode = {instr[30] && (instr[5] || instr[13:12] == 2'b01),instr[14:12]};

            mem_opcode = instr[14:12];
            if ((is_load || is_store) && instr[13:12] == 2'b11) begin
                // TinyQV custom: 2 or 4 loads/stores to consecutive registers
                mem_opcode = 3'b010;
                additional_mem_opcode = {1'b0, instr[14], 1'b1};
            end
            if (is_store && instr[14:12] == 3'b110) begin
                // TinyQV custom: 4 stores from the same reg (fast memset)
                mem_opcode = 3'b010;
                additional_mem_opcode = {1'b0, instr[14], 1'b1};
                mem_op_increment_reg = 0;
            end

            read_addr_a = instr[15+:REG_ADDR_WIDTH];
            read_addr_b = instr[20+:REG_ADDR_WIDTH];
            write_dest  = instr[ 7+:REG_ADDR_WIDTH];
        
        // ================================================================
        // 16-bit Compressed Instructions (4 cycles @ 4-bit/cycle)
        // ================================================================
        end else begin
            is_compressed = 1;
            is_load         = 0;
            is_alu_imm      = 0;
            is_auipc        = 0;
            is_store        = 0;
            is_alu_reg      = 0;
            is_lui          = 0;
            is_branch       = 0;
            is_jalr         = 0;
            is_jal          = 0;
            is_system       = 0;
            imm = {32{1'bx}};
            alu_opcode = 4'b0000;
            mem_opcode = 3'bxxx;
            read_addr_a = {REG_ADDR_WIDTH{1'bx}};
            read_addr_b = {REG_ADDR_WIDTH{1'bx}};
            write_dest = {REG_ADDR_WIDTH{1'bx}};

            case ({c_quadrant, c_funct3})
                // ============================================================
                // Quadrant 00 - Loads, Stores, and Stack Operations
                // ============================================================
                5'b00000: begin // C.ADDI4SPN (CIW-Type) 
                    is_alu_imm = 1;
                    imm = c_addi4sp_imm;
                    read_addr_a = 4'd2;
                    write_dest  = {1'b1, instr[4:2]};
                end
                5'b00010: begin // LW
                    is_load = 1;
                    mem_opcode = 3'b010;
                    imm = c_lsw_imm;
                    read_addr_a = {1'b1, instr[9:7]};
                    write_dest  = {1'b1, instr[4:2]};
                end 
                5'b00100: begin // Load/store byte or halfword
                    imm = instr[10] ? c_lsh_imm : c_lsb_imm;
                    read_addr_a = {1'b1, instr[9:7]};
                    if (instr[11]) begin
                        is_store = 1;
                        mem_opcode = {2'b00, instr[10]};
                        read_addr_b = {1'b1, instr[4:2]};
                    end else begin
                        is_load = 1;
                        mem_opcode = {~(instr[10] & instr[6]), 1'b0, instr[10]};
                        write_dest = {1'b1, instr[4:2]};
                    end
                end
                5'b00110: begin // SW
                    is_store = 1;
                    mem_opcode = 3'b010;
                    imm = c_lsw_imm;
                    read_addr_a = {1'b1, instr[9:7]};
                    read_addr_b = {1'b1, instr[4:2]};
                end
                5'b00111: begin // SCXT: Store rs2[2:0]+1 contiguous registers starting at {rs2[4:3], 3'b001}
                    is_store = 1;    //  from address imm(gp) (imm is a sign-extended 6-bit immediate multiplied by 16)
                    mem_opcode = 3'b010;
                    imm = c_scxt_imm;
                    read_addr_a = 4'd3;
                    read_addr_b = {instr[5], 3'b001};
                    additional_mem_opcode = instr[4:2];
                end
                
                // ============================================================
                // Quadrant 01 - ALU, Control Flow, and Immediates
                // ============================================================
                5'b01000: begin // C.ADDI (CI-Type)
                    is_alu_imm = 1;
                    imm = c_alu_imm;
                    read_addr_a = instr[11:7];
                    write_dest  = instr[11:7];
                end
                5'b01001: begin // JAL
                    is_jal = 1;
                    imm = c_j_imm;
                    write_dest  = 4'd1;
                end
                5'b01010: begin // LI
                    is_alu_imm = 1;
                    imm = c_alu_imm;
                    read_addr_a = 4'd0;
                    write_dest  = instr[11:7];
                end
                5'b01011: begin // ADDI16SP/LUI
                    write_dest  = instr[11:7];
                    if (instr[11:7] == 4'd2) begin
                        is_alu_imm = 1;
                        imm = c_addi16sp_imm;
                        read_addr_a = 4'd2;
                    end else begin
                        is_lui = 1;
                        imm = c_lui_imm;
                    end
                end
                5'b01100: begin // ALU
                    read_addr_a = {1'b1, instr[9:7]};
                    read_addr_b = {1'b1, instr[4:2]};
                    write_dest  = {1'b1, instr[9:7]};
                    imm = c_alu_imm;
                    if (instr[11:10] != 2'b11) begin
                        is_alu_imm = 1;
                        if (instr[11] == 1'b0) begin // SRx
                            alu_opcode = {instr[10], 3'b101};
                        end else begin
                            alu_opcode = 4'b0111;
                        end
                    end else if (instr[12]) begin
                        is_alu_imm = 1;
                        case (instr[4:2])
                            3'b101: begin  // NOT
                                    alu_opcode = 4'b0100; // XOR
                                    imm = 32'hffffffff;
                            end
                            default: begin // ZEXT
                                    alu_opcode = 4'b0111; // AND
                                    imm = {16'h0000, {8{instr[3]}}, 8'hff};
                            end
                        endcase
                        
                    end else begin
                        is_alu_reg = 1;
                        case (instr[6:5])
                            2'b00: alu_opcode = 4'b1000;  // SUB
                            2'b01: alu_opcode = 4'b0100;  // XOR
                            2'b10: alu_opcode = 4'b0110;  // OR
                            2'b11: alu_opcode = 4'b0111;  // AND
                        endcase
                    end
                end
                5'b01101: begin // J
                    is_jal = 1;
                    imm = c_j_imm;
                    write_dest  = 4'd0;
                end                
                5'b01110: begin // BEQZ
                    is_branch = 1;
                    imm = c_b_imm;
                    read_addr_a = {1'b1, instr[9:7]};
                    read_addr_b = 4'd0;
                    alu_opcode = 4'b0100;
                    mem_opcode = 3'b000;
                end    
                5'b01111: begin // BNEZ
                    is_branch = 1;
                    imm = c_b_imm;
                    read_addr_a = {1'b1, instr[9:7]};
                    read_addr_b = 4'd0;
                    alu_opcode = 4'b0100;
                    mem_opcode = 3'b001;
                end
                
                // ============================================================
                // Quadrant 10 - Stack-relative, Register Ops, and Jumps  
                // ============================================================
                5'b10000: begin // C.SLLI (CI-Type)
                    is_alu_imm = 1;
                    imm = c_alu_imm;
                    read_addr_a = instr[11:7];
                    write_dest  = instr[11:7];
                    alu_opcode = 4'b0001;
                end
                5'b10001: begin // LCXT: Load rd[2:0]+1 contiguous registers starting at {rd[4:3], 3'b001}
                    is_load = 1;     //  from address imm(gp) (imm is a sign-extended 6-bit immediate multiplied by 16)
                    mem_opcode = 3'b010;
                    imm = c_addi16sp_imm;
                    read_addr_a = 4'd3;
                    write_dest  = {instr[10], 3'b001};
                    additional_mem_opcode = instr[9:7];
                end
                5'b10010: begin // LWSP
                    is_load = 1;
                    mem_opcode = 3'b010;
                    imm = c_lwsp_imm;
                    read_addr_a = 4'd2;
                    write_dest  = instr[11:7];
                end
                5'b10011: begin // LWTP
                    is_load = 1;
                    mem_opcode = 3'b010;
                    imm = c_lwsp_imm;
                    read_addr_a = 4'd4;
                    write_dest  = instr[11:7];
                end
                5'b10100: begin 
                    if (instr[12]) begin  // C.ADD: bit 12 = 1
                        is_alu_reg = 1;
                        read_addr_a = instr[11:7];
                        read_addr_b = instr[6:2];
                        write_dest  = instr[11:7];
                    end else if (instr[6:2] == 0) begin  // JALR or EBREAK: bit 12 = 0, rs2 = 0
                        if (instr[11:7] == 0) begin  // EBREAK
                            is_system = 1;
                            imm = 1;
                        end else begin // JALR
                            if (instr[11:7] == 4'd1) is_ret = 1;
                            is_jalr = 1;
                            imm = 0;
                            read_addr_a = instr[11:7];
                            write_dest = 4'd1;  // x1 = ra
                        end
                    end else begin  // C.MV: bit 12 = 0, rs2 != 0
                        is_alu_reg = 1;
                        read_addr_a = 4'd0;
                        read_addr_b = instr[6:2];
                        write_dest  = instr[11:7];
                    end
                end
                5'b10101: begin // C.MUL16
                    is_alu_reg = 1;
                    alu_opcode = 4'b1010;
                    read_addr_a = instr[11:7];
                    read_addr_b = instr[6:2];
                    write_dest  = instr[11:7];
                end
                5'b10110: begin // SWSP
                    is_store = 1;
                    mem_opcode = 3'b010;
                    imm = c_swsp_imm;
                    read_addr_a = 4'd2;
                    read_addr_b = instr[6:2];
                end
                5'b10111: begin // SWTP
                    is_store = 1;
                    mem_opcode = 3'b010;
                    imm = c_swsp_imm;
                    read_addr_a = 4'd4;
                    read_addr_b = instr[6:2];
                end
                default: begin
                    is_system = 1;
                    imm = 32'd2;
                end
            endcase
        end
    end

endmodule
