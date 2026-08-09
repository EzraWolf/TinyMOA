"""Locate Homebrew/PATH LLVM tools for encode gating and Spike ELF assembly."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

_HOMEBREW_LLVM = Path("/opt/homebrew/opt/llvm/bin")
_HOMEBREW_LLD = Path("/opt/homebrew/opt/lld/bin")


def _find(name: str, env: str, *extra: Path) -> str:
    for cand in (os.environ.get(env), shutil.which(name)):
        if cand and Path(cand).is_file():
            return cand
    for base in extra:
        p = base / name
        if p.is_file():
            return str(p)
    raise FileNotFoundError(
        f"{name} not found; install LLVM/lld (brew install llvm lld) or set {env}=/path/to/{name}"
    )


def find_llvm_mc() -> str:
    return _find("llvm-mc", "LLVM_MC", _HOMEBREW_LLVM)


def find_ld_lld() -> str:
    return _find("ld.lld", "LD_LLD", _HOMEBREW_LLD, _HOMEBREW_LLVM)


def find_llvm_objcopy() -> str:
    return _find("llvm-objcopy", "LLVM_OBJCOPY", _HOMEBREW_LLVM)
