# A Legacy Advertising transmitter: header in registers, AdvA in ROM/OTP, AdvData in 32 × 8 (`ble-tx-min`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-min`, from `ble-tx-rom` (`66a7751`, after the lint closure)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-16  
**Author:** Miguel Simões  
**Status:** executed on commit `b723c06`, against `master` after the lint closure (`fca6ac6`): the
product audit's campaign (`PRODUCT_VALIDATION.md`), `tests/test_tx_min.py` and its mutants, the strict
lint; runs `tx-min` (area, static timing, switching activity of `master`, `ble-tx-rom` and the two
AdvData stores of this branch, one run; the activity with the harness fix `4657113`), `openram-min`
(the AdvData macro), the GF180MCU eFuse block (`results/otp/gf180-efuse/`) and `tx-min-gf180` (the
transmitter's layout with the OTP, signoff clean, `7f2306c`); figures in `results/figures/tx-min/`.
Pre-layout digital campaigns and measurements, plus one open-PDK layout of the transmitter (§ 7):
ASIC readiness is NOT READY, as on every branch (`ASIC_READINESS.md`).

---

## Purpose

On `ble-tx-rom` the transmitter's one macro is the packet buffer, 256 × 8 with one port plus a register
for byte 256 (6 979.1 µm², 74 % of the transmitter), sized for any PDU of up to 257 bytes. A transmitter
that only advertises with legacy PDUs never sends more than 39: the 2-byte header, AdvA (6 bytes) and at
most 31 bytes of AdvData. Of those, only AdvData changes from one advertising event to the next; the
header is two bytes of configuration, and AdvA is the device's address, fixed per chip. The thesis
supervisor's choice: AdvA in an OTP, programmed once per chip, modelled as a ROM in the RTL. This branch
builds that transmitter and measures how far it goes below `ble-tx-rom`.

## 1. What the branch contains

| Part | Files | How it is selected |
|---|---|---|
| Packet buffer `adv_pdu_buffer`: bytes 0–1 (header) in two registers; bytes 2–7 (AdvA) from `ADV_ADDRESS`, least significant byte first, pairs to them dropped; bytes 8–38 (AdvData) in a 32 × 8 one-port memory (word = byte[4:0]); pairs to bytes ≥ 39 dropped | `btle_tx.v` | structural, always on |
| AdvData in 31 bytes of flip-flops instead of the memory | `btle_tx.v` | `ADV_DATA_FLOPS = 1` (default 0) |
| AdvA from six eFuse blocks `efuse_async_mem_1x8` of the open GF180MCU eFuse compiler, read after reset, programmed through `adv_address_otp_prog` (tied off in `btle_phy`) | `btle_tx.v`, `btle_phy.v` | `ADV_ADDRESS_OTP = 1` (default 0: the ROM) |
| Counters for 39 bytes: PDU bit count 9 bits, byte address 6 bits, `payload_length` 6 bits saturated at 37 | `btle_tx.v` | structural |
| `ADV_ADDRESS` (default 01:02:03:04:05:06, the project's advertising example), `ADV_DATA_FLOPS`, `ADV_ADDRESS_OTP` passed down | `btle_phy.v`, `btle_controller.v` | parameters |
| Everything else: B2 paired, the ROM VCO, the exact counter rewrites | from `ble-tx-rom`, unchanged | `GAUSS_TABLE=1` |

The read protocol of `ble-tx-pdu` is kept as it is: the byte is asked at [clk_count] 116, a toggle and two
synchronizing flip-flops bring the request to `clkb`, and the byte is in `read_data` at most four `clkb`
clocks later, within the 12 `clk` clocks left. So there is no new stall and no new timing constraint; the
header, AdvA and the flip-flops answer in the clock that reads, the memory in the next one, as before.

**Contract.** A Legacy Advertising PDU of at most 39 bytes (payload length L ≤ 37), whose bytes 2..7 are
the chip's AdvA, written before `tx_start` (as `ble-tx-pdu`). Within it every output of the transmitter
is upstream's on every clock. ADV_IND, ADV_NONCONN_IND, ADV_SCAN_IND and SCAN_RSP start their payload
with AdvA; ADV_DIRECT_IND (AdvA + TargetA) also fits, with TargetA in the AdvData memory. **Outside the
contract**: a header length above 37 sends the header as written, 37 payload bytes and the CRC of what
was sent (376 PHY bits; a receiver that trusts the length rejects it), then returns to IDLE; a PDU whose
bytes 2..7 are not the chip's AdvA (a data-channel PDU, for example) is sent with the chip's AdvA there.

## 2. AdvA in an OTP: the GF180MCU eFuse compiler

Neither FreePDK45/Nangate45 nor OpenRAM has an OTP (`GAUSS_FILTER_OPTIONS.md` § 5). The open-source
GF180MCU eFuse compiler (github.com/egorxe/gf180_efuse_compiler, Apache-2.0, run in its Nix environment
— LibreLane, KLayout, Magic, Xyce — inside Docker, `results/otp/gf180-efuse/provenance.txt`) generates,
for the wafer.space GF180MCU-D PDK, an asynchronous 8-bit block with its sense amplifiers and output
latches, and a wrapper that senses the fuses once after reset:

```
./efuse.py 1 8 --async-efuse --digital-wrapper=async   ->  efuse_async_mem_1x8
```

| Check of the generated block | Result |
|---|---|
| KLayout DRC (GF180MCU deck) | clean |
| KLayout LVS | clean |
| Wrapper hardened with LibreLane | done (GDS, LEF, Liberty for 9 corners, SDF, netlists) |
| Xyce on the PEX netlist: 4 programming and 4 reading tests | all pass |

| Block | Size (LEF) | Area |
|---|---|---:|
| `efuse_array_async_1x8` (fuses, sense amplifiers, latches) | 42.27 × 53.02 µm | 2 241.2 µm² |
| `efuse_async_mem_1x8` (with the wrapper and its ring) | 97.27 × 83.02 µm | 8 075.4 µm² |
| **AdvA: six blocks** | — | **48 452 µm² (13 447 µm² of arrays)** in GF180MCU |

Programming: a 1 held for at least 50 µs on `prog[i]` blows fuse i (Xyce: about 17 mA through the fuse
while it blows), read as 1 from the next reset on (`results/figures/tx-min/efuse_xyce.png`). These areas
are **180 nm**, not comparable with the Nangate45/FreePDK45 figures of § 4, and eFuses do not shrink
like logic (the fuse is sized by its blowing current). In the 45 nm comparison AdvA is the ROM
(`ADV_ADDRESS`), which synthesis folds into the read multiplexer: its area is in the logic.

In the RTL the OTP option is `ADV_ADDRESS_OTP = 1`; `tests/efuse_async_mem_1x8_model.v` models the block
from its documented behaviour (sense after reset, Tprog = 50 µs, a short pulse leaves the fuse intact).
In the ASIC the programming port must reach a production test interface; this controller has none, so
`btle_phy` ties it off. The supervisor's flow — program each chip once, never at run time — is exactly
what the model checks (§ 3: the unprogrammed chip reads 0, AdvA is programmed once, the transmitter then
sends it).

## 3. Evidence

At commit `b723c06`, against `master` `fca6ac6`, in two clones (the RAM model; the one-port model of the
AdvData memory), with the product audit's input archive (`product-evidence-20261005/vectors.tar.gz`):

| Check | Result | Evidence (`results/validation/`) |
|---|---|---|
| Transmitter against `master`'s, every output on every clock (`tests/test_tx_min.py --mutants`): PDUs of 0–37 payload bytes (37 and 6 first) with the chip's AdvA, two AdvA values, 6 AXI clocks, four DUT builds (RAM model, one-port macro model, flip-flops, OTP programmed once), resets, writes while sending; then a header length of 38–255 on the DUT alone | **144/144 runs, no difference**; the overlong header gives 376 PHY bits and IDLE; **16/16 mutants** (read clock, AdvA byte, header byte 1, write in the reading clock, byte 38, flip-flop index, last bit, saturation, `payload_length`, `octet`, upsampling, CRC order, whitening, filter sum, OTP byte order, OTP never sensed) | `min-evidence-20261016/tx_min.log.gz` |
| The product audit's matrix, 270 cases (`run_rx_regression.sh`), each example on a DUT programmed with the AdvA of its packet (`REGRESSION_EXAMPLES`, example 1: 04500e0f0200), `GAUSS_TABLE=1` on **every** level | **270/270**, no DIFFERENT, ERROR, BOTH_FAIL or NO_STIMULUS | `min-matrix-ex{0,1,2}/` |
| The same on the one-port model of the AdvData memory | **270/270** | `min-matrix-one-port-ex{0,1,2}/` |
| TX waveforms against the Python model, every PDU decoded by the RTL receiver (`test_tx_packet.py --rtl-rx`, PDU bytes 2..7 = AdvA) | **167/167**; one-port 16/16 (`--quick`) | `min-tx-packets.json` |
| RF-valid contract (`test_clock_domain_contract.py --mutants`) | **12/12** scenarios, **2/2** mutants detected | `min-contract/` |
| Controller lockstep through the registers, one DUT per example programmed with its packet's AdvA | **6/6 runs**, 369 606 cycles compared, 36 TX and 36 RX completions; **5/5 mutations** | `min-controller/` |
| Product defects (`test_product_mutations.py`) | 2 baselines, **4/4** defects caught | `min-mutations/` |
| Strict lint (`run_lint.py`, Verilator 5.020 as the audit; `ADV_DATA_FLOPS` 0 and 1) | **PASS 4/4** configurations, 14 reviewed exceptions | `min-lint/` |
| Guards, measurement tools, RX model, Gaussian tail, upsampling, readback, suite | pass (suite: 34 tests, 2 skipped; 35 on `fe9faf4`, with the SAIF-name case of § 6) | `min-evidence-20261016/` |

Two runs failed first for reasons outside the RTL, both kept in `campaign.txt`: the lint ran with the
OSS CAD Suite's Verilator, which the audit does not use (rerun with 5.020: PASS), and the guard tests
need a local `master` branch in the clone. Example 1 of the matrix first ran with an AdvA derived by
hand from the wrong bytes (36 ERROR, kept as `*-wrong-adva`); with the AdvA of its packet it passes.

**A finding about the earlier campaigns.** `DUT_DEFAULTS='gauss_filter.v:GAUSS_TABLE=1'`, as the
matrices of `ble-tx-table`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-rom` and `ble-tx-cordic` applied it,
changes the default inside `gauss_filter.v` only; `gfsk_modulation`, `btle_tx`, `btle_phy` and
`btle_controller` pass their own `GAUSS_TABLE` (default 0) down, so in those matrices the testbenches ran
the runtime FIR, not B2 (checked: the elaborated `gauss_filter` instance has `GAUSS_TABLE = 0`). B2 itself
was covered by the module and controller locksteps and the formal proof, which set the parameter on the
instance. Here every level is set.

## 4. Area

Run `tx-min`: `scripts/area/run_area.sh` (Yosys + ABC, Nangate45), every configuration at its head
after the lint closure, in one run; the SRAMs as OpenRAM macros (FreePDK45, run `openram-min` for
32 × 8, `openram-pdu` for 256 × 8, `openram-tx` for `master`'s).

| | `btle_tx` cells | flip-flops | logic (µm²) | SRAM macros (µm²) | **Transmitter (µm²)** | vs `master` | vs `ble-tx-rom` |
|---|---:|---:|---:|---:|---:|---:|---:|
| `master` (`fca6ac6`) | 5 823 | 547 | 8 559.1 | 162 408.5 | **170 967.6** | — | — |
| `ble-tx-rom` | 1 463 | 236 | 2 520.6 | 6 979.1 (256 × 8) | **9 499.7** | −94.4 % | — |
| **`ble-tx-min`** (AdvData 32 × 8) | 1 470 | 239 | 2 531.3 | **2 475.8 (32 × 8)** | **5 007.1** | **−97.1 %** | **−47.3 %** |
| `ble-tx-min`, `ADV_DATA_FLOPS = 1` | 2 251 | 486 | 4 446.5 | — | **4 446.5** | −97.4 % | −53.2 % |

| `btle_controller` | cells | flip-flops | cell area (µm²) | SRAM bits |
|---|---:|---:|---:|---:|
| `master` | 52 357 | 4 722 | 74 684.8 | 1 136 070 |
| `ble-tx-rom` | 48 108 | 4 411 | 68 650.9 | 1 101 254 |
| `ble-tx-min` | 48 140 | 4 414 | 68 701.1 | 1 099 462 |
| `ble-tx-min`, flip-flops | 48 780 | 4 661 | 70 500.9 | 1 099 206 |

1. **The packet buffer goes from 6 979.1 to 2 475.8 µm²** (2 048 + 8 bits to 256 bits); the logic
   barely moves (+10.7 µm²: two header registers and the address decode, against `ble-tx-rom`'s byte-256
   register; the AdvA ROM folds into the read multiplexer). The transmitter is 5 007.1 µm²,
   −47.3 % against `ble-tx-rom`, the smallest with an SRAM.
2. **Without any macro it is smaller still**: 31 bytes of flip-flops cost 1 915 µm² of logic (248
   flip-flops, each with the multiplexer that Nangate45's lack of an enable flip-flop adds), less than
   the 32 × 8 macro, whose periphery (decoder, sense amplifiers, drivers) dominates at 256 bits (9.67 µm²
   per bit, against 6.12 for 64 × 8). The transmitter is then 4 446.5 µm², −53.2 % against
   `ble-tx-rom`. A 64 × 8 SRAM, the first idea, would be 3 135.5 µm² (5 666.8 in all).
3. Against the supervisor's architecture (header in registers, AdvA in OTP, AdvData in SRAM), the
   flip-flops change only where AdvData lives; both are built and validated (§ 3), the SRAM is the
   default. Which one is cheaper in power is § 6.

## 5. Timing

Run `tx-min`, `scripts/timing/run_sta.sh` at 62.5 ns against `master` `fca6ac6` (`master` itself 3.410
ns, its worst path in the Gaussian tail of the runtime FIR):

| | `ble-tx-rom` | `ble-tx-min` | `ble-tx-min`, flip-flops |
|---|---:|---:|---:|
| Logic path | 1.658 ns | 1.677 ns | 1.553 ns |
| **Min period** | 2.017 ns | **2.036 ns** | 1.913 ns |
| Slack at 62.5 ns / Fmax | +60.483 ns / 495.7 MHz | +60.464 ns / 491.1 MHz | +60.587 ns / 522.9 MHz |
| Worst path | demodulator multiply (RX) | demodulator multiply (RX) | demodulator multiply (RX) |

The worst path of all three is in the receiver, which this branch does not touch; the differences are
the flow's noise. The transmitter is not on the critical path, and the read protocol is unchanged: the
timing does not get worse, and there is no stall.

## 6. Switching activity

Run `tx-min`, `scripts/power/run_activity.sh` (the harness of `SWITCHING_ACTIVITY.md`): each
configuration's gate-level netlist (Nangate45) beside `master` `fca6ac6`'s in one Verilator simulation
per scenario, every output and register compared on every clock (`FULL_COMPARE`), on the vector set of
every earlier run (`results/compare/*/vectors.tar.gz`, `d53f2d49ed8db456`). Results in
`results/power/tx-min/<configuration>/`. The measure is the switched-capacitance proxy Σ toggles ×
liberty pin capacitance (data pins and flip-flop `CK` pins), setup subtracted, 100 000 `bb_clk` clocks:
no wires, no clock tree, no internal or macro energy, no leakage.

| Check | Result |
|---|---|
| Gate-level lockstep, 4 configurations × 5 scenarios | **0 mismatches**; `tx` 17 packets, `mixed` 8 packets and 202 AXI reads, `rx` 306 AXI reads |
| SAIF evidence (every loaded or driven net found) | **20/20 COMPLETE**, 0 missing nets |
| `master` against itself | +0.0 % in every scenario and measure (the harness's null) |

| Data + clock proxy against `master` | `rx` | `tx` | `mixed` | `idle` | `idle0` |
|---|---:|---:|---:|---:|---:|
| `master` (`fca6ac6`) | 1.258 × 10⁹ fF | 1.040 × 10⁹ fF | 1.302 × 10⁹ fF | 1.290 × 10⁹ fF | 0.975 × 10⁹ fF |
| `ble-tx-rom` | −4.70 % | −6.23 % | −4.75 % | −4.61 % | −6.08 % |
| **`ble-tx-min`** (AdvData 32 × 8) | **−4.73 %** | **−6.20 %** | **−4.79 %** | **−4.61 %** | **−6.04 %** |
| `ble-tx-min`, `ADV_DATA_FLOPS = 1` | −0.98 % | −1.74 % | −1.18 % | −0.94 % | −1.23 % |

| `btle_tx` except the Gaussian filter, scenario `mixed` | toggles / clock | data load × toggles | `CK` load × toggles | RAM-port toggles (whole design) |
|---|---:|---:|---:|---:|
| `master` | 48.1 | 1.46 × 10⁷ | 7.01 × 10⁷ | 3 165 890 |
| `ble-tx-rom` | 64.3 | 2.32 × 10⁷ | 4.07 × 10⁷ | 2 736 445 |
| `ble-tx-min` | 63.5 | 2.31 × 10⁷ | 4.12 × 10⁷ | 2 735 493 |
| `ble-tx-min`, flip-flops | 63.4 | 2.29 × 10⁷ | **8.81 × 10⁷** | 2 529 079 |

1. **`ble-tx-min` with its SRAM is `ble-tx-rom` in activity** (within 0.05 points in every scenario):
   the packet path reads the same bytes at the same clocks, and the header registers and AdvA ROM add
   three flip-flops' clock load (+1.4 % of the transmitter's `CK` load). The saving against `master`
   (−4.6 % to −6.2 %) is `ble-tx-rom`'s: B2 (the Gaussian filter, −68 % of its data load, −88 % of its
   clock load) and the ROM VCO.
2. **The flip-flops give back three quarters of it.** The 31 AdvData bytes are 248 flip-flops clocked
   on every `clkb` edge, written or not (no clock gating; Nangate45 has no enable flip-flop, so each
   holds its value through a multiplexer): the transmitter's `CK` load more than doubles (4.12 → 8.81 ×
   10⁷), in every scenario, idle ones included, and the design's saving falls from −4.8 % to −1.2 %.
3. **Against the SRAM's own energy, which the proxy does not hold**: the extra `CK` load is 4.69 × 10⁷
   fF·toggles in 6.25 ms, about 4.5 µW at 1.1 V (½CV²), pin capacitance only. The memory's side shows
   as 200 000 RAM-port toggles more per window in the idle scenarios (its clock, two edges per cycle);
   the OpenRAM 256 × 8 of `ble-tx-pdu` costs 5.17 µW of deselected clocks and 15.0 µW of leakage
   (`results/power/sram-energy/`, FreePDK45 SPICE); the 32 × 8 is not characterized. So **neither store
   wins clearly on power**: the flip-flops win on area (§ 4) and, written only between advertising
   events, would lose their clock cost with one clock gate on the 31 bytes; the SRAM keeps its leakage.

**A defect of the measurement harness, fixed here.** Every activity run against `master` `fca6ac6`
failed: the incomplete-evidence guard of the product audit (`c574a4c`) found 34 nets of `btle_ll` and
`btle_rx`, on both sides, that the netlist parser looked for under names the SAIF does not use (`ble-tx-rom`
has no activity in `BRANCH_COMPARISON.md`; this run is its first). Three
mismatches between the Yosys netlist and Verilator's SAIF (`saif_activity.py`, `4657113`): an escaped
name holding brackets (`\data_internal[0]`, a vector) taken as one bit; Verilator numbering a vector's
bits from 0 whatever its LSB (`octet_buf [31:8]` written `[0..23]`), which also gave, silently, bits
8..23 the activity of bits 16..31 in the runs before the guard; a `[0:0]` vector written without an
index. `tests/test_measurement_evidence.py` has a case for each (it fails on the old parser). The
earlier runs are not repeated: the mismatches sit in blocks no branch changes and on both sides alike.

## 7. Layout in an open PDK (GF180MCU) with the OTP

Run `tx-min-gf180`: `scripts/layout/tx_min_gf180/run.sh` (LibreLane Classic flow, GF180MCU-D,
`gf180mcu_fd_sc_mcu7t5v0`, in the eFuse compiler's Nix environment), `btle_tx` of `b723c06` with
`GAUSS_TABLE = 1`, `ADV_DATA_FLOPS = 1` and `ADV_ADDRESS_OTP = 1`: the transmitter with AdvA in the six
eFuse blocks of § 2 and AdvData in flip-flops (no SRAM compiler for this PDK in the flow). Die 760 ×
760 µm. Evidence in `results/layout/tx-min-gf180/` (metrics, signoff reports, the STA of every corner,
GDS and netlist, `provenance.txt`).

| Signoff check | Result |
|---|---|
| DRC: Magic, KLayout (GF180MCU decks) | **0**, **0** |
| LVS (Netgen) | **clean** (0 device, net or pin differences) |
| Antenna | **0** violating nets |
| Setup / hold, 9 corners (ss 125 °C 4.5 V, tt 25 °C 5 V, ff −40 °C 5.5 V × min/nom/max RC) | **met in all**: worst setup +6.388 ns (max_ss), worst hold +0.192 ns (ff) |
| Max slew / max capacitance, 9 corners | **0** / **0** |
| IR drop (VDD) | 0.25 mV average, 1.43 mV worst |
| Clock skew | 0.32 ns (two trees, `clk` and `clkb`) |

| Area (µm²) | |
|---|---:|
| Six eFuse blocks (AdvA) | 48 452.1 |
| Logic: combinational 39 276.5, flip-flops 31 894.1, inverters 1 009.8, buffers 149.3 | 72 329.7 |
| Timing-repair buffers / clock trees | 9 487.6 / 4 188.4 |
| Taps, end caps, antenna diodes (1 738) | 13 588.3, 1 861.5, 7 630.5 |
| **Placed cells + macros** | **157 538.1** (29.1 % of the core, 541 347) |

Clocks: `clk` 62.5 ns (16 MHz) and `clkb` 20 ns (50 MHz), asynchronous (`btle_tx.sdc`). The worst
path is `pdu_octet_mem_addr` → the address decoder → an AdvData flip-flop, on `clkb`. At 100 MHz it
met tt and ff but not ss (−0.87 ns, run 2 below): the contract asks `clkb` for 8 MHz or more, 50 MHz is
six times that. The 38.6 mW that LibreLane reports is OpenSTA's vectorless default activity at 5 V,
not a measurement; § 6 is the activity that the vectors give.

**In GF180MCU the OTP is the largest block**: the six eFuse blocks (48 452 µm²) are two thirds of the
transmitter's logic (72 330 µm²), because each block carries its sense amplifiers, latches and its own
power ring for 8 bits. The ROM (`ADV_ADDRESS`) costs nothing there (it folds into the read
multiplexer); the OTP is what makes AdvA per chip. A single 48-bit block would share the periphery.

What it took (each run kept only as the configuration's history; the final one is reproducible):

1. **The eFuse blocks had no supply** (run 1: `PSM-0069 Check connectivity failed on VDD`, 4 of 6
   blocks unconnected). The block's own VDD/VSS straps are on Metal4 and Metal5, the top metal of
   GF180MCU-D, so the core grid cannot cross it on a free layer; it is trimmed wherever it would short
   the block's shapes, and only blocks that a core strap happened to cross cleanly got power. Fix: the
   six blocks in one row and `PDN_HOFFSET = 69.92`, which puts one Metal5 VDD/VSS pair through every
   block's free corridor (y 40.86–55.96 µm of the block, no Metal5 shape there), with vias onto its
   Metal4 straps (`tx_min_gf180_efuse_pdn.png`).
2. **`clkb` was not timed** (284 unclocked flip-flops, no clock tree, 20 ns of latency through fanout
   buffers): LibreLane's base SDC constrains only the first `CLOCK_PORT`. Fix: `btle_tx.sdc`, both
   clocks, asynchronous.
3. **The resizer worked at tt only** and used delay cells (`dlyb_1`) and `clkbuf_1` chains as fanout
   buffers: 3.5 ns on one buffer, setup failing at ss, 316 slew violations. Fix: `RSZ_CORNERS` (ss,
   tt, ff), and no delay cells, `clkbuf_1`, `buf_1` or `aoi222_1` (the last one drove the only net left
   over 3 ns, under the eFuse row).
4. **With each corner's Liberty of the eFuse block**, `rst` → `reset_n` → `ready` → `adv_address_otp_ready`
   (the block's 32 ns sensing arc at ss) missed the output constraint by 0.19 ns. The fuses are
   sensed once after reset and held (`out` static, read like the ROM; `ready` a status output): a false
   path through the six `reset_n` pins, which the SDC refuses to apply unless it finds all six.

Not done: no pads or seal ring (a macro, not a chip), no parasitic-annotated simulation of the layout,
the eFuse programming port goes to the macro's pins (no production test interface, § 2).

## 8. Figures (as in `open_btle_baseband_chip/`)

`scripts/figures/tx_min_figures.py`, outputs in `results/figures/tx-min/`. The transmitter is the RTL of
this branch (`GAUSS_TABLE = 1`) under the upstream testbench; each waveform is compared with the Python
model, 0 samples differ in every case.

| Figure | Upstream's | What it shows |
|---|---|---|
| `tx_min_py_fig3.png` | `py-fig3.png` | a 39-byte ADV PDU (AdvA from the ROM, upstream's BER AdvData): upsampled bit, Gaussian filter output, normalized frequency offset; I and Q, all from the RTL |
| `tx_min_py_fig4.png` | `py-fig4.png` | the same waveform after a 20 dB, 20 ppm channel, the receiver's decision signal and best phase: CRC OK, the PDU received equal to the one sent |
| `tx_min_ber_ppm50.png`, `tx_min_ber_ppm-30.png` | `open_btle_baseband_chip_21_1.png`, `_23_1.png` | BER against SNR at 50 and −30 ppm, 39-byte ADV PDUs with random AdvData (100/200/300/300 packets per point), the transmitter the RTL and, with the same noise, the Python model: the two curves are identical; 0.1 % BER at about 24.5 dB (50 ppm) and 13.8 dB (−30 ppm), as upstream's |
| `tx_min_area.png` | — | the transmitter's area (logic and macros) of `master`, `ble-tx-rom` and both stores of this branch |
| `efuse_async_mem_1x8.png`, `efuse_xyce.png` | — | the eFuse block's layout (KLayout) and its Xyce programming and sensing waveforms |
| `tx_min_gf180_gds.png` | `btle-top-openlane-detailed-placement-cts.png`, `btle_rx_core-openlane-GDSII.png` | the GDS of § 7 (KLayout, the PDK's layer colours): the logic above, the six eFuse blocks in a row at the bottom |
| `tx_min_gf180_efuse.png`, `tx_min_gf180_efuse_pdn.png` | — | two eFuse blocks (fuse array, sense amplifiers, wrapper), all layers and Metal4/Metal5 only: the Metal5 VDD/VSS pair that crosses every block, with its vias onto the block's straps |

The BER uses upstream's `python/btlelib.py` (`upstream-baseline`) for the channel and the receiver, as
the original figures: the audited model returns no PDU when the CRC fails, which would count a whole
packet as wrong (a packet error rate, not a BER).

## 9. What the branch gives up

- **Any PDU but a Legacy Advertising one of at most 39 bytes**: no data-channel PDUs (unless their bytes
  2..7 happen to be the chip's AdvA), no extended advertising; the receiver keeps everything.
- **A changeable AdvA**: fixed per chip (ROM, or OTP programmed once); random or resolvable private
  addresses, which change at run time, cannot be sent.
- What `ble-tx-rom` gives up: the runtime Gaussian taps and the COS/SIN tables.
- The packet's contract of `ble-tx-pdu`: written before `tx_start`, the AXI clock at 8 MHz or faster.

## 10. Reproducing

From WSL, at the root of this branch (the tools of `results/validation/rom-evidence-20261005/tool_versions.txt`):

```bash
REF=fca6ac64fb28cd57a496cb45af62cf9e0f9209d5
python3 tests/test_tx_min.py --mutants --ref-rev $REF
G="btle_controller.v:GAUSS_TABLE=1 btle_phy.v:GAUSS_TABLE=1 btle_tx.v:GAUSS_TABLE=1 gfsk_modulation.v:GAUSS_TABLE=1 gauss_filter.v:GAUSS_TABLE=1"
A="btle_controller.v:ADV_ADDRESS=48'h04500e0f0200 btle_phy.v:ADV_ADDRESS=48'h04500e0f0200 btle_tx.v:ADV_ADDRESS=48'h04500e0f0200"
mkdir -p /tmp/btle-v && tar -xzf results/validation/product-evidence-20261005/vectors.tar.gz -C /tmp/btle-v
export REGRESSION_VECTORS=/tmp/btle-v/vectors
for ex in 0 2; do DUT_DEFAULTS="$G" REGRESSION_EXAMPLES=$ex bash scripts/validation/run_rx_regression.sh <label>-ex$ex $REF; done
DUT_DEFAULTS="$G $A" REGRESSION_EXAMPLES=1 bash scripts/validation/run_rx_regression.sh <label>-ex1 $REF
DUT_DEFAULTS="$G" python3 tests/test_tx_packet.py --rtl-rx --output /tmp/tx-packets.json
bash scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>-controller 2 6 $REF
PATH=/usr/bin:$PATH python3 scripts/validation/run_lint.py --output results/validation/<label>-lint   # Verilator 5.020
# area, timing and activity (run tx-min)
RTL_REV=HEAD AREA_PARAMS="GAUSS_TABLE=1" scripts/area/run_area.sh <label>
DUT_REV=HEAD DUT_PARAMS="GAUSS_TABLE=1" scripts/timing/run_sta.sh <label> 62.5 $REF
mkdir -p /tmp/vec && tar -xzf results/compare/tx-pdu-we/vectors.tar.gz -C /tmp/vec   # d53f2d49ed8db456
DUT_REV=HEAD DUT_PARAMS="GAUSS_TABLE=1" VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label> 100000 1 $REF
scripts/area/run_openram.sh <label> sram_1rw_8x32
# layout in GF180MCU-D with the OTP (needs the eFuse compiler and its macros, § 2)
scripts/layout/tx_min_gf180/run.sh <label> HEAD
# figures
python3 scripts/figures/tx_min_figures.py tx results/figures/<label>
python3 scripts/figures/tx_min_figures.py ber results/figures/<label>
```

The eFuse block: `./efuse.py 1 8 --async-efuse --digital-wrapper=async` in the compiler's `nix-shell`
(`results/otp/gf180-efuse/provenance.txt`); the activity runs need Verilator limited to a few build
jobs (`--build-jobs 4`) on a 32 GB machine, one configuration at a time (about 12 min each).
