// RV32E (embedded) register file implementation, so 16 registers
// Using 4b access, the registers are rotated 4 bits each clock cycle
// Read bit address is one ahead of write bit address, and both increment every clock cycle.
//
// https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/register.v
module tinymoa_register_file #(parameter REG_COUNT = 16) (
    input clk,
    // input nrst, // Wasted existance.

    input [2:0]  nibble_counter,

    input        write_en,
    input [3:0]  write_dest,  // rd writeback addr (4 bits for RV32E)
    input [3:0]  data_in,     // data to write to write_dest (rd)

    input [3:0]  read_addr_a, // rs1 (port A)
    input [3:0]  read_addr_b, // rs2 (port B)
    output [3:0] data_port_a,
    output [3:0] data_port_b,

    output [23:1] return_addr // $ra register result
);

    // x0 hardcoded, so ignore and setup 15 registers (only 13 with storage) for RV32E
    reg [31:0] registers       [1:REG_COUNT-1];
    reg  [3:0] register_access [0:REG_COUNT-1];

    genvar i;
    generate
        for (i = 0; i < REG_COUNT; i = i + 1) begin
            if (i == 0) begin : gen_reg_x0
                assign register_access[i] = 4'h0;
            end else if (i == 3) begin : gen_reg_gp

                // Generate a "pseudo-harcoded" dynamic combinational value to produce `0x01000400` for the global pointer (gp)
                // Since we read over 8 cycles and update nibble_counter each cycle, we reuse that wire to generate the value
                // This saves us something like 32 FFs by using 2 comparators and simple combinational logic for a 32b value
                // 0x01000400 = 0000_0001_0000_0000_0000_0100_0000_0000
                // Nibble #   =    7    6    5    4    3    2    1    0
                assign register_access[i] = {1'b0, (nibble_counter == 2), 1'b0, (nibble_counter == 6)};
            end else if (i == 4) begin : gen_reg_tp

                // Generate a pseudo-hardcoded value to produce `0x8000000` for the thread pointer (tp) register
                // See the above note on how/why (NOTE: We only use 1 comparator here since only 1 nibble is non-zero)
                // 0x8000000  = 0000_1000_0000_0000_0000_0000_0000_0000
                // Nibble #   =    7    6    5    4    3    2    1    0
                assign register_access[i] = {(nibble_counter == 6), 3'b0};
            end else begin : gen_reg_normal
                always @(posedge clk) begin
                    if (write_en && write_dest == i)
                        registers[i][3:0] <= data_in;
                    else
                        registers[i][3:0] <= registers[i][7:4];
                end

                // Bit rotation logic to handle 4b access to 32b registers.
                // On SG13G2 no buffer is required, use direct assignment.
                // On Sky130A, need to use i_regbuf - see TinyQV "SCL_sky130_fd_sc_hd" elsif case for reference.
                wire [31:4] rotated = {registers[i][3:0], registers[i][31:8]};
                always @(posedge clk) registers[i][31:4] <= rotated;
                assign register_access[i] = registers[i][7:4];
            end
        end
    endgenerate

    assign data_port_a = register_access[read_addr_a];
    assign data_port_b = register_access[read_addr_b];
    assign return_addr = registers[1][31:9];
endmodule

// Nibble-series counter register used as the Program Counter (PC)
// Counts the 32b register 4b at a time over 8 cycles. Hardcoded for simplicity.
// 
// https://github.com/MichaelBell/tinyQV/blob/858986b72975157ebf27042779b6caaed164c57b/cpu/counter.v
module tinymoa_counter (
    input clk,
    input nrst,

    // Counts the currently addressed nibble from 0 to 7
    input [2:0] nibble_counter,
    input increment,

    output [3:0] data,
    output carry_out
);
    reg [31:0] register;
    reg carry_bit;

    // Increment the current nibble (register[7:4])
    wire [3:0] current_nibble = register[7:4];
    wire       increment_amnt = (nibble_counter == 0) ? increment : carry_bit;
    wire [4:0] counter_sum    = current_nibble + increment_amnt;
    wire [3:0] next_nibble    = counter_sum[3:0];
    wire       next_carry_bit = counter_sum[4];

    always @(posedge clk) begin
        if (!nrst) begin
            register[3:0] <= 4'h0;
            carry_bit <= 0;
        end else begin
            register[3:0] <= next_nibble;
            carry_bit <= next_carry_bit;
        end
    end

    // TODO: Add Sky130A compatible buffer.
    // Okay to do on generic FPGA and IHP SG13G2 process - no timing issues
    // Sky130A requires special handling. See TinyQV "SCL_sky130_fd_sc_hd" counter implementation using i_regbuf.
    wire [31:4] rotated = {register[3:0], register[31:8]};
    
    always @(posedge clk) register[31:4] <= rotated;
    assign data = register[7:4];
    assign carry_out = next_carry_bit;
endmodule
