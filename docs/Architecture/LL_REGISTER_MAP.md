# Link Layer AXI-lite register map

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

## Purpose

Upstream does not document the register map. This table was reconstructed from
`verilog/btle_ll.v` (the `assign … = slv_regN` statements around lines 325–384,
the `ll_s_axi` write decoder and the read multiplexer around line 2120) and
checked against the accesses in `firmware/btle_ll.c`. None of it has been
checked in simulation yet.

## Access model

- The window is 256 bytes: 64 registers of 32 bits. The byte offset is the register index × 4.
- **Registers 0–39 are read/write.** They are stored in `ll_s_axi`, and reading one returns the value last written.
- **Registers 40–63 are read-only.** Hardware drives them, and writes are ignored, except for register 40 (see below).
- A register written from the AXI side reaches the 16 MHz baseband through
  `clk_cross_bus`. A multi-field write therefore takes effect a few cycles
  later, not at once.

## Read/write registers

| Reg | Offset | Bits | Field | Used by `btle_ll.c` |
|---|---|---|---|---|
| 0 | 0x00 | [15:0] | `reg_gpio`. Bit 15 resets the event counters and the RX RAM. All 16 bits are also exported as `ll_gpio`. | yes (bit 15; also writes `1` on error) |
| 1 | 0x04 | [15:0] tap value, [19:16] tap index | Gaussian filter tap write | no |
| 2 | 0x08 | [7:0] data, [26:16] address | TX COS table write | no |
| 3 | 0x0C | [7:0] data, [26:16] address | TX SIN table write | no |
| 4 | 0x10 | [7:0] | TX preamble | no |
| 5 | 0x14 | [31:0] | TX access address | no |
| 6 | 0x18 | [23:0] | TX CRC init | no |
| 7 | 0x1C | [5:0] | TX channel number | no |
| 8 | 0x20 | [7:0] data, [24:16] address | TX PDU octet memory write | no |
| 9 | 0x24 | [0] | `tx_start` | no |
| 10 | 0x28 | [31:0] | RX access address (unique bit sequence) | yes |
| 11 | 0x2C | [5:0] | RX channel number | yes |
| 12 | 0x30 | [23:0] | RX CRC init | yes |
| 13 | 0x34 | — | Intended as the RX PDU read address, but its `assign` is commented out (line 351), so nothing uses it | yes (writes 0) |
| 14–38 | 0x38–0x98 | — | Not connected to any logic | no |
| 39 | 0x9C | [2:0] | Crosses into `bb_clk` as `slv_reg39_bb`, but its only use is commented out (line 737) | yes (1 before a read, 0 after) |

## Read-only registers

| Reg | Offset | Content |
|---|---|---|
| 40 | 0xA0 | **RX PDU data port.** Each read returns the next word of the received PDU from `rx_ram`. A write resets the read address. |
| 41 | 0xA4 | `decode_end_to_host_read_counter`: time from decode end to the host read |
| 42–46 | 0xA8–0xB8 | No driver found (the timestamp `assign`s are commented out) |
| 47 | 0xBC | No driver found, yet bits [7:0] and [8] feed `data_frame` / `frame_en` of the UART TX. See the note below. |
| 48 | 0xC0 | [0] `tx_iq_valid_last`: TX packet finished |
| 49 | 0xC4 | [19] hit flag, [18] decode running, [17] decode end, [16] CRC OK (latched), [15:8] payload length (latched), [7:0] PDU octet |
| 50–55 | 0xC8–0xDC | Event counters 0–5 |
| 56–57 | 0xE0–0xE4 | 64-bit timestamp of the RX hit, latched at decode end (low word, high word) |
| 58 | 0xE8 | 1 PPS reference: toggle and count |
| 59 | 0xEC | Current write address of the IQ-capture BRAM |
| 60–61 | 0xF0–0xF4 | 64-bit free-running timestamp (low word, high word) |
| 62 | 0xF8 | [2:0] `ll_state`, the placeholder state machine |
| 63 | 0xFC | [16] `tx_done`, [9] UART frame error, [8] `rx_done`, [7:0] `rx_frame` |

## Notes for the thesis

- **The TX path can be driven entirely from registers 1–9.** No upstream
  software does this. The testbenches drive TX through the `ext_*` ports instead.
- **Register 47 looks like a real defect.** It is declared as an input to the
  AXI slave and feeds the UART transmitter, but nothing drives it. If
  simulation confirms this, the UART HCI TX path cannot be used from the
  register interface. This is recorded as an open item, not as a claim.
- **Any new controller needs this table as its contract.** Whether a RISC-V
  core talks to these registers, or replaces them with a leaner interface, is
  one of the decisions in
  [../Design Decisions/SCOPE.md](../Design%20Decisions/SCOPE.md).
