// Testing Alchitry Cu (iCE40-HX8K) compilation using the IIC-OSIC toolchain

module top (
    input  clk,
    output reg [7:0] led
);
    reg [25:0] counter;
    always @(posedge clk) begin
        counter <= counter + 1;
        led <= counter[25:18];
    end
endmodule
