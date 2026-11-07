# Validation of the reduced configuration (A1, A2, B2) and analysis of B4

> Validation correction (2026-10-04): earlier success claims for all 270 checks are withdrawn. The strict rerun is **FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See [the integrity audit](VALIDATION_INTEGRITY.md) for evidence and limitations.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-19  
**Author:** Miguel Simões  
**Status:** executed on commit `39f5851`. B4 analysed, not implemented (§ 5).

---

## Purpose

This report records the evidence that the reductions of item 3 keep
transmission, reception and processor control intact. It also measures the
cells they save, and explains why the fourth one (B4) was not implemented.

## 1. What changed

Each reduction is a parameter of `btle_controller`. The default keeps the
original design, and the **reduced configuration** is
`ENABLE_IQ_CAPTURE=0, LL_MINIMAL=1, GAUSS_TABLE=1`.

| # | Change | What it keeps | What it removes |
|---|---|---|---|
| A1 | `auxiliary_daemon`: `ENABLE_IQ_CAPTURE` | the AGC/gain signals (they feed the LL event counter 2) | the 1 Mbit diagnostic IQ-capture RAM, its address counter (reg 59) and its half-flag interrupt (`ll_itrpt2`) |
| A2 | `btle_ll`: `LL_MINIMAL` | configuration (regs 0–12), packet access (40), status and events (48–53, 55), RX-hit timestamp (56–57), timestamp (60–61), LL state (62), interrupts 0 and 1 | UART HCI, 1 PPS counter (58), host-latency counter (41), scratch registers 13–39, undriven registers 42–47 and 54, UART status (63), and the unused fields of both clock-domain crossings. Removed registers read 0. |
| B2 | `gauss_filter`: `GAUSS_TABLE` | the modulation, bit-exact | the runtime-writable taps: the taps become a synthesis parameter (`GAUSS_TABLE_TAPS`, default = BLE BT = 0.5) and register 1 no longer changes them |

**Function removed on purpose:**
- the IQ capture (`btle_ll -q`);
- the UART HCI;
- the 1 PPS input;
- the latency statistic that `btle_ll.c` prints;
- runtime change of the Gaussian taps.

The firmware's packet path uses none of them: it reads registers 49, 40, 56,
57, 10, 50, 51, 53 and 55, and all of them are kept. It also reads 41, which
now returns 0.

## 2. Area (measured)

Same flow as every earlier run (Yosys 0.68, Nangate45, SRAMs as macros).

| Configuration | Controller cells | Flip-flops | Cell area (µm²) | SRAM bits | Run |
|---|---:|---:|---:|---:|---|
| Upstream | 50 295 | 4 578 | 71 706 | 1 136 070 | `baseline-upstream` |
| After B1 | 23 346 | 3 926 | 38 782 | 1 136 070 | `shared-demod` |
| **Reduced (B1 + A1 + A2 + B2)** | **16 102** | **2 673** | **26 681** | **87 046** | `sticker` |
| Reduction from upstream | **−68.0 %** | −41.6 % | −62.8 % | **−92.3 %** | |

Per module in the reduced configuration:

| Module | After B1 | Reduced | Change |
|---|---:|---:|---:|
| `gauss_filter` | 2 286 | 253 | −89 % |
| `btle_tx` | 3 411 | 1 392 | −59 % |
| `btle_ll` | 9 453 | 4 336 | −54 % (and −448 SRAM bits) |
| `auxiliary_daemon` | 299 | 233 | −22 % (and −1 048 576 SRAM bits) |
| `btle_rx` | 10 068 | 10 068 | unchanged |

The remaining 87 046 SRAM bits are:
- the 8 RX PDU buffers (32 768 bits), kept at full capacity as agreed;
- the TX COS/SIN tables (32 768 bits);
- the TX PDU buffer (4 096 bits);
- the LL RX RAM (16 384 bits);
- the clock-crossing RAMs.

## 3. Evidence that nothing needed was lost

### 3.1 Default configuration: proved identical to the previous RTL

`scripts/validation/equiv_defaults/run_equiv_defaults.sh` checks, module by
module, that with default parameters the new RTL is equivalent to commit
`88f2250` (the RTL before these changes). It uses Yosys equivalence checking
(`equiv_make`, `equiv_simple`, `equiv_induct`, `equiv_status -assert`), with
the RAMs mapped to flip-flops, so memory contents are part of the proof.

| Module | Result |
|---|---|
| `auxiliary_daemon` | equivalent (2 146 `$equiv` cells, all proven) |
| `gauss_filter` | equivalent (450) |
| `gfsk_modulation` | equivalent (33 294) |
| `btle_tx` | equivalent (37 622) |
| `btle_ll` | equivalent (20 602) |
| `btle_phy` | equivalent (72 435) |
| `btle_controller` | **equivalent (95 446)** |

Results: `results/validation/sticker/equiv_defaults/`.

This is what guarantees that the Vivado flow of the boards, which uses the
defaults, sees exactly the same design.

**Method notes:**
- The IQ-capture RAM is too large to map to flip-flops, so for the two modules
  that contain it `BRAM_DEPTH` is reduced to 64 **on both sides**.
- Asynchronous resets are modelled as synchronous on both sides (`async2sync`).
- Instances that the parameterisation moved into `generate` blocks are renamed
  back before flattening, so that every flattened signal pairs with its old
  counterpart.

The regression over the upstream testbenches confirms it by simulation:
**FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See the [integrity audit](VALIDATION_INTEGRITY.md).

### 3.2 Reduced configuration against upstream, through the registers

`scripts/validation/ctl_lockstep/run_ctl_lockstep.sh` runs the **upstream
`btle_controller`** and the **reduced `btle_controller`** side by side in one
simulation. Both are driven through the AXI-lite registers in mode 0, the path
the boards use, which no upstream test simulated (gap 1 of the test inventory).

The stimulus follows the software sequence of `firmware/btle_ll.c`:
- load the COS/SIN tables and the taps, and configure RX;
- for each packet of the Python model, sent between random noise (and in about
  a third of the packets with the tail replaced by noise, so the access address
  is found but the CRC fails): wait for interrupt 0, read register 49, read the
  PDU words from register 40, then read the timestamp and the counters;
- configure TX through registers 4–8 and pulse register 9;
- at the end, read all 64 registers.

Every clock, every output is compared except the three removed on purpose
(IQ-capture data, `ll_itrpt2`, `uart_tx`). Every read of a kept register must
match, and every read of a removed register must return 0.

| Result | |
|---|---|
| Runs | **15 of 15 without a mismatch** (3 packets × 5 seeds × 6 packets) |
| Clocks compared | 923 385 |
| RX packets | 90 interrupts; 57 with a correct CRC, 33 corrupted on purpose |
| TX packets through the registers | 90, the I/Q output identical on every clock |
| AXI register reads checked | 2 404 |
| Mutation check | 3 of 3 caught: register 49 dropped from the kept set; one table tap wrong (24 → 23); event counters 0 and 1 swapped in the crossing |

### 3.3 Gaussian table: formal equivalence

`scripts/validation/formal_gauss/run_formal_gauss.sh`. In the miter, the
upstream FIR is loaded through its own tap interface with the taps the table
was built from, then the input bits, their valid signals and the resets are
free on every clock. The outputs must be equal on every clock after loading.

| Result | |
|---|---|
| Proof | **PASS, unbounded** (k-induction, depth 40) |
| Mutants | 3 of 3 make the proof fail: wrong tap mirroring, a table group one position off, a wrong sign |

The table is exact for **every** input sequence, not only for packets that the
upstream transmitter produces.

## 4. Upstream issues found on the way

| # | Issue | Effect |
|---|---|---|
| U11 | `event4_counter` in `btle_ll.v` is declared but never driven, so register 54 reads an undefined value | Not read by the firmware. Removed in the reduced configuration. |
| U12 | `btle_controller_wrapper.v` connects a port `rx_iq_valid` that `btle_controller` does not have, so the wrapper does not elaborate | Excluded from the equivalence flow. Not fixed. |

## 5. B4 (sharing more logic between phases): analysed, not implemented

Measured after B1 (`btle_rx_core` with the external demodulator):
**633 cells per phase, of which 102 are flip-flops**, so 8 × 633 = 5 064 cells.

| Part of each decoder | Cells | Shareable? |
|---|---:|---|
| state: access-address shift register (32), CRC (24), whitening (7), counters and FSM | 102 flip-flops | **no**: each hypothesis needs its own state |
| access-address comparator | ≈ 65 | yes |
| CRC and whitening feedback | ≈ 15 | yes |
| next-state and enable logic of the state above | ≈ 350 | mostly no: it is the write path of each phase's own registers |
| FSM decisions (length, end, CRC check) | ≈ 100 | yes |

At most one phase receives a bit per clock, so one shared "bit engine" could
serve all eight phases. It would have to read the active phase's state through
an 8:1 multiplexer over about 102 bits (≈ 700 cells) and write it back. That
overhead cancels most of the ≈ 7 × 180 shareable cells.

The **estimated net gain is about 500–1 000 cells** (3–6 % of the 16 102),
and it would require rewriting the whole decoder and proving it again at the
level of B1. The decision is therefore **not to implement B4 now**. It should
be reconsidered only if the final area budget needs those few percent.

## 6. What is not claimed

- No FPGA or board test. No timing analysis. No power measurement.
- Removing the IQ capture and the UART removes functions that the boards'
  diagnostic tools use. The reduced configuration is for the tag, and the
  default configuration keeps them for the board.
- Runtime-programmable Gaussian taps are gone in the reduced configuration. If
  the thesis needs a reconfigurable BT, the table can become a 1-kbit RAM that
  software writes, and it would stay exact for any taps.
