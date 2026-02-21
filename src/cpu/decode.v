// Instruction decoder for TinyMOA CPU
// https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/decode.v
//
// 
/*
    32-bit ALU instructions (opcode in bits [6:2])
    Part of the RV32E base instruction set.
    E stands for "embedded", meaning we only use registers x0-x15 instead of x0-x31
    The RV32E base ISA is compatible with all extensions as of Jan. 2026
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



    Quadrant 3 does not yet exist.




*/


module tinymoa_decode #(parameter REG_ADDR_WIDTH = 4) (
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

    // System instruction (?)
    output reg is_system,

    // ???
    output reg is_auipc



    output reg [3:0] alu_opcode,
    output reg [2:0] mem_opcode, // Bit 0 means branch condition is reversed

    output reg [REG_ADDR_WIDTH-1:0] read_addr_a, // rs1 (port A)
    output reg [REG_ADDR_WIDTH-1:0] read_addr_b, // rs2 (port B)
    output reg [REG_ADDR_WIDTH-1:0] write_dest,

    output reg [2:0] additional_mem_opcode, // ?
    output reg mem_op_increment_reg // ? 
);
    // TODO
endmodule
