# Upstream architecture

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

## Purpose

This document describes the hardware and firmware inherited from upstream as
they are in the code, not as the upstream README describes them. Where the two
disagree, the code wins and the disagreement is listed in section 7. Nothing
here has been simulated or synthesised yet. Every statement comes from reading
the sources, and each one cites a file.

## 1. System view on the FPGA board

```
 AD9361 RF  ──8 MHz IQ──►  ┌──────────────────── Zynq PL ───────────────────┐
            ◄─8 MHz IQ───  │ btle_controller                                 │
                           │  ├─ clock_domain_conversion_iq   8 ↔ 16 MHz     │
                           │  ├─ btle_phy  (btle_rx + btle_tx)   16 MHz      │
                           │  ├─ btle_ll   (AXI-lite regs, RX RAM, counters) │
                           │  └─ auxiliary_daemon (AGC, IQ capture BRAM)     │
                           └───────────────┬────────────────────────────────┘
                                           │ AXI-lite + BRAM + IRQ
                           ┌───────────────▼────────────────────────────────┐
                           │ Zynq PS (ARM, Linux)                            │
                           │  firmware/btle_ll.c  (UIO, mmap, raw Ethernet)  │
                           └───────────────┬────────────────────────────────┘
                                           │ Ethernet, EtherType 0x88B5
                           ┌───────────────▼────────────────────────────────┐
                           │ Host PC: host/ble_fpga_ctl → Wireshark          │
                           └────────────────────────────────────────────────┘
```

Upstream sums the chain up as "BTLE baseband (FPGA/PL) ↔ ARM (btle_ll) ↔ host PC
(ble_fpga_ctl, ble_send_cmd) → wireshark" (`fpga/README.md`).

## 2. RTL hierarchy

This hierarchy was extracted from the module instantiations in `verilog/`.

```
btle_controller                    verilog/btle_controller.v
├── clock_domain_conversion_iq     RF 8 MHz ↔ baseband 16 MHz, IQ samples
├── auxiliary_daemon               AGC and IQ capture into a 32768-word BRAM
│   └── sdpram_two_clk(_xilinx)
├── btle_ll                        verilog/btle_ll.v (2 800+ lines, several modules)
│   ├── ll_s_axi                   AXI-lite slave, 64 × 32-bit registers
│   ├── clk_cross_bus              register values from the AXI clock into the 16 MHz clock
│   ├── rx_ram, octet_to_word      received PDU buffer, read through register 40
│   ├── event_counter_*            packet/event counters
│   ├── uart_frame_rx/tx, tx/rx_clk_gen   UART HCI (from the separate files; see U1)
│   └── sdpram_one_clk, sdpram_two_clk
└── btle_phy                       verilog/btle_phy.v
    ├── btle_tx                    verilog/btle_tx.v
    │   ├── crc24 → crc24_core
    │   ├── scramble → scramble_core          (data whitening)
    │   ├── gfsk_modulation
    │   │   ├── bit_repeat_upsample           8 samples per symbol
    │   │   ├── gauss_filter                  17 taps, BT = 0.5 by default
    │   │   └── vco → sdpram_one_clk          COS/SIN look-up table
    │   └── sdpram_two_clk
    └── btle_rx                    verilog/btle_rx.v
        ├── btle_rx_core
        │   ├── gfsk_demodulation             sign(i0·q1 − i1·q0)
        │   ├── search_unique_bit_sequence    access-address detection
        │   ├── scramble_core                 de-whitening
        │   └── crc24_core
        └── serial_in_ram_out → sdpram_two_clk
```

## 3. Parameters that matter

These are the defaults of `btle_controller` (`verilog/btle_controller.v`, lines 15–45).

| Parameter | Default | Meaning |
|---|---|---|
| `SAMPLE_PER_SYMBOL` | 8 | 8× oversampling at 1 Mb/s → 8 MS/s baseband |
| `NUM_TAP_GAUSS_FILTER` | 17 | Gaussian filter length; taps writable at runtime |
| `SIN_COS_ADDR_BIT_WIDTH` | 11 | VCO table depth (2048 entries); writable at runtime |
| `IQ_BIT_WIDTH` | 8 | TX IQ width |
| `GFSK_DEMODULATION_BIT_WIDTH` | 16 | RX demodulator width |
| `LEN_UNIQUE_BIT_SEQUENCE` | 32 | Access address length |
| `CRC_STATE_BIT_WIDTH` | 24 | CRC-24 |
| `NUM_BIT_PAYLOAD_LENGTH` | 8 | PDU length field |
| `BRAM_DEPTH` | 32768 | IQ capture buffer depth |
| `C_S00_AXI_ADDR_WIDTH` | 8 | 256-byte AXI-lite window → 64 registers |

## 4. Clock domains

| Clock | Frequency | Used by | Source |
|---|---|---|---|
| `rf_clk` | 8 MHz | AD9361 IQ interface | `clock_domain_conversion_iq.v` header |
| `bb_clk` | 16 MHz | PHY and the baseband half of the LL | same; `btle_controller_wrapper.xdc` constrains `clk` at 62.5 ns |
| `s00_axi_aclk` | Set by the Zynq block design | AXI-lite registers | `btle_ll.v`, `ll_s_axi` |

Register values cross from the AXI clock into `bb_clk` through `clk_cross_bus`
(`btle_ll.v`, around lines 590–650). Status and counters come back the same way.

## 5. Who controls the PHY

`btle_controller` has an input `baremetal_phy_intf_mode`, which selects who
drives the PHY configuration (`btle_controller.v`, line 240 onwards):

- **`1`**: the `ext_*` ports drive the PHY directly. The testbenches use this mode.
- **`0`**: `btle_ll` drives the PHY from its AXI-lite registers.

On the boards the input is tied to ground (`fpga/antsdr/src/system.bd`, net
`GND_1_dout`), so **the LL registers control the PHY**. The RTL comment on
line 111, "currently 1 for external access", is out of date.

The `ext_*` port set is already a complete, cycle-level PHY interface:
configuration, TX PDU memory, `tx_start`, and RX hit/decode/CRC flags with PDU
memory. For the thesis this matters, because a new controller can connect
there without going through the AXI register file.

## 6. What the Link Layer actually does

This is the most important finding of the inventory.

**In hardware (`btle_ll.v`)** the "LL state machine" (lines 386–421) moves
STANDBY → ADVERTISING → INITIATING → CONNECTION → ISOCHRONOUS_BROADCASTING →
SCANNING → SYNCHRONIZATION → STANDBY, one step every time a packet finishes
transmitting (`tx_iq_valid_last`). It reacts to no received packet, runs no
timer and makes no protocol decision. It is a placeholder. The real work of
`btle_ll.v` is register plumbing: the AXI-lite slave, the clock crossing, the
RX PDU RAM, the event counters and the timestamps.

**In software (`firmware/btle_ll.c`)** a Linux user-space process on the ARM:

1. maps the register window through `/dev/uio*` (`mmap`) and pins itself to a
   CPU with real-time priority;
2. writes only the **RX** configuration: access address (reg 10), channel
   (reg 11), CRC init (reg 12) and PDU read address (reg 13);
3. waits for the RX interrupt (`poll` on the UIO file descriptor), reads the
   decoded PDU word by word through reg 40, and checks the interrupt count
   against the hardware counters to detect lost packets;
4. forwards each packet to the host over raw Ethernet (EtherType 0x88B5) and, in
   a child process, receives channel, CRC and access-address changes from
   `ble_send_cmd`;
5. with `-q <ms>`, captures raw IQ from the BRAM to a file.

It never writes a TX register (1–9) and never starts a transmission.

**Consequence:** the FPGA system is a **receive-only sniffer**. It has no active
Link Layer: no advertising schedule, no scan response, no connection events, no
channel hopping, and no T_IFS (150 µs) response deadline anywhere. The TX path
is exercised only by the testbenches and by the Python model.

For the thesis, this means a RISC-V Link Layer would have to be **built**, not
migrated from hardware to software. See
[../Design Decisions/SCOPE.md](../Design%20Decisions/SCOPE.md).

## 7. Known upstream issues found while reading

None of these has been fixed. They are recorded so that they are not
rediscovered later, and so that fixing any of them becomes a deliberate change
that goes in `CHANGES.md`.

| # | Issue | Where | Effect |
|---|---|---|---|
| U1 | *Corrected 2026-09-18.* `btle_ll.v` holds second copies of `uart_frame_rx`, `uart_frame_tx`, `tx_clk_gen` and `rx_clk_gen`, which differ from the separate files only in whitespace and comments. They sit inside `` `ifdef AVOID_DUPLICATION ``, which nothing defines, so they are never compiled. The first version of this table said the modules were defined twice. That was wrong. | `btle_ll.v` lines 2218–2783 | Dead code only. The separate files are the definitions that actually get compiled. |
| U2 | The top-level Icarus command in the chip write-up lists `dpram.v`, which no longer exists, and leaves out `auxiliary_daemon.v` and `clock_domain_conversion_iq.v`. | `open_btle_baseband_chip/open_btle_baseband_chip.md`, around line 347 | The documented `btle_controller_tb` command does not run as written. |
| U3 | The command in the header of `btle_controller.v` refers to `./btle_ll/hw/fpga/btle_ll_stub.v`, which is not in the repository. | `btle_controller.v` line 5 | Same as U2. |
| U4 | The comment on `baremetal_phy_intf_mode` does not match the boards. | `btle_controller.v` line 111 | Misleading; see section 5. |
| U5 | The LL state machine is a placeholder (section 6), although the header comment says it "implements the link layer minimum state machine according to the core spec". | `btle_ll.v` lines 5–8, 386–421 | Overstates what the LL does. |
| U6 | The firmware writes register 39 around each PDU read, but no RTL consumer of `slv_reg39` was found; its only use is commented out. | `btle_ll.v` line 737; `btle_ll.c` lines 836, 886 | Probably dead; not confirmed in simulation. |
| U7 | The OpenLane2 results are partial: post-PnR STA fails for `btle_rx_core`, and global routing fails for the full design. | `open_btle_baseband_chip/README.md`, sections "GDSII" and "Detailed Placement" | There is no signed-off area or timing number for the whole baseband to compare against. |
| U8 | Register 47 feeds the UART TX `data_frame`/`frame_en`, but nothing drives it. Registers 42–46 are undriven too, and register 13 has no consumer. | `btle_ll.v` lines 351–354, 941–946 | The UART HCI TX path probably cannot be used from the register interface. To be confirmed in simulation. |

The full register table, with these gaps marked, is in
[LL_REGISTER_MAP.md](LL_REGISTER_MAP.md).
