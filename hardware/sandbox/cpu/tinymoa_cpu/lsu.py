"""LSU — port of hardware/rtl/ecore/ecore_lsu.veryl."""

from __future__ import annotations

from dataclasses import dataclass


def _sext(value: int, bits: int, width: int) -> int:
    value &= (1 << bits) - 1
    if value & (1 << (bits - 1)):
        value |= ~((1 << bits) - 1)
    return value & ((1 << width) - 1)


@dataclass(frozen=True)
class LsuResult:
    wdata: int
    wmask: int
    load_data: int
    error: bool
    bus_addr: int


def lsu(
    addr: int,
    store_data: int,
    funct3: int,
    is_load: bool,
    is_store: bool,
    rdata: int,
    width: int = 32,
) -> LsuResult:
    nbytes = width // 8
    addr_mask = (1 << width) - 1
    addr &= addr_mask
    store_data &= addr_mask
    rdata &= addr_mask

    byte_bits = (nbytes - 1).bit_length()  # clog2(WIDTH/8)
    byte_offset = addr & ((1 << byte_bits) - 1)
    bit_offset = byte_offset * 8
    shift_rdata = rdata >> bit_offset
    shift_wdata = (store_data << bit_offset) & addr_mask

    op_size = funct3 & 0b11
    if op_size == 0b00:
        store_mask = 0b1
        align_mask = 0b000
    elif op_size == 0b01:
        store_mask = 0b11
        align_mask = 0b001
    elif op_size == 0b10:
        store_mask = 0b1111
        align_mask = 0b011
    else:
        store_mask = (1 << nbytes) - 1
        align_mask = 0b111

    is_misalign = (addr & 0b111 & align_mask) != 0

    wdata = shift_wdata if is_store else 0
    wmask = 0
    load_data = 0
    error = False

    if is_store:
        if funct3 == 0b000:  # SB
            wmask = (store_mask << byte_offset) & ((1 << nbytes) - 1)
        elif funct3 == 0b001:  # SH
            wmask = (store_mask << byte_offset) & ((1 << nbytes) - 1)
            error = is_misalign
        elif funct3 == 0b010:  # SW
            wmask = (store_mask << byte_offset) & ((1 << nbytes) - 1)
            error = is_misalign
        elif funct3 == 0b011:  # SD
            if width >= 64:
                wmask = (store_mask << byte_offset) & ((1 << nbytes) - 1)
                error = is_misalign
            else:
                error = True
        else:
            error = True

    if is_load:
        if funct3 == 0b010:  # LW
            load_data = _sext(shift_rdata & 0xFFFFFFFF, 32, width)
            error = is_misalign
        elif funct3 == 0b000:  # LB
            load_data = _sext(shift_rdata & 0xFF, 8, width)
        elif funct3 == 0b100:  # LBU
            load_data = shift_rdata & 0xFF
        elif funct3 == 0b001:  # LH
            load_data = _sext(shift_rdata & 0xFFFF, 16, width)
            error = is_misalign
        elif funct3 == 0b101:  # LHU
            load_data = shift_rdata & 0xFFFF
            error = is_misalign
        elif funct3 == 0b011:  # LD
            if width >= 64:
                load_data = rdata
                error = is_misalign
            else:
                error = True
        elif funct3 == 0b110:  # LWU
            if width >= 64:
                load_data = shift_rdata & 0xFFFFFFFF
                error = is_misalign
            else:
                error = True
        else:
            error = True

    if error:
        wmask = 0
        load_data = 0

    bus_addr = addr & ~((1 << byte_bits) - 1)
    return LsuResult(wdata=wdata, wmask=wmask, load_data=load_data, error=error, bus_addr=bus_addr)


def apply_store(dmem: dict[int, int], bus_addr: int, wdata: int, wmask: int, width: int = 32) -> None:
    """Merge store lanes into a word-addressed dict (WIDTH==32 words)."""
    nbytes = width // 8
    # Model dmem as WIDTH-bit words keyed by aligned bus_addr
    word = dmem.get(bus_addr, 0)
    for i in range(nbytes):
        if wmask & (1 << i):
            word &= ~(0xFF << (i * 8))
            word |= ((wdata >> (i * 8)) & 0xFF) << (i * 8)
    dmem[bus_addr] = word & ((1 << width) - 1)
