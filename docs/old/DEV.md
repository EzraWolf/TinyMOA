# TinyMOA Development Ecosystem

Lessons from IHP26a. Rules for every future tapeout.

## Repo Structure

Two repos per design. One for development, one per shuttle target.

The contdev repo (TinyMOA) holds all RTL, tests, and docs. It has no PDK dependency, no TinyTapeout tooling, no shuttle-specific config. It targets Icarus for simulation, Verilator for lint, and the Alchitry Cu V2 for FPGA validation. This repo never knows about IHP, Sky130, or GF.

The contdev repo must be clone-and-go. `uv sync` installs Python deps. Icarus and Verilator are the only system dependencies. A `tinymoa.py` script at the repo root is the single entry point for all project commands. Running `pre-commit install` after clone activates git hooks. These are the only setup steps beyond `uv sync`.

The target repo (e.g. TinyMOA-IHP25a) is a thin wrapper. It contains project.v, info.yaml, config.json, pdn_cfg.tcl, and the macro directory. The contdev repo is linked as a git submodule pinned to a tested tag. TT tools, LibreLane, and PDK references live here. One target repo per shuttle attempt. They are cheap to create and disposable.

Never modify the submodule from the target repo. All RTL development happens in contdev.

## tinymoa.py CLI

Single entry point for the entire project. Python script at the repo root. All commands are `./tinymoa.py <command> [args]`.

### Verification

`lint` -- Runs Verilator (`-Wall`) and iverilog elaboration on all src/ files. Fast sanity check that everything compiles and has no structural warnings. Under 5 seconds.

`test` -- Runs the full cocotb test suite via pytest. All unit tests and system integration tests. Greps output for "non-0/1" to flag X/Z propagation even if tests technically pass.

`test <module>` -- Runs tests for a specific module only. For example `test dcim` runs DCIM unit tests, `test system` runs pin-level integration tests. Maps to the pytest test ID.

`check` -- Runs all pre-commit hooks manually without committing. Useful for a quick "am I clean?" check before a big change.

### Synthesis and Area

`synth` -- Runs Yosys synthesis (no place-and-route) on the full design. Reports total cell count, area estimate, and per-module breakdown. Checks the log for "latch inferred" and "combinational loop" warnings and prints them prominently. Useful for quick "does this fit?" checks without a 25-minute harden cycle.

`synth <module>` -- Same as above but for a single module. Useful for comparing area before and after a change to one block.

### FPGA

`fpga build` -- Runs yosys + nextpnr targeting the Alchitry Cu V2 (ICE40 HX8K). Uses a pre-configured constraints file in fpga/. Reports LUT utilization and Fmax. The FPGA build substitutes block RAM for the SRAM macro via ifdef.

`fpga flash` -- Programs the Alchitry Cu V2 with the last built bitstream. Requires iceprog.

`fpga test` -- Runs the pin-level IO test suite against the FPGA over USB/UART. Same test vectors as cocotb system tests, but exercising real hardware. Requires the board to be connected.

### Target Repo Sync

`sync` -- Parses project.v in the target repo to find which modules are instantiated (walking the hierarchy from the top module). Collects the .v source files needed for each module. Updates info.yaml source_files list and the test Makefile VERILOG_SOURCES to match. Also runs iverilog elaboration as a check. This means you never manually maintain the source file list: add a module instantiation in project.v, run sync, and the build files update themselves.

This solves the IHP26a problem where the Makefile was missing tcm.v in the GL block, and where info.yaml source_files had to be manually kept in sync with actual instantiations.

### Hardening

`harden` -- Runs LibreLane on the full top-level design using the target repo's config.json. Equivalent to what TT's GH Actions do, but local. Requires LibreLane and a PDK to be installed (target repo concern, not contdev).

`harden <module>` -- Hardens a single module as a standalone macro. This is an interactive command that walks you through the process:

1. Which PDK? (ihp-sg13g2, sky130, gf180)
2. What is the target area? (enter dimensions, or "auto" to let the tool decide)
3. Save as macro? If yes, copies GDS/LEF/LIB into macro/<module>/ and prints the dimensions from the LEF so you can set placement coordinates in the target repo's config.json. If no, runs harden in a temp directory, reports area and timing, then cleans up. Useful for "how big is this block?" without polluting the repo.
4. If saving as macro: the original .v file stays in src/ for contdev simulation. The target repo references the hardened macro instead of synthesizing the module from RTL. This is exactly how the SRAM macro works -- the behavioral .v is for simulation, the GDS/LEF/LIB is for hardening.

### Utilities

`tree` -- Prints the module hierarchy starting from tinymoa_top. Shows which modules instantiate which, with file paths. Quick reference for "where does this live?" questions.

`map` -- Prints the memory map extracted from RTL reset values. Shows base addresses, region sizes, and which port accesses what. Single source of truth check: if RTL and test constants diverge, this command flags it.

`doctor` -- Checks that all dependencies are installed and working: iverilog, verilator, yosys, ruff, cocotb, numpy. Reports versions. Useful after cloning on a new machine to see what's missing before running anything.

## Sim/Silicon Divergence

Every bug we hit during IHP26a traced back to simulation not matching real hardware.

**Behavioral models must match real timing.** If the SRAM macro has registered outputs, the behavioral model has registered outputs. The unit test TB has registered outputs. No combinational shortcuts, ever. This was the root cause of the DCIM pipeline bug: the unit test TB used a combinational memory read, so DCIM's pipeline looked correct. The real TCM has 1-cycle registered reads, and every weight row latched garbage. A pre-commit hook greps all TB files for `assign.*= mem\[` and flags combinational memory reads as errors.

**Explicit reset for every register.** Verilog regs start as X. Silicon powers up to random 0/1. Reset must bring everything to a known state. The pre-commit Verilator lint (`-Wall`) catches missing resets. No exceptions.

**Avoid clock gating.** `clk & ~halt` caused hold violations during IHP26a hardening. Use clock enables instead: `always @(posedge clk) if (!halt) begin ... end`. If gating is truly required, use ICG cells the synthesis tool understands and treat the gated domain as a separate clock domain.

**Every case statement has a default.** Missing default infers a latch. Synthesis proceeds silently. Silicon behaves unpredictably. The pre-commit Verilator lint catches this.

## Test Rules

Pin-level IO tests are the source of truth. They interact only through top-level pins (ui_in, uo_out, uio). If these tests pass, the chip works. If they fail, it does not. The test helpers (io_write_byte, io_read_byte, io_execute, io_read_debug) model exactly what an FPGA sees. Expected results are computed independently with numpy, never derived from RTL output.

Unit test TBs must match real interfaces. Registered SRAM reads, not combinational. Same latency as the macro. If unit tests pass but system tests fail, the TB is lying to you. Fix the TB, not the system test.

GL sim uses the same test vectors as pin-level tests. If RTL passes but GL fails, the problem is synthesis. The target repo Makefile is kept in sync by `./tinymoa.py sync` so it always includes the correct source files in the GL block.

## FSM Rules

Draw the state diagram before writing Verilog. Every state, every edge, every condition.

One concern per state. If a state does two things, split it into two states.

All pulse signals (mem_read, mem_write, out_ready) default to 0 at the top of the else block. This prevents "forgot to deassert" bugs that are invisible in simulation but cause double-writes or stuck enables in silicon.

Every case statement has a default that returns to a safe state (IDLE).

Count memory latency cycles. For registered SRAM: assert enable at cycle N, data is valid at cycle N+2 (one cycle for the enable to take effect via NBA, one cycle for the SRAM to register the read). Draw the timing diagram and put it in a comment above the state.

Self-clearing bits (like cfg_start) must document when they clear and which block clears them.

## Memory Rules

Document read latency per port. Example: "Port A: registered, data valid 1 cycle after a_en asserted. Port B: registered, data valid 1 cycle after b_en asserted."

Maintain a single source of truth for the memory map. Addresses are defined once. RTL reset values and Python test constants must match. The `./tinymoa.py map` command checks this. A pre-commit hook does the same check automatically and blocks the commit if they diverge.

Never read SRAM before writing. Contents are undefined after power-on. Tests always write known values before reading.

## Automations

Automations are split between pre-commit hooks (block bad commits locally) and CI workflows (block bad merges remotely). Both are non-negotiable.

**On every commit (pre-commit hooks, < 10 seconds total):**

`ruff-format`: runs `ruff format --check` on changed .py files.

`ruff-check`: runs `ruff check` on changed .py files.

`iverilog-elaborate`: compiles all src/*.v with `-DBEHAVIORAL -DCOCOTB_SIM`. Catches syntax errors, missing modules, port mismatches. Under 2 seconds.

`no-combinational-mem-reads`: greps test/**/*.v for `assign.*= mem\[`. Blocks commit if found. This would have prevented the DCIM pipeline bug.

`constant-consistency`: extracts memory map addresses from RTL reset values and Python test constants, diffs them. Blocks commit if they diverge. This would have prevented the stale address comment bug.

**On every push (CI, < 5 minutes):**

Full cocotb test suite: unit + system integration. CI log grepped for "non-0/1" to catch X/Z propagation. Any failure blocks merge.

**On every tag:**

Target repo runs local harden + GL sim. If either fails, the tag is not valid for submission.

## Hardening Lessons

Use local hardening for iteration. 25 min local vs 45 min CI.

Plan memory maps before writing RTL.

Harden sub-blocks as macros for deterministic placement when area is tight. Use `./tinymoa.py harden <module>` to produce GDS/LEF/LIB in `macro/<module>/`. Reference the macro in the target repo's config.json the same way the SRAM macro is referenced. You define placement; the tool stops guessing.

Tag every successful harden run.

## Tools

SymbiYosys: formal verification. Proves FSM properties mathematically. Would have caught the DCIM pipeline timing assumption instantly. Advanced tactic worth investing in for next tapeout.

Surfer: waveform viewer. Better than GTKWave on macOS.

Verilator: lint and coverage analysis. Shows which FSM transitions were never tested.

## Current Repo Cleanup TODOs

Ordered by priority. Guardrails first so they protect every subsequent change.

**Phase 1: Guardrails**
- [ ] Create tinymoa.py CLI with: lint, test, test <module>, synth, check, tree, map, doctor
- [ ] Create .pre-commit-config.yaml with hooks: ruff-format, ruff-check, iverilog-elaborate, no-combinational-mem-reads, constant-consistency
- [ ] Run `pre-commit install` and verify hooks fire on a test commit
- [ ] Add numpy to pyproject.toml dev deps (used by system tests)
- [ ] CLAUDE.md: add "behavioral models must use registered reads" rule
- [ ] CLAUDE.md: add "run tests after every RTL change" rule
- [ ] Create docs/TODO.md (CLAUDE.md references it but it does not exist)

**Phase 2: RTL fixes**
- [ ] dcim.v: decide 16x16 or 32x32, make parameters consistent (currently 32x32 with dual compressor, but unit tests run 16x16)
- [ ] tcm.v: confirm Port B uses registered reads, not the combinational debug hack
- [ ] tinymoa.v: replace clock gating with clock enable, or remove halt entirely
- [ ] Run `./tinymoa.py test` after each fix. Commit each fix separately.

**Phase 3: Test overhaul**
- [ ] test_system.py: remove sentinel pre-fill debug block
- [ ] test_system.py: remove try/except debug wrapper in result read loop
- [ ] test_system.py: remove RTL internal probe block (TCM mem, DCIM shift_acc, etc.)
- [ ] test_system.py: keep dcim_expected() helper and random dotprod test
- [ ] Plan all tests ground up from pin-level IO requirements
- [ ] Redo all tests ground up
- [ ] Run all tests. Every test green before tagging v1.1.

**Phase 4: IHP25a-CMOS5L target repo**
- [ ] Create TinyMOA-IHP25a-CMOS5L repo from IHP26a template
- [ ] Add TinyMOA as git submodule pinned to v1.1
- [ ] Copy project.v, pdn_cfg.tcl, macro/ from IHP26a
- [ ] Update info.yaml for 6x2 tiles and new top_module name
- [ ] Update config.json DIE_AREA for 6x2 (approx 1002 x 314)
- [ ] Remove SRAM macro since only 5 layer metal, adapt code for it
- [ ] Run `./tinymoa.py sync` to generate Makefile and info.yaml source lists
- [ ] Local harden to check fit
- [ ] If it does not fit: drop to 16x16 DCIM in contdev, re-tag, re-harden
- [ ] GL sim
- [ ] Submit
