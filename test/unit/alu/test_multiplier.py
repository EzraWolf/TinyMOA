"""Test suite for tinymoa_multiplier."""

import cocotb
import numpy as np
from numpy import random
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles


async def setup_multiplier(dut):
    """Initialize multiplier with clock and reset."""
    clock = Clock(dut.clk, 4, unit="ns")
    cocotb.start_soon(clock.start())

    dut.nrst.value = 0
    dut.a_in.value = 0
    dut.b_in.value = 0
    await ClockCycles(dut.clk, 1)
    dut.nrst.value = 1

    return dut


@cocotb.test()
async def test_multiplication(dut):
    await setup_multiplier(dut)

    a = random.randint(0, 0xFFFF)
    b = random.randint(0, 0xFFFF)
    dut.a_in.value = a
    dut.b_in.value = b
    await ClockCycles(dut.clk, 1)

    for _ in range(100):
        await ClockCycles(dut.clk, 7)
        expected = a * b

        # Load next values
        a = random.randint(0, 0xFFFF)
        b = random.randint(0, 0xFFFF)
        dut.a_in.value = a
        dut.b_in.value = b
        await ClockCycles(dut.clk, 1)

        result = int(dut.result.value)
        assert result == expected, f"Expected 0x{expected:X}, got 0x{result:X}"


@cocotb.test()
async def test_zero_multiplication(dut):
    """Test that 0 * anything = 0."""
    await setup_multiplier(dut)

    for _ in range(50):
        b = random.randint(0, 0xFFFF)
        dut.a_in.value = 0
        dut.b_in.value = b
        await ClockCycles(dut.clk, 8)
        result = int(dut.result.value)
        assert result == 0, f"0 * {b}: got {result:X}, expected 0"

    for _ in range(50):
        a = random.randint(0, 0xFFFF)
        dut.a_in.value = a
        dut.b_in.value = 0
        await ClockCycles(dut.clk, 8)
        result = int(dut.result.value)
        assert result == 0, f"{a} * 0: got {result:X}, expected 0"


@cocotb.test()
async def test_one_multiplication(dut):
    """Test multiplication by 1."""
    await setup_multiplier(dut)

    for _ in range(50):
        b = random.randint(0, 0xFFFF)
        dut.a_in.value = 1
        dut.b_in.value = b
        await ClockCycles(dut.clk, 8)
        result = int(dut.result.value)
        assert result == b, f"1 * {b}: got {result:X}, expected {b:X}"

    for _ in range(50):
        a = random.randint(0, 0xFFFF)
        dut.a_in.value = a
        dut.b_in.value = 1
        await ClockCycles(dut.clk, 8)
        result = int(dut.result.value)
        assert result == a, f"{a} * 1: got {result:X}, expected {a:X}"


@cocotb.test()
async def test_matrix_vector_multiply(dut):
    """Test simple 2x2 8b matrix-vector multiplication."""
    await setup_multiplier(dut)

    # Because many of us forgot linear algebra.
    # Matrix: [[2, 3], [4, 5]]
    # Vector: [7, 11]
    # Result: [2*7 + 3*11, 4*7 + 5*11] = [47, 83]

    A = [
        [random.randint(0, 0xFF), random.randint(0, 0xFF)],
        [random.randint(0, 0xFF), random.randint(0, 0xFF)],
    ]

    B = [random.randint(0, 0xFF), random.randint(0, 0xFF)]

    result_vec = []
    for row in A:
        accumulator = 0
        for mat_val, vec_val in zip(row, B):
            dut.a_in.value = int(mat_val)
            dut.b_in.value = int(vec_val)
            await ClockCycles(dut.clk, 8)
            product = int(dut.result.value)
            accumulator += product
        result_vec.append(accumulator)

    expected = np.dot(A, B).tolist()
    assert result_vec == expected, f"MVM: got {result_vec}, expected {expected}"


@cocotb.test()
async def test_matrix_matrix_multiply(dut):
    """Test simple 4x4 matrix-matrix multiplication."""
    await setup_multiplier(dut)

    # Matrix A: [[1, 2], [3, 4]]
    # Matrix B: [[5, 6], [7, 8]]
    # Result C: [[1*5+2*7, 1*6+2*8], [3*5+4*7, 3*6+4*8]] = [[19, 22], [43, 50]]

    A = [[1, 2], [3, 4]]
    B = [[5, 6], [7, 8]]

    result = [[0, 0], [0, 0]]

    for i in range(2):
        for j in range(2):
            accumulator = 0
            for k in range(2):
                dut.a_in.value = A[i][k]
                dut.b_in.value = B[k][j]
                await ClockCycles(dut.clk, 8)
                product = int(dut.result.value)
                accumulator += product
            result[i][j] = accumulator

    expected = np.dot(A, B).tolist()
    assert result == expected, f"MMM: got {result}, expected {expected}"
