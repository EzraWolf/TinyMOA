# Makefile for register file unit tests

# Defaults
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Source files
VERILOG_SOURCES += $(PWD)/tb_registers.v
VERILOG_SOURCES += $(PWD)/../../../src/cpu/registers.v

# Testbench module
TOPLEVEL = tb_registers

# Python test module
MODULE = test_registers

# Include cocotb makefiles
include $(shell cocotb-config --makefiles)/Makefile.sim

# Clean targets
clean::
	rm -rf __pycache__ sim_build results.xml *.fst *.vcd
