import random
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge


async def setup_dut(dut):
    """Initialize the clock, reset the TB, and flush the DUT to 0."""
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Safely initialize signals
    dut.tb_nrst.value = 1
    dut.load_en.value = 0
    dut.increment.value = 0
    dut.decrement.value = 0
    dut.load_data.value = 0

    # Reset the testbench wrapper
    dut.tb_nrst.value = 0
    await ClockCycles(dut.clk, 1)
    dut.tb_nrst.value = 1

    # 8-cycle flush to 0
    dut.load_en.value = 1
    dut.load_data.value = 0
    await ClockCycles(dut.clk, 8)
    dut.load_en.value = 0


@cocotb.test()
async def test_load(dut):
    """Test a single load of a random 32b value"""
    await setup_dut(dut)
    value = random.randint(0, 0xFFFFFFFF)

    dut.load_en.value = 1
    dut.load_data.value = value
    await ClockCycles(dut.clk, 8)
    dut.load_en.value = 0

    # Wait half a cycle for the final register updates to propagate
    await FallingEdge(dut.clk)
    actual = int(dut.result.value)
    assert actual == value, f"Load Failed: Expected {hex(value)}, got {hex(actual)}"


@cocotb.test()
async def test_load_sequential(dut):
    """Load values sequentially in a loop without edge triggers"""
    await setup_dut(dut)

    dut.load_en.value = 1

    for _ in range(100):
        value = random.randint(0, 0xFFFFFFFF)
        dut.load_data.value = value

        await ClockCycles(dut.clk, 8)

        # Check mid-cycle to avoid reading pre-update flip-flops
        await FallingEdge(dut.clk)
        actual = int(dut.result.value)
        assert actual == value, (
            f"Sequential Load Failed: Expected {hex(value)}, got {hex(actual)}"
        )

    dut.load_en.value = 0


@cocotb.test()
async def test_increment(dut):
    """Test continuous incrementing"""
    await setup_dut(dut)
    expected = random.randint(0, 0xFFFFFFFF - 200)

    dut.load_en.value = 1
    dut.load_data.value = expected
    await ClockCycles(dut.clk, 8)

    dut.load_en.value = 0
    dut.increment.value = 1

    for _ in range(100):
        await ClockCycles(dut.clk, 8)

        await FallingEdge(dut.clk)
        expected = (expected + 1) & 0xFFFFFFFF
        actual = int(dut.result.value)
        assert actual == expected, (
            f"Increment Failed: Expected {hex(expected)}, got {hex(actual)}"
        )

    dut.increment.value = 0


@cocotb.test()
async def test_decrement(dut):
    """Test continuous decrementing"""
    await setup_dut(dut)
    expected = random.randint(200, 0xFFFFFFFF)

    dut.load_en.value = 1
    dut.load_data.value = expected
    await ClockCycles(dut.clk, 8)

    dut.load_en.value = 0
    dut.decrement.value = 1

    for _ in range(100):
        await ClockCycles(dut.clk, 8)

        await FallingEdge(dut.clk)
        expected = (expected - 1) & 0xFFFFFFFF
        actual = int(dut.result.value)
        assert actual == expected, (
            f"Decrement Failed: Expected {hex(expected)}, got {hex(actual)}"
        )

    dut.decrement.value = 0


@cocotb.test()
async def test_rollover(dut):
    """Test incrementing past the max 32b limit"""
    await setup_dut(dut)

    dut.load_en.value = 1
    dut.load_data.value = 0xFFFFFFFF
    await ClockCycles(dut.clk, 8)

    dut.load_en.value = 0
    dut.increment.value = 1
    await ClockCycles(dut.clk, 8)
    dut.increment.value = 0

    await FallingEdge(dut.clk)
    actual = int(dut.result.value)
    assert actual == 0x00000000, (
        f"Rollover Failed: Expected 0x00000000, got {hex(actual)}"
    )


@cocotb.test()
async def test_rollunder(dut):
    """Test decrementing past the min 32b limit (zero)"""
    await setup_dut(dut)

    dut.decrement.value = 1
    await ClockCycles(dut.clk, 8)
    dut.decrement.value = 0

    await FallingEdge(dut.clk)
    actual = int(dut.result.value)
    assert actual == 0xFFFFFFFF, (
        f"Rollunder Failed: Expected 0xFFFFFFFF, got {hex(actual)}"
    )


@cocotb.test()
async def test_branch(dut):
    """Simulate the PC executing sequentially, then jumping to a branch target."""
    await setup_dut(dut)

    pc = random.randint(0x00000000, 0x0000FFFF)
    dut.load_en.value = 1
    dut.load_data.value = pc
    await ClockCycles(dut.clk, 8)

    # 1. Sequential execution
    dut.load_en.value = 0
    dut.increment.value = 1
    for _ in range(15):
        await ClockCycles(dut.clk, 8)
        pc += 1

    await FallingEdge(dut.clk)
    actual = int(dut.result.value)
    assert actual == pc, (
        f"Sequential fetch failed: Expected {hex(pc)}, got {hex(actual)}"
    )

    # 2. CPU evaluates a branch and overwrites the PC
    dut.increment.value = 0
    branch_target = random.randint(0x40000000, 0x80000000)
    dut.load_en.value = 1
    dut.load_data.value = branch_target
    await ClockCycles(dut.clk, 8)

    await FallingEdge(dut.clk)
    pc = branch_target
    actual = int(dut.result.value)
    assert actual == pc, (
        f"Branch control transfer failed: Expected {hex(pc)}, got {hex(actual)}"
    )

    # 3. Resume sequential execution at the new branch target
    dut.load_en.value = 0
    dut.increment.value = 1
    for _ in range(5):
        await ClockCycles(dut.clk, 8)
        pc += 1

    await FallingEdge(dut.clk)
    actual = int(dut.result.value)
    assert actual == pc, (
        f"Execution after branch failed: Expected {hex(pc)}, got {hex(actual)}"
    )
