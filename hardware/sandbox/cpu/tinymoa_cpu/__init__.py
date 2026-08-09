"""TinyMOA e-core cycle-accurate sandbox (phase CPU #1)."""

from tinymoa_cpu.cpu import Core, RunResult
from tinymoa_cpu.programs import FIBONACCI, FIB_HALT_PC, FIB_RESULT, FIB_RESULT_ADDR

__all__ = [
    "Core",
    "RunResult",
    "FIBONACCI",
    "FIB_HALT_PC",
    "FIB_RESULT",
    "FIB_RESULT_ADDR",
]
