# The best transmitter together: B2 and the {cos, sin} memory (`ble-tx-opt`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-opt`, from `ble-tx-table` (`e6bf731`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-29  
**Author:** Miguel Simões  
**Status:** executed: `tests/test_vco_sin8.py`, runs `tx-opt` of
`scripts/validation/run_rx_regression.sh` and `scripts/validation/ctl_lockstep/run_ctl_lockstep.sh`,
and run `tx-opt` of `scripts/compare/run_compare.sh` (area, static timing, gate-level lockstep
and switching activity; `docs/04 Validation/BRANCH_COMPARISON.md`).

---

## Purpose

The other branches shrink the two parts of the transmitter separately. For
the Gaussian filter, the constant tables of B2 (`ble-tx-table`) are the
smallest option of `docs/02 Design Decisions/GAUSS_FILTER_OPTIONS.md`: 348.5 µm²
against 3 366.0 µm² for the upstream FIR. For the VCO, the quarter-wave tables
of `ble-tx-sin4`, kept in one {cos, sin} memory on `ble-tx-sin8`, are the
smallest memory. This branch puts those two together, and nothing else: the
receiver (8 demodulators), the Link Layer and the IQ-capture debug memory are
upstream's. It answers two questions: how small the transmitter gets once
both are built into one design, and whether the two savings add up.

## 1. What the branch contains

| Part | Taken from | Files | How it is selected |
|---|---|---|---|
| Gaussian filter: constant distributed-arithmetic tables (B2) | `ble-tx-table` | `gauss_filter.v`, `gfsk_modulation.v`, `btle_tx.v`, `btle_phy.v`, `btle_controller.v`: byte-identical | `GAUSS_TABLE=1`; the default, 0, is the upstream FIR |
| VCO: the first quarter of the COS and SIN tables, in one 512 × 16 memory with a write mask | `ble-tx-sin8` | `vco.v`: byte-identical (blob `cb281b1`) | structural, always on |
| Receiver, Link Layer, IQ-capture RAM, everything else | upstream | unchanged | — |

The branch is `ble-tx-table` plus the `vco.v` of `ble-tx-sin8`, which
`ble-tx-table` had never changed, so the two parts meet only at the VCO's
input, the filtered frequency. As on `ble-tx-table` and `ble-opt`, B2 is a
parameter that defaults to the upstream FIR, and the branch is measured with
it on (`scripts/branch_config.sh` gives `GAUSS_TABLE=1`).

## 2. Evidence

The two parts keep their own proofs, because their files are the same bytes:
B2 is equivalent to the upstream FIR, unbounded, in
`docs/04 Validation/TX_TABLE_VALIDATION.md`; the VCO is checked in
`TX_SIN8_COMPARISON.md` on `ble-tx-sin8` (sweep against `master`, random
lockstep against `ble-tx-sin4`, 7/7 mutants). Together, on this branch:

| Check | What it compares | Result |
|---|---|---|
| Upstream testbenches (`scripts/validation/run_rx_regression.sh`, table on through `DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1"`) | the 5 upstream testbenches (demodulator, RX core, RX, TX, controller) over 54 conditions: 3 packets × 3 SNR × 3 clock errors × 2 delays, every output file byte for byte against upstream | **270/270 runs identical**; 24 fail on both designs at 8 dB, a limit of the model, as on every branch |
| Controller through the registers (`scripts/validation/ctl_lockstep/run_ctl_lockstep.sh`) | the whole controller against upstream, clock by clock, the COS and SIN tables written through the AXI registers one after the other as the firmware does, packets of the Python model sent and received | **15/15 runs, 923 385 cycles, every output and every register read identical**; 90 packets sent and 90 received; 4/4 mutants caught (a wrong table tap, a group index off by one, a wrong sign, the IQ-capture half flag) |
| The VCO (`tests/test_vco_sin8.py`) | the sweep against the `master` VCO; 4 × 1 000 000 clocks against the `ble-tx-sin4` VCO with random table writes | **3 072 clocks and 2 919 121 comparisons, no mismatch** |
| Gate-level lockstep (run `tx-opt`, `BRANCH_COMPARISON.md` § 6.1) | both synthesised netlists, this branch and upstream, on every output and every clock, in 5 scenarios | **5/5 scenarios, no mismatch**; 25 packets transmitted, 27 sent to the receiver |

The upstream TX testbenches write the COS and SIN tables at the same address
on every clock, so the memory of this branch writes both halves in one write;
the controller lockstep writes one table at a time. Both stay inside the
write-rate limit of § 5.

## 3. Area

Yosys 0.68 + ABC, Nangate45, SRAMs blackboxed and counted in bits (run
`tx-opt`; the other columns are runs `all-branches` and `tx-sin8` of the same
harness). Each top is synthesised alone.

| Top | `master` | `ble-tx-table` | `ble-tx-sin8` | **`ble-tx-opt`** |
|---|---:|---:|---:|---:|
| `gauss_filter` (cells) | 2 286 | 253 | 2 286 | **253** |
| `vco` (cells) | 86 | 86 | 438 | **438** |
| `btle_tx`: cells / flip-flops | 3 409 / 404 | 1 392 / 248 | 3 718 / 482 | **1 696 / 326** |
| `btle_tx`: cell area (µm²) | 5 322.9 | 2 325.6 | 6 025.4 | **3 028.9** |
| `btle_controller`: cells / flip-flops | 50 295 / 4 578 | 48 227 / 4 422 | 50 716 / 4 656 | **48 559 / 4 500** |
| `btle_controller`: SRAM bits | 1 136 070 | 1 136 070 | 1 111 494 | 1 111 494 |

The filter and the VCO synthesise exactly as on the branches they come from
(253 and 438 cells), and the transmitter logic is now smaller than the
upstream Gaussian filter alone (3 028.9 against 3 366.0 µm²).

**The two savings add up.** On the transmitter:

| | Std cells | Flip-flops | Cell area (µm²) |
|---|---:|---:|---:|
| B2 (`ble-tx-table` − `master`) | −2 017 | −156 | −2 997.3 |
| {cos, sin} memory (`ble-tx-sin8` − `master`) | +309 | +78 | +702.5 |
| Sum of the parts, from `master` | 1 701 | 326 | 3 028.1 |
| **Measured, `ble-tx-opt`** | **1 696** | **326** | **3 028.9** |
| Residual | −5 | 0 | +0.8 |

On the whole controller the flip-flops add up exactly (4 578 − 156 + 78 =
4 500) and the cells to within 89 (0.2 %), the flow noise that
`BRANCH_COMPARISON.md` § 3.1 records (the receiver alone, the same RTL, moves
by up to 116 cells from one netlist to another).

**The transmitter with its SRAM macros** (OpenRAM, FreePDK45; runs
`openram-tx` and `openram-sin8`; one read/write port and one read port, as the
RTL needs):

| | `master` | `ble-tx-table` | `ble-tx-sin8` | **`ble-tx-opt`** |
|---|---:|---:|---:|---:|
| TX cells (µm²) | 5 322.9 | 2 325.6 | 6 025.4 | 3 028.9 |
| COS/SIN macros (µm²) | 138 700.5 | 138 700.5 | 37 703.9 | 37 703.9 |
| Packet buffer (µm²) | 23 708.0 | 23 708.0 | 23 708.0 | 23 708.0 |
| **Total TX (µm²)** | **167 731.4** | **164 734.1** | **67 437.3** | **64 440.8** |
| vs `master` | — | −1.8 % | −59.8 % | **−61.6 %** |
| Total with single-port macros (µm²) | 79 667.6 | 76 670.3 | 33 844.0 | 30 847.5 (−61.3 %) |

`BRANCH_COMPARISON.md` had estimated this combination at 64 440.0 µm² from the
two branches apart; built, it measures 64 440.8. The memories are now 95 % of
the transmitter, so what is left to gain is in the macros (the packet buffer,
23 708 µm², and the {cos, sin} memory), not in the logic.

## 4. Timing and switching activity

Run `tx-opt`, the whole controller against upstream
(`docs/04 Validation/BRANCH_COMPARISON.md` §§ 5 and 6):

- **Timing:** minimum period 1.917 ns at the 62.5 ns (16 MHz) target, against
  1.991 ns upstream. The worst path is still the multiply of one of the 8
  upstream demodulators, in the receiver; the difference is flow noise.
- **Switching activity** (pin-capacitance proxy, not power): −1.1 to −3.1 %
  over the five scenarios. The Gaussian table saves 2.3 to 5.0 points, the
  write port of the {cos, sin} memory costs 1.2 to 1.8, and the two add up to
  within 0.1 point in every scenario:

| Scenario | B2 (`ble-tx-table`) | {cos, sin} memory (`ble-tx-sin8`) | Sum | **`ble-tx-opt`** |
|---|---:|---:|---:|---:|
| `rx` | −2.4 % | +1.2 % | −1.3 % | **−1.2 %** |
| `tx` | −5.0 % | +1.8 % | −3.2 % | **−3.1 %** |
| `mixed` | −3.2 % | +1.3 % | −1.9 % | **−1.8 %** |
| `idle` | −2.3 % | +1.2 % | −1.2 % | **−1.1 %** |
| `idle0` | −3.1 % | +1.5 % | −1.6 % | **−1.5 %** |

While transmitting, the Gaussian filter switches 69 % less (79.1 → 24.8
toggles per cycle) and all non-clock toggles fall 15.1 %; the clock-pin load
falls 1.7 % in every scenario (156 flip-flops fewer in the filter, 78 more in
the write port).

## 5. What the branch gives up

The sum of what its two parts give up, and nothing else:

- **The runtime Gaussian taps** (as `ble-tx-table`): the taps become a
  synthesis parameter, so changing the filter needs a new chip.
- **Arbitrary COS/SIN tables** (as `ble-tx-sin4`): each table must have
  quarter-wave symmetry; only addresses 0..511 are stored. The project's
  tables have it.
- **The write rate of the tables** (as `ble-tx-sin8`): at most w + 1 table
  writes in any w consecutive clocks, two writes to the same address in one
  clock counting as one; upstream accepts two per clock. The firmware writes
  one table at a time, a register write every few clocks.

The receiver, the Link Layer and the IQ-capture debug memory lose nothing.

## 6. Reproducing

From WSL, at the root of this branch:

```bash
python3 tests/test_vco_sin8.py                                                  # IVERILOG, VVP in PATH
DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1" scripts/validation/run_rx_regression.sh <label>
scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> master ble-tx-opt
```
