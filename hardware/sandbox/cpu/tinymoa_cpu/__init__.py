"""TinyMOA e-core cycle-accurate sandbox (phase CPU #1)."""

from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    run_fibonacci,
)
from tinymoa_cpu.top import Core, RunResult

__all__ = [
    "Core",
    "RunResult",
    "FIBONACCI",
    "FIB_HALT_PC",
    "FIB_RESULT",
    "FIB_RESULT_ADDR",
    "run_fibonacci",
]
