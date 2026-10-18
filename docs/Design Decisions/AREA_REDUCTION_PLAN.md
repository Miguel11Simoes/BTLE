# Area reduction plan for a sticker-class BLE interface

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  
**Status:** baseline measured. On branch `ble-tx-table`, **B2 alone** is
implemented, measured and validated (2026-09-28); B1, A1 and A2 are not on this
branch (see [../Validation/TX_TABLE_VALIDATION.md](../Validation/TX_TABLE_VALIDATION.md)
and [../Validation/TX_BRANCH_COMPARISON.md](../Validation/TX_BRANCH_COMPARISON.md),
[../Validation/RX_BRANCH_COMPARISON.md](../Validation/RX_BRANCH_COMPARISON.md)).
Every saving below is marked either *measured* or *estimate*.

---

## Purpose

The BLE interface must shrink to fit a battery-free sticker tag, in the class of
Wiliot's, without losing any function the tag needs. This document measures
where the cells are today, sorts every candidate reduction by how it can be
proved, and fixes the order in which the reductions are made.

"Without losing any function" is judged against **the sticker's function set**,
not against the upstream SDR research platform. Most of the upstream area buys
debug visibility and SDR flexibility, and BLE does not need either. Every
function removed is listed as a removal, with the reason, so the claim can be
checked.

## 1. Baseline (measured)

Run `baseline-upstream`, produced by `scripts/area/run_area.sh` on commit
`74bb17c` (RTL identical to `upstream-baseline`). Toolchain: Yosys 0.68+195
(OSS CAD Suite 2026-09-07), Nangate45 typical liberty, sha256 `8d540a4d…`. The
flow and the rules are the same as MS-0-S1-YOSYS in `snitch_cluster_tese`.
Raw results are in
[`results/area/baseline-upstream/`](../../results/area/baseline-upstream/summary.md).

SRAMs (`sdpram_*`) are blackboxed macros: they are counted in bits and are
**not** included in the cell counts or cell areas.

| Top | Std cells | Flip-flops | Cell area (µm²) | SRAM bits |
|---|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 |
| `gauss_filter` | 2 286 | 178 | 3 366.0 | 0 |
| `vco` | 86 | 15 | 150.0 | 32 768 |
| `gfsk_modulation` | 2 466 | 229 | 3 740.2 | 32 768 |
| **`btle_tx`** | **3 409** | 404 | 5 322.9 | 36 864 |
| `gfsk_demodulation` | 3 899 | 100 | 4 757.4 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 |
| `btle_rx_core` | 4 438 | 202 | 5 669.0 | 0 |
| **`btle_rx`** (8 × `btle_rx_core`) | **36 864** | 2 068 | 48 824.3 | 32 768 |
| `btle_phy` | 40 339 | 2 472 | 54 040.3 | 69 632 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 048 576 |
| **`btle_ll`** | **9 453** | 2 036 | 16 746.3 | 17 862 |
| **`btle_controller`** (whole) | **50 295** | 4 578 | 71 706.4 | 1 136 070 |

### Where the cells go

| Share of `btle_controller` | Cells | % |
|---|---:|---:|
| RX (`btle_rx`) | 36 864 | 73.3 |
| … of which the 8 GFSK demodulators (8 × 3 899) | 31 192 | 62.0 |
| Link Layer wrapper (`btle_ll`) | 9 453 | 18.8 |
| TX (`btle_tx`) | 3 409 | 6.8 |
| … of which the Gaussian filter | 2 286 | 4.5 |
| IQ capture, AGC, clock crossing, top glue | 569 | 1.1 |

| Share of SRAM bits | Bits | % |
|---|---:|---:|
| IQ capture buffer (`auxiliary_daemon`) | 1 048 576 | 92.3 |
| TX COS/SIN tables | 32 768 | 2.9 |
| RX PDU buffers (8 × 512 × 8) | 32 768 | 2.9 |
| LL RX RAM + clock-crossing RAMs | 17 862 | 1.6 |
| TX PDU buffer | 4 096 | 0.4 |

Two facts dominate the cell count:

1. **The receiver decodes every packet 8 times.** `btle_rx.v` instantiates one
   complete `btle_rx_core` per sampling phase (lines 255–264) and keeps the one
   whose CRC passes. Each copy contains a demodulator built from two 16 × 16
   signed multipliers. Yosys already trims the 32-bit declarations in
   `gfsk_demodulation.v` down to 16 × 16 (`yosys.log`: "Removed top 16 bits
   (of 32)"), so fixing the widths saves nothing. The cost is in the
   replication.
2. **Almost all the memory is a debug buffer.** The 1 Mbit IQ capture exists so
   raw samples can be inspected on the FPGA board.

## 2. Target function set (to confirm)

The target is a battery-free sticker tag, in the class of Wiliot's. As far as I
know, such tags mainly **transmit BLE advertising packets** from harvested
energy, and do not hold connections. *This must be confirmed against the
datasheet of the product the thesis targets before any class-C cut (below) is
made.*

| Function | Needed by a sticker? |
|---|---|
| Legacy advertising TX (ADV_NONCONN_IND / ADV_IND), channels 37/38/39 | yes |
| Standard GFSK: BT = 0.5, h = 0.5, 1 Mb/s | yes |
| Runtime choice of payload, AA, CRC init, channel | yes |
| RX of advertising packets (scan requests, commands) | **open**: decides whether RX exists at all |
| Connections and data channels | probably not |
| Runtime-programmable Gaussian taps and COS/SIN tables | no (research flexibility) |
| Raw IQ capture, AGC for the AD9361, 64-bit timestamps, event counters, UART HCI | no (debug / SDR platform) |

## 3. Candidate reductions

Every candidate belongs to one class, and the class determines how it is proved.

- **A. Removal of infrastructure.** No BLE function changes. Proof: the
  testbenches still pass.
- **B. Equivalent rewrite.** Same outputs, bit for bit, for all legal inputs.
  Proof: the testbenches pass, plus an equivalence argument or formal check.
- **C. Function-set decision.** The output changes, or a function goes away.
  Proof: the standard is still met (BER curve, spectrum), and the removed
  function is recorded.

| # | Class | Change | Saves | Basis |
|---|---|---|---|---|
| A1 | A | Remove `auxiliary_daemon` (IQ capture, AGC) | 299 cells, **1 048 576 SRAM bits** | measured |
| A2 | A | Remove debug registers from `btle_ll`: 64-bit timestamps, 1 PPS, event counters, the 25 unconnected R/W registers, UART HCI | part of 9 453 cells | estimate; measure after the cut |
| A3 | A | Drop `KEEP_FOR_DBG` (`mark_debug` / `DONT_TOUCH`) | ≈ 0 in Yosys (it ignores them); matters for Vivado | measured indirectly |
| B1 | B | **One shared GFSK demodulator** for all 8 phases. Every phase computes `i[n-8]·q[n] − i[n]·q[n-8]`, one symbol apart; one unit with an 8-sample delay line produces the same product for every incoming sample. | ≈ 7 × 3 899 = **27 293 cells** (54 % of the controller) | estimate from measured parts |
| B2 | B | Gaussian filter → look-up table. The input is a repeated bit stream, so the 17-tap output depends only on 3 consecutive bits and the sample phase: 3 bits × 8 phases = 64 entries. As a ROM it stays bit-exact for the default taps. As a small RAM of 64 × 16 = 1 kbit written by software, it stays bit-exact for **any** taps and remains runtime-reconfigurable. *As implemented* (`GAUSS_TABLE=1`, same code as `ble-opt`): distributed-arithmetic tables over the 17-sample window (6+6+5 samples) built from fixed taps, exact for every input sequence. | estimate: most of 2 286 cells; **measured: 2 286 → 253 cells, controller 50 295 → 48 227** | **done on this branch**, validated in [TX_TABLE_VALIDATION.md](../Validation/TX_TABLE_VALIDATION.md) |
| B3 | B | COS/SIN tables: quarter-wave storage, 4× fewer bits | 24 576 bits | bit-exact only if the table is symmetric, so it becomes C if arbitrary tables must stay supported |
| C1 | C | **Single-phase receiver**: timing recovery on the preamble, then one decode | the remaining ≈ 7 × 540 cells of core logic, plus 7 PDU buffers (28 672 bits) | estimate; changes sensitivity; proof = BER vs SNR and ppm with `python/test_btle_ber.py`, against upstream's claim of 0.1 % BER at 11.5 dB / 20 ppm |
| C2 | C | PDU buffers sized for legacy advertising: 64 × 8 instead of 512 × 8 | 3 584 bits per buffer | only if data PDUs over 64 bytes are out of scope (§ 2) |
| C3 | C | **TX-only tag**: remove the receiver | all of `btle_rx` (36 864 cells, 32 768 bits) | depends on § 2 |
| C4 | C | Direct PLL/DCO modulation instead of I/Q: the baseband outputs a frequency word, so the VCO and the COS/SIN tables disappear | 86 cells + 32 768 bits, plus the need for an I/Q DAC path | changes the analogue interface; proof = instantaneous frequency compared with `python/test_alignment_with_btle_sdr.py` |
| C5 | C | Lower baseband clock once RX oversampling is gone or single-phase | power, not cells | energy per packet |

### What the reductions add up to (estimate)

| Scenario | Controller cells | SRAM bits |
|---|---:|---:|
| Upstream today (measured) | 50 295 | 1 136 070 |
| **B2 alone (measured, this branch, `GAUSS_TABLE=1`)** | **48 227** | 1 136 070 |
| A1 + B1 (no function removed) | ≈ 22 700 | ≈ 87 500 |
| + A2 + B2 | lower still; A2 depends on the new LL interface | ≈ 87 500 |
| TX-only sticker: C3 + C4 + B2 + minimal LL | a few thousand | ≈ 4 000 (TX PDU buffer) |

These totals are sums of measured parts minus the estimated savings. They
become measurements only when each change is implemented and the flow is run
again under a new label.

## 4. The consequence for the RISC-V choice

A TX-only advertising baseband after B2 and C3 comes down to a CRC-24
(287 cells), a whitening LFSR (121), an upsampler (94), a small Gaussian table
and the packet state machine. Any RISC-V core is larger than that. In a sticker,
**the core, not the radio, dominates the area**. This narrows decision **D2**
in [SCOPE.md](SCOPE.md) towards the smallest cores (bit-serial SERV, RV32E),
and decision **D3** towards "replaceable firmware" rather than reconfigurable
logic. The next measurement should put the candidate cores through the same
flow, so the comparison uses the same ruler.

## 5. Order of work

1. **Close gaps 1 and 4** of the test inventory
   ([../Validation/UPSTREAM_TEST_INVENTORY.md](../Validation/UPSTREAM_TEST_INVENTORY.md)):
   run every testbench and script a regression. Without it, "no function lost"
   cannot be proved.
2. **A1**, then **B1**, then **B2**, one commit each. After each commit, run the
   regression and the area flow under a new label, and add a row to this
   document with the measured result.
3. Confirm the target function set (§ 2) with the supervisor.
4. The class-C cuts that § 2 allows, each with its BER or frequency evidence.
5. Measure the candidate RISC-V cores with the same flow.

## 6. Reproducing the baseline

From WSL, at the repository root:

```bash
scripts/area/run_area.sh <new-label>            # all 16 tops, ~2 min on the baseline
scripts/area/run_area.sh <new-label> btle_rx    # one top
```

The script refuses to overwrite an existing label. It records the commit,
tool version and liberty hash in `provenance.txt`, keeps the logs compressed,
and stores only the sha256 of each mapped netlist in `netlist.sha256`.

## Revision history

| Date | Change |
|---|---|
| 2026-09-18 | First version: baseline measured, candidates classified. |
| 2026-09-28 | Branch `ble-tx-table`: B2 implemented alone (the `ble-opt` code) and measured, controller 50 295 → 48 227 cells. The rest of this plan is left as it was on 2026-09-18; its later revisions are on `ble-opt`. |
