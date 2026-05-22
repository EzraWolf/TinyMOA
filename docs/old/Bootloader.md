# TinyMOA Boot Sequence

On full device reset, the CPU is held in reset (`cpu_nrst = 0`) while a boot FSM loads the TCM from QSPI flash. Once loading is complete, the CPU is released and begins executing from `PC = 0x000000`.

## Boot FSM

```
RESET -> LOAD (read flash word → write TCM Port A, repeat 512×) → DONE → release CPU
```

- Boot FSM ONLY ACCESSES PORT A. NEVER PORT B.
- No watchdog — if QSPI never responds, the CPU simply stays in reset.
- Boot copies flash starting at a fixed flash offset into TCM `0x000000–0x000FFF` (or partial, TBD).
- After `boot_done = 1`, Port A is handed to the CPU exclusively. Boot FSM never runs again unless a full device reset occurs.

## CPU Start

PC starts at `0x000000`. If a bootloader stub is needed (e.g., stack init, peripheral config before jumping to `main`), it occupies the first N words of TCM. Otherwise the application code begins directly at `0x000000`.

## Flash Image Layout

The flash image burned to QSPI must match the TCM layout defined in Architecture.md. The boot FSM reads sequentially — no addressing indirection.
