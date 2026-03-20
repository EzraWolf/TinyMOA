import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_sram(dut):
    """Initialize SRAM with clock and reset."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.write_en.value = 0
    dut.read_en.value = 0
    dut.write_addr.value = 0
    dut.write_data.value = 0
    dut.read_addr.value = 0
    await ClockCycles(dut.clk, 2)
    dut.nrst.value = 1
    await ClockCycles(dut.clk, 1)

    return dut


@cocotb.test()
async def test_sram_write_read(dut):
    """Test basic write and read operations on SRAM."""
    await setup_sram(dut)

    # Write test values to different addresses
    test_data = [
        (0, 0x12345678),
        (1, 0x9ABCDEF0),
        (255, 0xDEADBEEF),
        (511, 0xCAFEBABE),
    ]

    # Write phase
    for addr, data in test_data:
        dut.write_addr.value = addr
        dut.write_data.value = data
        dut.write_en.value = 1
        await ClockCycles(dut.clk, 1)

    dut.write_en.value = 0

    # Read phase - verify data was written correctly
    for addr, expected_data in test_data:
        dut.read_addr.value = addr
        dut.read_en.value = 1
        await ClockCycles(dut.clk, 1)

        actual_data = int(dut.read_data.value)
        assert actual_data == expected_data, (
            f"Address {addr}: Expected 0x{expected_data:08X}, got 0x{actual_data:08X}"
        )

    dut.read_en.value = 0


@cocotb.test()
async def test_sram_simultaneous_read_write(dut):
    """Test simultaneous read from one address and write to another."""
    await setup_sram(dut)

    # Pre-populate some addresses
    dut.write_en.value = 1
    for i in range(5):
        dut.write_addr.value = i
        dut.write_data.value = 0x1000 + i
        await ClockCycles(dut.clk, 1)

    dut.write_en.value = 0
    await ClockCycles(dut.clk, 1)

    # Now do simultaneous read and write
    dut.read_addr.value = 0
    dut.read_en.value = 1
    dut.write_addr.value = 10
    dut.write_data.value = 0x5555
    dut.write_en.value = 1
    await ClockCycles(dut.clk, 1)

    # Read should return data from address 0
    read_data = int(dut.read_data.value)
    assert read_data == 0x1000, f"Expected 0x1000, got 0x{read_data:08X}"

    # Write to address 10 should complete
    dut.read_en.value = 0
    dut.write_en.value = 0
    dut.read_addr.value = 10
    dut.read_en.value = 1
    await ClockCycles(dut.clk, 1)

    read_data = int(dut.read_data.value)
    assert read_data == 0x5555, f"Expected 0x5555, got 0x{read_data:08X}"
