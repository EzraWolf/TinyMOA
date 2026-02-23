"""Test suite for RV32E register file."""

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


@cocotb.test()
async def test_all_registers(dut):
    """Test write/read for all 16 registers including hardcoded ones."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())
    
    dut.rstn.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rstn.value = 1
    dut.wr_en.value = 1
    
    hardcoded = {
        0: 0x00000000, # x0 is $zero
        3: 0x01000400, # x3 is $ga
        4: 0x08000000  # x4 is $tp
    }
    
    for reg in range(16):
        dut.rs1.value = reg
        dut.rs2.value = 0
        dut.rd.value = reg
        
        test_value = 0xA5000000 | (reg << 16) | reg
        dut.rd_in.value = test_value
        await ClockCycles(dut.clk, 8)
        
        dut.wr_en.value = 0
        await ClockCycles(dut.clk, 8)
        
        # Read
        dut.wr_en.value = 1
        dut.rd_in.value = 0
        await ClockCycles(dut.clk, 1)
        
        read_value = int(dut.rs1_out.value)
        expected = hardcoded.get(reg, test_value)
        
        assert read_value == expected, f"x{reg}: got {hex(read_value)}, expected {hex(expected)}"
        
        await ClockCycles(dut.clk, 7)


@cocotb.test()
async def test_dual_port_read(dut):
    """Test reading two different registers simultaneously."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())
    
    test_value_a = 0xDEADBEEF
    test_value_b = 0xFEEDC0DE

    dut.rstn.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rstn.value = 1
    dut.wr_en.value = 1
    
    dut.rs1.value = 1
    dut.rs2.value = 2
    dut.rd.value = 1
    dut.rd_in.value = test_value_a
    await ClockCycles(dut.clk, 8)
    
    dut.rd.value = 2
    dut.rd_in.value = test_value_b
    await ClockCycles(dut.clk, 8)
    
    dut.wr_en.value = 0
    await ClockCycles(dut.clk, 8)
    
    # Read
    dut.wr_en.value = 1
    dut.rd_in.value = 0
    await ClockCycles(dut.clk, 1)
    
    rs1_value = int(dut.rs1_out.value)
    rs2_value = int(dut.rs2_out.value)
    
    assert rs1_value == test_value_a, f"rs1: got {hex(rs1_value)}, expected {hex(test_value_a)}"
    assert rs2_value == test_value_b, f"rs2: got {hex(rs2_value)}, expected {hex(test_value_b)}"


@cocotb.test()
async def test_write_enable_gating(dut):
    """Verify writes only happen when wr_en is high."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())
    
    dut.rstn.value = 0
    await ClockCycles(dut.clk, 2)
    dut.rstn.value = 1
    dut.wr_en.value = 1
    
    dut.rs1.value = 5
    dut.rd.value = 5
    dut.rd_in.value = 0xAAAAAAAA
    await ClockCycles(dut.clk, 8)
    
    dut.wr_en.value = 0
    dut.rd_in.value = 0x55555555
    await ClockCycles(dut.clk, 8)
    
    dut.wr_en.value = 1
    dut.rd_in.value = 0
    await ClockCycles(dut.clk, 1)
    
    read_value = int(dut.rs1_out.value)
    assert read_value == 0xAAAAAAAA, \
        f"Write enable failed: got {hex(read_value)}, expected 0xAAAAAAAA"
