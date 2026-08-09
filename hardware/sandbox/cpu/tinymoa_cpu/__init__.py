"""TinyMOA e-core cycle-accurate sandbox (phase CPU #1)."""

from tinymoa_cpu.mem import IdealMem, imem_from_words
from tinymoa_cpu.programs import (
    FIBONACCI,
    FIB_HALT_PC,
    FIB_RESULT,
    FIB_RESULT_ADDR,
    run_fibonacci,
)
from tinymoa_cpu.top import Core, CycleSample, RetireEvent, RunResult

__all__ = [
    "Core",
    "CycleSample",
    "IdealMem",
    "RetireEvent",
    "RunResult",
    "FIBONACCI",
    "FIB_HALT_PC",
    "FIB_RESULT",
    "FIB_RESULT_ADDR",
    "imem_from_words",
    "run_fibonacci",
]
