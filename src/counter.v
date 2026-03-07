`default_nettype none
`timescale 1ns / 1ps

module tinymoa_counter (
    input  wire       clk,
    input  wire       load_en,
    input  wire       increment,
    input  wire       decrement,
    input  wire       start,
    input  wire [3:0] bus_in,
    output wire [3:0] data_out
);

    reg [31:0] pc_reg;
    reg        carry;

    assign data_out = pc_reg[3:0];
    wire enable = load_en | increment | decrement;

    always @(posedge clk) begin
        if (enable) begin
            if (load_en) begin
                // Shift in the new nibble to the top
                pc_reg <= {bus_in, pc_reg[31:4]};
                carry  <= 1'b0;
            end else if (increment) begin
                // Add 1 if the first nibble, otherwise add the carry.
                {carry, pc_reg[31:28]} <= pc_reg[3:0] + (start? 4'd1 : {3'd0, carry});
                pc_reg[27:0] <= pc_reg[31:4];
            end else if (decrement) begin
                // Subtracting 1 is the same as adding 15 (4'b1111) continuously.
                {carry, pc_reg[31:28]} <= pc_reg[3:0] + 4'd15 + (start? 1'b0 : {3'd0, carry});
                pc_reg[27:0] <= pc_reg[31:4];
            end
        end
    end
endmodule
