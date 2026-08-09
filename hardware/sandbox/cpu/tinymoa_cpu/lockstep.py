"""Retire-stream helpers (RVFI-lite on o_valid/o_pc + RF write)."""

from __future__ import annotations

from tinymoa_cpu.top import RetireEvent


def compare_retires(
    got: list[RetireEvent],
    exp: list[RetireEvent],
    *,
    check_values: bool = True,
) -> None:
    if len(got) != len(exp):
        raise AssertionError(f"retire count {len(got)} != {len(exp)}")
    for i, (g, e) in enumerate(zip(got, exp)):
        if g.pc != e.pc:
            raise AssertionError(f"retire[{i}] pc {g.pc:#x} != {e.pc:#x}")
        if g.rd != e.rd:
            raise AssertionError(f"retire[{i}] rd {g.rd} != {e.rd}")
        if check_values and g.rd is not None and g.value != e.value:
            raise AssertionError(
                f"retire[{i}] x{g.rd} value {g.value:#x} != {e.value:#x}"
            )


def diff_cycle_samples(a_samples, b_samples, *, check_rf: bool = True) -> str | None:
    """Return a first-mismatch description, or None if equal on compared fields."""
    n = min(len(a_samples), len(b_samples))
    for i in range(n):
        a, b = a_samples[i], b_samples[i]
        for field in (
            "imem_valid",
            "imem_addr",
            "dmem_valid",
            "dmem_ren",
            "dmem_wen",
            "dmem_addr",
            "dmem_wdata",
            "dmem_wmask",
            "retire_valid",
            "retire_pc",
        ):
            if getattr(a, field) != getattr(b, field):
                return (
                    f"cycle {a.cycle} field {field}: "
                    f"sandbox={getattr(a, field)!r} dut={getattr(b, field)!r}"
                )
        if check_rf and a.rf != b.rf:
            for r in range(len(a.rf)):
                if a.rf[r] != b.rf[r]:
                    return f"cycle {a.cycle} rf x{r}: sandbox={a.rf[r]:#x} dut={b.rf[r]:#x}"
    if len(a_samples) != len(b_samples):
        return f"sample count sandbox={len(a_samples)} dut={len(b_samples)}"
    return None
