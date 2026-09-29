# Comparison of the branches: upstream, the transmitter variants, B1 and `ble-opt`

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** every branch carries this same file (`master`, `risc-v-ble`, `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-rx-dm`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-28; updated 2026-09-29 (five transmitter branches, SRAM macro areas)  
**Author:** Miguel Simões  
**Status:** executed: run `all-branches`, harness `scripts/compare/` at `f540e99` (summary
regenerated at `696b036`, § 11); with the same harness and the same vectors, run `tx-variants`
(`fe14935`) for four transmitter branches (its two failed checks are explained in § 6.1) and run
`tx-sin8` (`577bb31`) for `ble-tx-sin8`; transmitter SRAM macros from runs `openram-tx` and
`openram-sin8` (OpenRAM 1.2.48, FreePDK45). Pre-layout area and static timing; gate-level
switching activity, which is a proxy and **not power**.

---

## Purpose

`ble-opt` shrinks the BLE controller with four changes applied together. Two
of them rewrite the signal processing, and two remove debug infrastructure:

| # | Change | Block |
|---|---|---|
| B1 | one shared GFSK demodulator instead of 8 | receiver (`btle_rx`) |
| B2 | fixed-tap tables instead of the Gaussian FIR | transmitter (`gauss_filter`) |
| A1 | no IQ-capture debug RAM | `auxiliary_daemon` |
| A2 | minimal Link Layer (no UART HCI, 1 PPS, debug registers) | `btle_ll` |

Two branches isolate the signal-processing changes: `ble-tx-table` holds only
B2 and `ble-rx-dm` only B1. Five more change only the transmitter. Three of them
build the Gaussian filter another way: `ble-tx-table-reg` and
`ble-tx-table-sram` keep B2's tables but rewritable (in flip-flops, in SRAM),
and `ble-tx-fir2` folds the FIR by the symmetry of its taps; their choice is
argued in `docs/02 Design Decisions/GAUSS_FILTER_OPTIONS.md`. The other two
shrink the VCO's memory: `ble-tx-sin4` stores only the first quarter of the
cosine and sine tables and rebuilds the rest by symmetry, and `ble-tx-sin8`
then keeps those two quarter tables, which are always read at the same
address, in one memory of {cos, sin} words.

This document measures every branch with the same ruler and answers four
questions: what each change buys on its own, whether the changes add up, what
each one costs in function, and how large the transmitter really is once its
memories are counted. The area flow counts RAM in bits only, so it cannot
weigh logic against memory; § 4 adds the area of real SRAM macros.

This file is identical on every branch. The raw results it cites are in
`results/compare/{all-branches,tx-variants,tx-sin8}/`, in the
per-configuration folders `results/{area,timing,power}/{all-branches,tx-variants,tx-sin8}/`
and in `results/area/{openram-tx,openram-sin8}/`, which exist on `ble-opt`,
`ble-tx-table` and `ble-rx-dm`; the relative links below resolve there.

## 1. The branches

| Branch | What it is | RTL (`verilog/`) against upstream | Measured as |
|---|---|---|---|
| `master` | upstream BTLE at tag `upstream-baseline` (`8540186`) | the reference; tree `4bacca3` | defaults |
| `risc-v-ble` | `master` + the thesis documentation | **identical**: same tree `4bacca3` | same as `master` |
| `ble-tx-table` | B2 alone | 5 RTL files and the testbench fix U9; tree `2d36551` | `GAUSS_TABLE=1` |
| `ble-tx-table-reg` | B2's tables in 2 560 flip-flops, rebuilt in hardware from the 9 runtime taps | as `ble-tx-table`, with a larger `gauss_filter.v`; tree `c8675f2` | `GAUSS_TABLE=1` |
| `ble-tx-table-sram` | the same tables in three SRAM banks (2 560 bits) | as `ble-tx-table`, with a larger `gauss_filter.v`; tree `3887f20` | `GAUSS_TABLE=1` |
| `ble-tx-fir2` | folded (symmetric) Gaussian FIR, taps still programmable | `gauss_filter.v` and U9; tree `07255a3` | defaults (the folded FIR is not a parameter) |
| `ble-tx-sin4` | quarter-wave VCO tables: 2 × 512 × 8 bits instead of 2 × 2 048 × 8 | `vco.v` only; tree `fd4e70c` | defaults (not a parameter) |
| `ble-tx-sin8` | the two quarter-wave tables in one 512 × 16 memory, {cos, sin} per word | `vco.v` only; tree `8ba2c0e` | defaults (not a parameter) |
| `ble-rx-dm` | B1 alone | `btle_rx.v`, `btle_rx_core.v`, new `gfsk_demodulation_shared.v`, file lists, U9; tree `aa807f8` | defaults (B1 is not a parameter) |
| `ble-opt` | B1 + B2 + A1 + A2, plus the model-update firmware | 11 RTL files (1 new), the Vivado file list, 2 testbenches; tree `b78aa37` | `ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1` |

How they relate:

```
master  (= upstream-baseline, 8540186)
 ├─ ble-tx-sin4                  from fae132e: quarter-wave VCO tables (5df56e9)
 │   └─ ble-tx-sin8              from 8567f8d: one {cos, sin} memory (94a7bc7), its test
 └─ risc-v-ble                   70cab42, 3e3086e: documentation only
     └─ 74bb17c, 69c8b51         area flow; upstream baseline measured
         ├─ ble-tx-table         + B2 alone (dfcc15c), U9 (4c8d66a), its validation
         │   ├─ ble-tx-table-reg     from f6c9f78: tables in flip-flops (e5d7f51)
         │   └─ ble-tx-table-sram    from f6c9f78: tables in SRAM (65eefff)
         ├─ ble-tx-fir2          + folded FIR (05d5d95), U9 (7f45d46), its proofs
         └─ aa8a014 … 88f2250    B1 and its proofs
             ├─ ble-rx-dm        = 88f2250: B1 alone, nothing of A1, A2, B2
             └─ 39f5851 … d37ac4b    A1, A2, B2, model update, activity, timing  (ble-opt)
```

Every branch then has commits that add this document; the three measurement
branches also carry the comparison harness (the same files on the three) and
its results.

The two isolated branches measure **exactly the code that `ble-opt`
combines**. `ble-rx-dm` is the `ble-opt` history itself, stopped at `88f2250`.
In `ble-tx-table`, `gauss_filter.v`, `gfsk_modulation.v` and `btle_tx.v` are
byte-identical to `ble-opt`, and `btle_phy.v` and `btle_controller.v` carry only
the B2 lines of `39f5851`. The five transmitter branches are alternatives to B2
(`reg`, `sram`, `fir2`) or independent of it (`sin4` and `sin8`, which touch
only `vco.v`), and none of them is part of `ble-opt`.

A branch is measured in **its configuration: every optional reduction its
`btle_controller` declares, switched on** (`scripts/branch_config.sh`). The
parameters default to the original design on every branch, so the Vivado flow
of the boards sees upstream unless it asks otherwise; B1, the folded FIR, the
quarter-wave tables and the {cos, sin} memory are the exceptions, because they
are structural.

## 2. The comparison

Differences are against `master`. `risc-v-ble` has the same `verilog/` tree
as `master`, so its figures are the same by construction: the flows are
deterministic for identical inputs, `master` reproduces the committed
`baseline-upstream` area run exactly, and it came out identical in all three runs
(§§ 3, 6.1).

| | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-rx-dm` | `ble-opt` |
|---|---|---|---|---|---|---|---|---|---|
| **Content** | upstream BTLE (+ thesis docs on `risc-v-ble`) | **B2** | B2's tables in flip-flops | B2's tables in SRAM | folded FIR | quarter-wave VCO tables | one {cos, sin} memory for the quarter-wave tables | **B1** | **B1 + B2 + A1 + A2** |
| Configuration measured | defaults | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | defaults | defaults | defaults | defaults | `ENABLE_IQ_CAPTURE=0`, `LL_MINIMAL=1`, `GAUSS_TABLE=1` |
| GFSK demodulators in `btle_rx` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | **1, shared** | **1, shared** |
| Gaussian filter | FIR, runtime taps | **fixed-tap table** | **table in 2 560 flip-flops**, runtime taps | **table in SRAM**, runtime taps | **folded FIR**, runtime taps | FIR, runtime taps | FIR, runtime taps | FIR, runtime taps | **fixed-tap table** |
| VCO COS / SIN tables | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | **2 × 512 × 8** | **1 × 512 × 16** ({cos, sin}) | 2 × 2 048 × 8 | 2 × 2 048 × 8 |
| IQ-capture debug RAM (1 Mbit) | yes | yes | yes | yes | yes | yes | yes | yes | **removed** |
| Link Layer | full | full | full | full | full | full | full | full | **minimal** |
| **Std cells, `btle_controller`** | 50 295 | 48 227 (−4.1 %) | 58 091 (+15.5 %) | 49 324 (−1.9 %) | 49 620 (−1.3 %) | 50 397 (+0.2 %) | 50 716 (+0.8 %) | 23 346 (−53.6 %) | **16 102 (−68.0 %)** |
| Flip-flops | 4 578 | 4 422 (−3.4 %) | 7 222 (+57.8 %) | 4 667 (+1.9 %) | 4 570 (−0.2 %) | 4 581 (+0.1 %) | 4 656 (+1.7 %) | 3 926 (−14.2 %) | 2 673 (−41.6 %) |
| Cell area (µm²) | 71 706 | 68 667 (−4.2 %) | 91 556 (+27.7 %) | 70 896 (−1.1 %) | 70 652 (−1.5 %) | 71 863 (+0.2 %) | 72 484 (+1.1 %) | 38 782 (−45.9 %) | 26 681 (−62.8 %) |
| **SRAM bits** | 1 136 070 | 1 136 070 | 1 136 070 | 1 138 630 (+0.2 %) | 1 136 070 | 1 111 494 (−2.2 %) | 1 111 494 (−2.2 %) | 1 136 070 | **87 046 (−92.3 %)** |
| **Transmitter with its SRAM macros (µm², § 4)** | 167 731 | 164 734 (−1.8 %) | 187 610 (+11.9 %) | 185 280 (+10.5 %) | 166 704 (−0.6 %) | **76 552 (−54.4 %)** | **67 437 (−59.8 %)** | 167 737 (0) | 164 734 (−1.8 %) |
| Min period at 16 MHz (62.5 ns) | 1.991 ns | 1.905 ns | 1.995 ns | 2.011 ns | 1.877 ns | 2.007 ns | 1.910 ns | 1.834 ns | 1.944 ns |
| Slack / Fmax | +60.509 ns / 502 MHz | +60.595 ns / 525 MHz | +60.505 ns / 501 MHz | +60.489 ns / 497 MHz | +60.623 ns / 533 MHz | +60.493 ns / 498 MHz | +60.590 ns / 524 MHz | +60.666 ns / 545 MHz | +60.556 ns / 514 MHz |
| Worst path | demodulator multiply, one of 8 copies | Link Layer 64-bit timestamp | demodulator multiply, one of 8 copies | the same | the same | the same | Link Layer 64-bit timestamp | shared demodulator multiply | Link Layer 64-bit timestamp |
| **Data + clock switched capacitance, `mixed`** | 1.25 × 10⁹ fF | −3.2 % | +40.8 % | +0.6 % | −0.5 % | +0.1 % | +1.3 % | −9.5 % | **−30.3 %** |
| … over the 5 scenarios | — | −2.3 to −5.0 % | +39.9 to +53.0 % (4 scenarios, § 6.1) | +0.6 to +1.8 % (4 scenarios) | −0.1 to −1.1 % | 0 to +0.4 % | +1.2 to +1.8 % | −5.9 to −12.9 % | −25.5 to −34.7 % |
| Clock pins (load × toggles) | 8.76 × 10⁸ fF | −3.4 % | +57.3 % | +1.9 % | −0.2 % | +0.1 % | +1.7 % | −14.1 % | −41.4 % |
| Non-clock toggles / cycle, `mixed` | 984.3 | 956.4 (−2.8 %) | 988.0 (+0.4 %) | 958.7 (−2.6 %) | 971.0 (−1.4 %) | 987.0 (+0.3 %) | 989.4 (+0.5 %) | 1 004.5 (+2.1 %) | 939.7 (−4.5 %) |
| Nets with activity > 10 %, `mixed` | 839 | 827 | 836 | 824 | 841 | 851 | 845 | 4 002 (×4.8) | 3 908 (×4.7) |
| RAM-port toggles, `mixed` | 3 044 741 | unchanged | unchanged | +10.8 % | unchanged | −0.4 % | −0.4 % | unchanged | −40.0 % |
| Functions removed | — | runtime Gaussian taps | none; 928 clocks after a tap write before the next transmission | the same | none | COS/SIN tables without quarter-wave symmetry | as `ble-tx-sin4`; table writes limited to w + 1 in any w clocks (§ 8) | **none** | runtime taps, IQ capture, UART HCI, 1 PPS, latency counter |
| Gate-level outputs vs upstream, 5 scenarios | — | identical, every output | identical in 4; `tx` transmits before the rebuild (§ 6.1) | the same | identical, every output | identical, every output | identical, every output | identical, every output | identical, except the 3 removed outputs |

## 3. Area

Same flow as every earlier run: Yosys 0.68, `synth -flatten`, `dfflibmap`,
`abc -liberty`, Nangate45, SRAMs blackboxed and counted in bits. All 16 tops
were synthesised for each branch; results in
[`results/area/all-branches/`](../../results/area/all-branches/),
[`results/area/tx-variants/`](../../results/area/tx-variants/) and
[`results/area/tx-sin8/`](../../results/area/tx-sin8/). Every
configuration reproduces its earlier area run top for top: `master` =
`baseline-upstream` (in all three runs), `ble-tx-table` = `tx-table`, `ble-rx-dm` =
`shared-demod`, `ble-opt` = `sticker`; the Gaussian filter and the
transmitter of `ble-tx-table-reg`, `ble-tx-table-sram` and `ble-tx-fir2` =
run `tx-area` of `GAUSS_FILTER_OPTIONS.md`, and the transmitter of
`ble-tx-sin4` = its own `TX_SIN4_COMPARISON.md`.

### 3.1 Per block (std cells, each top synthesised alone)

| Top | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gauss_filter` | 2 286 | **253** (−88.9 %) | 10 097 (+341.7 %) | 1 362 (−40.4 %) | **1 560** (−31.8 %) | 2 286 | 2 286 | 2 286 | **253** (−88.9 %) |
| `vco` | 86 | 86 | 86 | 86 | 86 | 179 (+108.1 %) | 438 (+409.3 %) | 86 | 86 |
| `btle_tx` | 3 409 | **1 392** (−59.2 %) | 11 328 (+232.3 %) | 2 477 (−27.3 %) | **2 707** (−20.6 %) | 3 465 (+1.6 %) | 3 718 (+9.1 %) | 3 411 | **1 392** (−59.2 %) |
| `btle_rx` | 36 864 | 36 884 | 36 954 | 36 954 | 36 980 | 36 884 | 36 928 | **10 068** (−72.7 %) | **10 068** (−72.7 %) |
| `btle_phy` | 40 339 | 38 083 (−5.6 %) | 48 192 (+19.5 %) | 39 294 (−2.6 %) | 39 655 (−1.7 %) | 40 384 (+0.1 %) | 40 573 (+0.6 %) | 13 536 (−66.4 %) | 11 394 (−71.8 %) |
| `auxiliary_daemon` | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | **233** (−22.1 %) |
| `btle_ll` | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | **4 336** (−54.1 %) |
| **`btle_controller`** | **50 295** | **48 227** (−4.1 %) | **58 091** (+15.5 %) | **49 324** (−1.9 %) | **49 620** (−1.3 %) | **50 397** (+0.2 %) | **50 716** (+0.8 %) | **23 346** (−53.6 %) | **16 102** (−68.0 %) |

The cell counts leave out the RAMs. `ble-tx-table-sram` moves 2 560 bits of
its table into SRAM banks (controller: 1 138 630 SRAM bits), and
`ble-tx-sin4` and `ble-tx-sin8` remove 24 576 bits (1 111 494), which
`ble-tx-sin8` then keeps in one memory instead of two; § 4 converts the
transmitter's RAMs into area.

Each change moves only its own block. The small moves elsewhere (`btle_rx`
36 864 → 36 884 … 36 980 on the transmitter branches, `btle_tx` 3 409 → 3 411
on `ble-rx-dm`) are the flow noise already recorded on `ble-opt`: ABC's result
depends on everything Yosys reads.

### 3.2 The savings add up

| Saving on `btle_controller` | Std cells | Flip-flops |
|---|---:|---:|
| B2 alone (`ble-tx-table`) | 2 068 | 156 |
| B1 alone (`ble-rx-dm`) | 26 949 | 652 |
| A1 + A2, on their own tops (`auxiliary_daemon`, `btle_ll`; `ble-opt` against `master`) | 5 183 | 1 097 |
| **Sum of the parts** | **34 200** | **1 905** |
| **All four together (`ble-opt`)** | **34 193** | **1 905** |
| Residual | −7 (0.02 % of the controller) | 0 |

The four changes are **independent**: the whole is the sum of the parts to
within 7 cells, and exactly in flip-flops. Each one can be kept or dropped on
its own with a predictable effect. The SRAM saving is A1 and A2 only:
1 048 576 bits (the IQ-capture RAM) + 448 bits (Link Layer crossings) =
1 049 024 = 1 136 070 − 87 046.

The transmitter branches do not enter this sum. `ble-tx-table-reg`,
`ble-tx-table-sram` and `ble-tx-fir2` replace the same block as B2, so one of
them can be chosen instead of B2, not added to it. `ble-tx-sin4` changes only
`vco.v`, so it would add to any of them; its cost in logic is the VCO's
+93 cells (+124.2 µm²), +56 cells (+104.8 µm²) on the whole transmitter.
`ble-tx-sin8`, also only `vco.v`, adds another 259 cells and 75 flip-flops to
the VCO for the shared write port of its table memory (+597.7 µm² on the
transmitter).

### 3.3 Share of each change in the total reduction

| Change | Share of the cells saved | Share of the SRAM bits saved |
|---|---:|---:|
| B1, shared demodulator | 78.8 % | 0 |
| A1 + A2, debug infrastructure | 15.2 % | 100 % |
| B2, Gaussian table | 6.0 % | 0 |

Shares of the sum of the parts (34 200 cells). B1 is most of the logic saving
because upstream replicates the demodulator 8 times (62 % of the controller).
B2 removes 89 % of the Gaussian filter, but the filter is only 4.5 % of the
controller. The memory saving of `ble-opt` comes only from removing debug
infrastructure.

## 4. The transmitter with its memories

The area flow counts RAMs in bits only, so the cell area of § 3 leaves out
most of the transmitter. `btle_tx` has three RAMs, and each is written by one
side while the other reads it:

| RAM | RTL | Every other branch | `ble-tx-sin4` | `ble-tx-sin8` | Written | Read |
|---|---|---|---|---|---|---|
| COS table | `vco.v`, `sdpram_one_clk` | 2 048 × 8 | 512 × 8 | one 512 × 16, {cos, sin} per word, with a write mask of one bit per table | from the table registers, on every clock (`write_enable` tied to 1); on `ble-tx-sin8`, when a register changes, through one shared port | at the VCO phase, on every clock |
| SIN table | `vco.v`, `sdpram_one_clk` | 2 048 × 8 | 512 × 8 | (the same word) | the same | the same |
| PDU buffer | `btle_tx.v`, `sdpram_two_clk` | 512 × 8 | 512 × 8 | 512 × 8 | by the processor side, on `clkb`, every clock | by the packet path, on `clk` |

`ble-tx-table-sram` adds the three Gaussian-table banks, 2 560 bits,
18 437.4 µm² (`GAUSS_FILTER_OPTIONS.md` § 3). The receiver is not converted.
In the RTL of `ble-tx-sin8`, the 512 × 16 memory is written as its two
halves, two `sdpram_one_clk` that share the write and read addresses (the mask
bits are their write enables); it is one macro.

### 4.1 The macros

OpenRAM 1.2.48 in FreePDK45, the process behind the Nangate45 cells, default
layout, in two port sets (`scripts/area/run_openram.sh`, runs
[`openram-tx`](../../results/area/openram-tx/summary.md) and
[`openram-sin8`](../../results/area/openram-sin8/summary.md)):

| Macro | Ports | Words × bits | Size (µm) | Area (µm²) | µm² per bit |
|---|---|---|---|---:|---:|
| `sram_1rw1r_8x2048` | 1 read/write + 1 read | 2 048 × 8 | 232.930 × 297.730 | 69 350.2 | 4.23 |
| `sram_1rw1r_8x512` | 1 read/write + 1 read | 512 × 8 | 146.120 × 162.250 | 23 708.0 | 5.79 |
| `sram_1rw1r_16x512_m8` | 1 read/write with an 8-bit write mask + 1 read | 512 × 16 | 230.000 × 163.930 | 37 703.9 | 4.60 |
| `sram_1rw_8x2048` | 1 read/write | 2 048 × 8 | 136.623 × 232.907 | 31 820.4 | 1.94 |
| `sram_1rw_8x512` | 1 read/write | 512 × 8 | 85.285 × 125.507 | 10 703.9 | 2.61 |
| `sram_1rw_16x512_m8` | 1 read/write with an 8-bit write mask | 512 × 16 | 135.157 × 126.627 | 17 114.7 | 2.09 |

- **1RW1R is the macro the RTL needs**, and the one used below: every RAM of
  the transmitter is a simple dual-port model whose write port and read port
  work in the same cycle, and the PDU buffer has a clock on each side.
- **1RW is a lower bound.** One port would do only if the RTL wrote the tables
  and the buffer while the transmitter is idle and gated the writes, which no
  branch does.
- **A quarter of the bits is a third of the area.** The periphery (decoders,
  sense amplifiers, write drivers, control, supply rings) does not shrink with
  the array: 512 × 8 costs 34 % of 2 048 × 8, in both port sets.
- **One 16-bit macro costs 20 % less than two 8-bit ones** (37 703.9 against
  47 415.9 µm²; 20.1 % with one port). The two tables share the address
  decoders, word-line drivers, control and rings, but each bit keeps its
  column, sense amplifier and write driver.

### 4.2 Total area of the transmitter

`btle_tx` std-cell area (§ 3.1) plus its macros. The two estimated rows are
not built: they add the measured change of `ble-tx-sin8` (+702.5 µm² of
logic, one 512 × 16 table memory) to another branch, which § 3.2 justifies for
changes in different blocks.

| Branch | `btle_tx` cells (µm²) | Gaussian-table macros | COS + SIN macros | PDU buffer | **Total, 1RW1R (µm²)** | vs `master` | Total, 1RW (µm²) | vs `master` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `master` / `risc-v-ble` | 5 322.9 | — | 138 700.5 | 23 708.0 | **167 731.4** | — | 79 667.6 | — |
| `ble-tx-table` | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 734.1** | −1.8 % | 76 670.3 | −3.8 % |
| `ble-tx-table-reg` | 25 201.6 | — | 138 700.5 | 23 708.0 | **187 610.1** | +11.9 % | 99 546.3 | +25.0 % |
| `ble-tx-table-sram` | 4 434.5 | 18 437.4 | 138 700.5 | 23 708.0 | **185 280.4** | +10.5 % | 97 216.6 | +22.0 % |
| `ble-tx-fir2` | 4 295.9 | — | 138 700.5 | 23 708.0 | **166 704.4** | −0.6 % | 78 640.6 | −1.3 % |
| **`ble-tx-sin4`** | 5 427.7 | — | **47 415.9** | 23 708.0 | **76 551.6** | **−54.4 %** | 37 539.4 | **−52.9 %** |
| **`ble-tx-sin8`** | 6 025.4 | — | **37 703.9** | 23 708.0 | **67 437.3** | **−59.8 %** | 33 844.0 | **−57.5 %** |
| `ble-rx-dm` | 5 328.2 | — | 138 700.5 | 23 708.0 | **167 736.7** | 0 | 79 672.9 | 0 |
| `ble-opt` | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 734.1** | −1.8 % | 76 670.3 | −3.8 % |
| *estimate: `ble-tx-sin8` + `ble-tx-table`* | *3 028.1* | — | *37 703.9* | *23 708.0* | *64 440.0* | *−61.6 %* | *30 846.7* | *−61.3 %* |
| *estimate: `ble-tx-sin8` + `ble-tx-fir2`* | *4 998.4* | — | *37 703.9* | *23 708.0* | *66 410.3* | *−60.4 %* | *32 817.0* | *−58.8 %* |

### 4.3 What the total says

1. **The transmitter is its memories.** In `master` the three RAMs are 96.8 %
   of the transmitter's area (93.3 % with single-port macros). The Gaussian
   filter, the block that five of the branches work on, is 2 % of it.
2. **`ble-tx-sin4` halves the transmitter.** It adds 104.8 µm² of logic and
   removes 91 284.6 µm² of macros (42 233.0 µm² with single-port macros): the
   transmitter goes from 167 731 to 76 552 µm², −54.4 % (−52.9 % with 1RW).
   That is 30 times the saving of B2 on the same block, and more than the whole
   cell area of the `ble-opt` controller (26 681 µm²). Its price is not area
   but function: the COS/SIN tables must have quarter-wave symmetry (§ 8).
3. **`ble-tx-sin8` takes another 11.9 % off.** Once the tables are small, the
   periphery is most of each macro, so the next step was fewer macros, not
   fewer bits: the two quarter tables, always read at the same address, share
   one 512 × 16 macro. It saves 9 712.0 µm² of macro for 597.7 µm² of logic
   (the shared write port), and the transmitter goes to 67 437 µm², −59.8 %
   against `master` (−57.5 % with 1RW). Its price is a limit on how fast the
   two tables can be written together (§ 8).
4. **The Gaussian-filter options hardly move the real total.** B2 saves
   1.8 % of the transmitter (3.8 % with 1RW), the folded FIR 0.6 %, and the
   rewritable tables add 10 to 12 % (22 to 25 % with 1RW).
   `GAUSS_FILTER_OPTIONS.md` ranks them right within the filter; this puts the
   filter in scale.
5. **The two kinds of change add.** `ble-tx-sin4` and `ble-tx-sin8` touch only
   `vco.v`, the Gaussian branches only the filter. With B2, `ble-tx-sin8`'s
   transmitter would be about 64 440 µm² (−61.6 %); with the folded FIR, which
   keeps the taps programmable, about 66 410 µm² (−60.4 %).

## 5. Static timing

`scripts/timing/run_sta.sh` with `STA_SET=controller`: the netlist of the area
flow, flip-flops and RAM macros cut to a register-to-register network, fanout
legalised (maximum 16) and gates sized, ABC `stime`, and the worst liberty
clock-to-Q and setup added. Results in
[`results/timing/all-branches/`](../../results/timing/all-branches/),
[`results/timing/tx-variants/`](../../results/timing/tx-variants/) and
[`results/timing/tx-sin8/`](../../results/timing/tx-sin8/).
Target: the 16 MHz baseband clock, 62.5 ns.

| | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.546 ns | 6.479 ns | 7.115 ns | 6.408 ns | 7.081 ns | 6.251 ns | 3.913 ns | 4.044 ns |
| Logic path (buffered, sized) | 1.631 ns | 1.546 ns | 1.636 ns | 1.652 ns | 1.517 ns | 1.647 ns | 1.550 ns | 1.475 ns | 1.597 ns |
| Register overhead | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.347 ns |
| **Min period** | **1.991 ns** | **1.905 ns** (−4.3 %) | **1.995 ns** (+0.2 %) | **2.011 ns** (+1.0 %) | **1.877 ns** (−5.7 %) | **2.007 ns** (+0.8 %) | **1.910 ns** (−4.1 %) | **1.834 ns** (−7.9 %) | **1.944 ns** (−2.4 %) |
| Slack at 62.5 ns | +60.509 ns | +60.595 ns | +60.505 ns | +60.489 ns | +60.623 ns | +60.493 ns | +60.590 ns | +60.666 ns | +60.556 ns |
| Fmax | 502.3 MHz | 524.9 MHz | 501.2 MHz | 497.2 MHz | 532.8 MHz | 498.3 MHz | 523.6 MHz | 545.3 MHz | 514.3 MHz |
| Flip-flops / gates timed | 4 578 / 45 716 | 4 422 / 43 804 | 7 222 / 50 868 | 4 667 / 44 656 | 4 570 / 45 049 | 4 581 / 45 815 | 4 656 / 46 059 | 3 926 / 19 419 | 2 673 / 13 428 |
| Worst path | demodulator multiply, copy 2 | Link Layer `timestamp` | demodulator multiply, copy 2 | demodulator multiply, copy 6 | demodulator multiply, copy 3 | demodulator multiply, copy 6 | Link Layer `timestamp` | shared demodulator multiply | Link Layer `timestamp` |

The worst paths in full:

- demodulator multiply: `btle_phy_i.btle_rx_i.genblk1[k].btle_rx_core_i.gfsk_demodulation_i.i1[5]`
  (`master`) or `…i0[6]` / `…i0[4]` (the transmitter branches) →
  `…signal_for_decision[31]`, in one of the 8 upstream demodulator copies;
- shared demodulator multiply (`ble-rx-dm`): `gfsk_demodulation_shared_i.old_q[7]` →
  `signal_for_decision[30]`;
- Link Layer `timestamp` (`ble-tx-table`, `ble-tx-sin8`, `ble-opt`):
  `btle_ll_i…write_data[16]` → `[76]`, the 64-bit `timestamp` counter.

What can be said, and what cannot:

1. **Every branch closes 16 MHz with a factor of about 31 in hand**
   (1.83–2.01 ns of a 62.5 ns period). None of the changes makes timing a
   constraint.
2. **No change lengthens the critical path.** Sharing the demodulator (B1) does
   not: `ble-rx-dm` has the shortest period of all, because the sharing is
   in time, not in logic depth. None of the transmitter branches puts the
   worst path in the transmitter: it stays the multiply of one of the 8
   upstream demodulators or, on `ble-tx-sin8`, the Link Layer's `timestamp`
   counter, as on `ble-tx-table`.
3. **Differences below about 0.15 ns are flow noise, not design effects.** The
   worst path of four transmitter branches is the same upstream RTL, the
   demodulator multiply, and it times anywhere from 1.877 ns (`ble-tx-fir2`)
   to 2.011 ns (`ble-tx-table-sram`), against 1.991 ns on `master`. Likewise
   the `timestamp` counter of `btle_ll` is the same RTL on `master`,
   `ble-tx-table` and `ble-rx-dm`, yet it times at 1.546 ns in the
   `ble-tx-table` netlist, where it is the worst path, and at most 1.475 ns in
   the `ble-rx-dm` one. Buffering and sizing are heuristics over the whole
   netlist, so ranking the branches within 0.15 ns means nothing.
4. The unbuffered column only shows that Yosys builds no buffer trees
   (explained in `STATIC_TIMING.md` on `ble-opt`); it is kept for completeness.

## 6. Switching activity

### 6.1 Method

`scripts/power/run_activity.sh`, the harness of `SWITCHING_ACTIVITY.md` on
`ble-opt`, once per branch. Results in
[`results/power/all-branches/`](../../results/power/all-branches/),
[`results/power/tx-variants/`](../../results/power/tx-variants/) and
[`results/power/tx-sin8/`](../../results/power/tx-sin8/).

- Both **gate-level** netlists, upstream and the branch, run side by side in one
  Verilator simulation per scenario, and every output is compared on every
  clock. For every branch except `ble-opt`, which removes three outputs on
  purpose, the comparison covers **every** output and every register read
  (`FULL_COMPARE`). **No mismatch in any scenario, on any branch, except one
  expected case.** On `ble-tx-table-reg` and `ble-tx-table-sram` the `tx`
  scenario stops at its first packet, 210 clocks into the window, on a
  difference at the Gaussian filter output. That scenario starts transmitting
  as soon as the setup has written the taps, and these two branches rebuild
  their tables for 928 clocks after a tap write (§ 8). This is their
  specified behaviour, not a fault: every other scenario is identical on every
  clock, `mixed` included, which transmits 8 packets later in the window, and
  so is their controller lockstep, which waits for the rebuild (§ 7). Their
  `tx` scenario is therefore not measured, and the summary of run
  `tx-variants` lists these two failed checks.
- Five scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`), each a window of
  exactly 100 000 `bb_clk` cycles after the same setup, which is subtracted.
- **One vector set for every branch** (`vectors.tar.gz`, example 0 of the
  Python model, 20 dB, 20 ppm). The generator's channel noise is not seeded;
  a first attempt of run `all-branches` generated vectors per branch, so each
  branch saw a different packet noise, and it was stopped and repeated with
  one set. Runs `tx-variants` and `tx-sin8` reused that set (the same
  `vectors.sha256`).
- Measures, as on `ble-opt`: toggles per net where it is driven; nets with a
  toggle rate > 0.1; and the **switched-capacitance proxy** Σ toggles × liberty
  input-pin capacitance, split into data pins and flip-flop `CK` pins. No
  wires, no clock tree, no internal energy, no leakage.

The upstream side of every run is the same design on the same stimulus, and
it comes out identical in every configuration: within each run the summary
checks it, and between the runs `master` gives the same counts and the
same capacitance sums to 10⁻¹⁴. `master` against upstream shows no
difference at all, in any run (the consistency checks at the end of
[`all-branches/summary.md`](../../results/compare/all-branches/summary.md),
[`tx-variants/summary.md`](../../results/compare/tx-variants/summary.md) and
[`tx-sin8/summary.md`](../../results/compare/tx-sin8/summary.md)). The
scenarios that do not use the packet vectors (`tx`, `idle`, `idle0`) also
reproduce the earlier `ble-opt` run `sticker-vs-upstream` exactly, every count
of every block, upstream and reduced alike; `rx` and `mixed` cannot, because
that run's vectors were not kept.

### 6.2 Data + clock switched capacitance, every scenario

| Scenario | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rx` | 1.23 × 10⁹ fF | −2.4 % | +40.8 % | +1.4 % | −0.1 % | 0 | +1.2 % | −12.9 % | **−33.2 %** |
| `tx` | 1.00 × 10⁹ fF | −5.0 % | — | — | −1.1 % | +0.4 % | +1.8 % | −8.0 % | **−34.7 %** |
| `mixed` | 1.25 × 10⁹ fF | −3.2 % | +40.8 % | +0.6 % | −0.5 % | +0.1 % | +1.3 % | −9.5 % | **−30.3 %** |
| `idle` | 1.26 × 10⁹ fF | −2.3 % | +39.9 % | +1.4 % | −0.1 % | 0 | +1.2 % | −5.9 % | **−25.5 %** |
| `idle0` | 0.95 × 10⁹ fF | −3.1 % | +53.0 % | +1.8 % | −0.1 % | 0 | +1.5 % | −8.5 % | **−34.4 %** |

### 6.3 The measures of `SWITCHING_ACTIVITY.md`, scenario `mixed`, every branch

| Measure | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Toggles / cycle, non-clock nets | 984.3 | 956.4 (−2.8 %) | 988.0 (+0.4 %) | 958.7 (−2.6 %) | 971.0 (−1.4 %) | 987.0 (+0.3 %) | 989.4 (+0.5 %) | 1 004.5 (+2.1 %) | 939.7 (−4.5 %) |
| Nets with activity > 10 % | 839 | 827 | 836 | 824 | 841 | 851 | 845 | 4 002 (×4.8) | 3 908 (×4.7) |
| `btle_rx` toggles / cycle | 791.1 | 790.6 | 788.2 | 788.9 | 791.4 | 788.8 | 791.0 | 811.5 (+2.6 %) | 808.8 (+2.2 %) |
| `btle_ll` toggles / cycle | 41.5 | 40.6 | 41.6 | 41.9 | 42.7 | 41.1 | 42.2 | 41.7 | 11.0 (**−73.4 %**) |
| Gaussian filter toggles / cycle | 39.1 | 12.6 (**−67.8 %**) | 45.6 (+16.4 %) | 15.4 (**−60.8 %**) | 24.2 (**−38.1 %**) | 39.1 | 39.1 | 39.1 | 12.3 (**−68.6 %**) |
| Rest of `btle_tx` (VCO, packet path) toggles / cycle | 37.4 | 37.4 | 37.4 | 37.4 | 37.4 | 42.8 (+14.4 %) | 42.0 (+12.1 %) | 36.9 | 37.7 |
| Clock network (CK-pin load × toggles) | 8.76 × 10⁸ | −3.4 % | **+57.3 %** | +1.9 % | −0.2 % | +0.1 % | +1.7 % | −14.1 % | **−41.4 %** |
| Memory: toggles on RAM ports | 3 044 741 | unchanged | unchanged | +10.8 % | unchanged | −0.4 % | −0.4 % | unchanged | **−40.0 %** |
| Data load × toggles | 3.73 × 10⁸ | −2.8 % | +1.8 % | −2.5 % | −1.2 % | +0.2 % | +0.4 % | +1.5 % | −4.3 % |
| **Data + clock proxy** | 1.25 × 10⁹ | **−3.2 %** | **+40.8 %** | **+0.6 %** | **−0.5 %** | **+0.1 %** | **+1.3 %** | **−9.5 %** | **−30.3 %** |

The full tables (every scenario, every block, the most active nets) are in
[`all-branches/summary.md`](../../results/compare/all-branches/summary.md),
[`tx-variants/summary.md`](../../results/compare/tx-variants/summary.md)
and in each branch's `results/power/<run>/<branch>/summary.md`.

### 6.4 The activity savings add up too

A1 and A2 have no branch of their own, but they act only on `btle_ll` and
`auxiliary_daemon`, so their share can be measured on those two blocks of
`ble-opt` against `master`. In points of the upstream data + clock proxy:

| Scenario | B2 (`ble-tx-table`) | B1 (`ble-rx-dm`) | A1 + A2 (their blocks) | Sum | `ble-opt` | Residual |
|---|---:|---:|---:|---:|---:|---:|
| `rx` | −2.4 | −12.9 | −17.9 | −33.2 | −33.2 | 0.0 |
| `tx` | −5.0 | −8.0 | −21.6 | −34.7 | −34.7 | 0.0 |
| `mixed` | −3.2 | −9.5 | −17.6 | −30.3 | −30.3 | 0.0 |
| `idle` | −2.3 | −5.9 | −17.2 | −25.4 | −25.5 | −0.1 |
| `idle0` | −3.1 | −8.5 | −22.8 | −34.4 | −34.4 | 0.0 |

Each change acts only on its own block: on `ble-tx-table` only the Gaussian
filter's proxy moves (−79.8 % in `mixed`), on `ble-rx-dm` only `btle_rx`'s
(−16.6 %); every other block stays within 1 %. The five transmitter branches
behave the same way: only their own block moves the proxy by more than 0.1
point, the Gaussian filter on `ble-tx-table-reg` (+40 to +53 points),
`ble-tx-table-sram` (+0.6 to +1.8) and `ble-tx-fir2` (−0.1 to −1.1), and the
rest of `btle_tx`, which holds the VCO, on `ble-tx-sin4` (at most +0.4) and
`ble-tx-sin8` (+1.2 to +1.9).

### 6.5 What each change does to activity

- **B2, Gaussian table.** The filter switches 68 % less (79.1 → 25.4 toggles per
  cycle while transmitting) and loses 156 of its 178 clocked flip-flops. It
  only works while transmitting, so the gain is largest in `tx` (−18.7 % of all
  non-clock toggles, −5.0 % of the proxy) and in `idle` it is the clock pins
  alone (−2.3 %).
- **Gaussian table in flip-flops (`ble-tx-table-reg`).** Its 2 560 table
  flip-flops are clocked on every cycle and Nangate45 has no clock gating, so
  the clock-pin load rises 57 % in every scenario, transmitting or not, and the
  proxy 40 to 53 %. Data switching hardly moves (+0.4 % of the toggles in
  `mixed`). Clock gating would remove most of this cost, but not the area
  (§§ 3, 4).
- **Gaussian table in SRAM (`ble-tx-table-sram`).** The filter switches 61 %
  less (`mixed`), but it has 89 more flip-flops than the FIR (clock pins
  +1.9 %) and the table reads add 6.6 to 10.8 % to the RAM-port toggles. The proxy
  rises 0.6 to 1.8 %, and it does not count the SRAM's own read energy.
- **Folded FIR (`ble-tx-fir2`).** The filter switches 38 % less while
  transmitting (79.1 → 49.1 toggles per cycle in `tx`) and has 8 fewer
  flip-flops: −1.1 % of the proxy in `tx`, about −0.1 % without traffic.
- **Quarter-wave VCO tables (`ble-tx-sin4`).** The address reflection and the
  sign logic make the rest of the transmitter switch 16 % more while
  transmitting (68.0 → 78.8 toggles per cycle in `tx`), +0.4 % of the proxy;
  without traffic nothing changes. The RAM ports toggle 1 % less (9 address
  bits instead of 11). The proxy does not see the memories themselves:
  OpenRAM's analytical model puts the leakage of a 512 × 8 dual-port macro at
  4.9 µW against 17.7 µW for 2 048 × 8, a model figure, not a measurement.
- **One {cos, sin} memory (`ble-tx-sin8`).** Its write port adds 75
  flip-flops clocked on every cycle (the previous register pairs and the
  queues), so the clock-pin load rises 1.7 % in every scenario and the proxy
  1.2 to 1.8 %. The rest of the transmitter switches as on `ble-tx-sin4`
  (68.0 → 77.1 toggles per cycle in `tx`), and so do the RAM ports. In
  OpenRAM's model the one 512 × 16 dual-port macro leaks 9.0 µW, against
  2 × 4.9 µW for the two 512 × 8 of `ble-tx-sin4`.
- **B1, shared demodulator.** It removes 652 flip-flops (−14 % of the clock
  load, the same in every scenario). With real packets (`rx`) the receiver also
  switches less (`btle_rx` −10.2 %). With no traffic it switches **more**:
  `btle_rx` +16 % in `idle` and +125 % in `tx` (receiver input zero). The nets
  above 10 % activity grow ×4.8 in `mixed` and ×6.7 in `idle`. As found on
  `ble-opt`, this is the shared unit's valid/enable network, which toggles on
  every sample whatever the data. The proxy still falls in every scenario
  (−5.9 to −12.9 %) because the clock pins dominate it.
- **A1 + A2, debug infrastructure.** They give the largest activity saving
  (−17 to −23 points), although they are only 15 % of the cells saved. The
  full Link Layer holds 44 % of the upstream flip-flops (2 036 of 4 578), all
  clocked on every cycle, and makes 32 % of the upstream proxy; the minimal one
  switches 73 % less. The IQ-capture RAM, written on every 16 MHz cycle, is
  gone (RAM-port toggles −25 to −48 %, depending on the scenario).

The ranking by activity (A1 + A2, then B1, then B2) is not the ranking by area
(B1, then A1 + A2, then B2): cells that are clocked on every cycle cost switching
whatever the traffic, and the debug infrastructure is exactly that.

## 7. Evidence per branch

Every branch that changes the RTL has its own proof that nothing needed was
lost, plus the gate-level lockstep of these runs (§ 6.1), in which every output
of the synthesised netlist is compared with upstream on every clock.

| | `ble-tx-table` (B2) | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---|---|---|
| Formal proof of the change | table ≡ upstream FIR, **unbounded** (k-induction), 3/3 mutants rejected | shared ≡ the 8 upstream demodulators, **unbounded at 16 bits**, 4/4 mutants rejected | both proofs (B1, B2) |
| Defaults ≡ original (formal, per module) | 5 modules against `upstream-baseline` (96 609 `$equiv` cells for the controller) | — (B1 is not optional) | 7 modules against `88f2250` |
| Lockstep against upstream | controller through the registers, `GAUSS_TABLE=1`: 15/15, 923 385 clocks, **every output and register**, 4/4 mutants | `btle_rx`: 60/60, 25 367 270 clocks, 4/4 mutants | controller through the registers: 15/15, 923 385 clocks (removed outputs skipped), 3/3 mutants |
| Upstream testbenches, 270 runs | 270/270 identical **with the table on** | 270/270 identical | 270/270 identical (defaults) |
| Gate-level lockstep, run `all-branches` | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches |
| Report | `docs/04 Validation/TX_TABLE_VALIDATION.md` | `docs/04 Validation/SHARED_DEMOD_VALIDATION.md` | `SHARED_DEMOD_VALIDATION.md`, `STICKER_REDUCTIONS_VALIDATION.md` |

| | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` |
|---|---|---|---|---|---|
| Formal | defaults ≡ upstream: `gauss_filter`, `gfsk_modulation`, `btle_tx` | the same | pair identity at 16 bits; whole filter ≡ upstream for any taps and any input, unbounded, at 4 bits; 3/3 mutants | — | — |
| Random lockstep, module level | 4 seeds × 200 random tap sets × 5 000 clocks; 2/2 mutants | the same; 4/4 mutants | 4 seeds × 2 000 000 clocks, 1 001 125 random tap writes | `vco` against the `master` VCO, both full tables loaded: all 2 048 phase addresses, phase jumps, gaps, a reset; 3 072 clocks, no mismatch (`tests/test_vco_sin4.py`) | `vco` against the `ble-tx-sin4` VCO: 4 seeds × 1 000 000 clocks of random writes to both tables (same and different addresses in one clock, streams, resets), reads aimed at the entries just written, 2 919 121 comparisons, no mismatch; 7/7 mutants. And the sweep of `test_vco_sin4.py` against `master` (`tests/test_vco_sin8.py`) |
| Controller through the registers | 15/15 runs, 90 random tap sets reprogrammed in flight, 930 629 clocks, every output and register; 4/4 mutants | 15/15 runs, 927 488 clocks; 6/6 mutants | — | — | — |
| Upstream testbenches, 270 runs | 270/270 identical with the table on | 270/270 identical with the table on | 270/270 identical | — | — |
| Gate-level lockstep, runs `tx-variants` and `tx-sin8` | 4/5 scenarios, 0 mismatches; `tx` transmits before the 928-clock rebuild (§ 6.1) | the same | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches, with the full 2 048-entry tables written as the firmware writes them (25 packets sent) | 5/5 scenarios, 0 mismatches, with the full tables written as the firmware writes them (25 packets sent) |
| Report | `GAUSS_FILTER_OPTIONS.md` § 7 | `GAUSS_FILTER_OPTIONS.md` § 7 | `GAUSS_FILTER_OPTIONS.md` § 7 | `TX_SIN4_COMPARISON.md` (on `ble-tx-sin4`) | `TX_SIN8_COMPARISON.md` (on `ble-tx-sin8`) |

## 8. What each branch gives up

| Branch | Functions removed |
|---|---|
| `master`, `risc-v-ble` | none (the reference) |
| `ble-rx-dm` | **none**: B1 is an exact rewrite; the 8 phase hypotheses and the CRC-based selection are kept |
| `ble-tx-fir2` | **none**: an exact rewrite; the taps stay programmable through register 1 and apply on the next clock |
| `ble-tx-table-reg`, `ble-tx-table-sram` | none, but after a tap write the tables need 928 clocks (58 µs) to be rebuilt before the next transmission |
| `ble-tx-sin4` | the independent programming of the whole COS/SIN tables: only addresses 0–511 of each are stored and the rest follows by quarter-wave symmetry, so a table without that symmetry can no longer be loaded (the project's tables have it, § 6.1) |
| `ble-tx-sin8` | the same as `ble-tx-sin4`, and the two tables share one write port: their writes must not back up by more than one, at most w + 1 table writes in any w consecutive clocks (two writes to the same address in one clock count as one), where upstream accepts two per clock. Within that, the outputs differ only if the VCO reads an entry in the clock after its write had to wait, which means rewriting both tables while transmitting. The firmware writes one table at a time, a register write every few clocks |
| `ble-tx-table` | the runtime change of the Gaussian taps (register 1): the taps become a synthesis parameter |
| `ble-opt` | the runtime Gaussian taps; the IQ capture (`btle_ll -q`); the UART HCI; the 1 PPS input; the latency statistic of `btle_ll.c`; removed registers read 0 |

## 9. Conclusions

1. **B1 is the change that matters for logic.** On its own it removes 53.6 %
   of the controller's cells, 79 % of all that `ble-opt` saves, costs no
   function and does not slow the design. B2 is a small exact gain (−4.1 %)
   that costs the runtime-programmable taps.
2. **For the transmitter, memory matters more than any logic change.** With
   its SRAM macros counted, the COS/SIN tables and the packet buffer are 97 %
   of the transmitter. `ble-tx-sin4` halves it (−54.4 %, 91 180 µm²) for
   104.8 µm² of logic, 30 times what B2 saves there; B2 and the folded FIR save
   1.8 % and 0.6 %. `ble-tx-sin4` only looked larger (+2.0 % of cell area)
   because the flow does not count the memory it removes. `ble-tx-sin8`, with
   one memory for both quarter tables, is the smallest transmitter measured:
   67 437 µm², −59.8 % against `master` and −11.9 % against `ble-tx-sin4`.
   Their cost is function, not area: the tables must have quarter-wave
   symmetry, which the project's tables have (identical outputs, § 6.1), and on
   `ble-tx-sin8` the two tables cannot be written faster than one entry per
   clock between them, with one of slack (§ 8).
3. **All the memory saving of `ble-opt` is debug infrastructure.** Neither B1
   nor B2 touches the SRAM; A1 and A2 remove 92.3 % of its bits, almost all of
   them the 1 Mbit IQ-capture RAM.
4. **The rewritable Gaussian tables are the worst transmitter options on
   every measure**: +10.5 to +11.9 % of the transmitter's real area, the
   flip-flop table +40 to +53 % of the switching proxy, and 928 clocks after a
   tap write. If the taps must stay programmable, the folded FIR is the
   choice (`GAUSS_FILTER_OPTIONS.md`).
5. **The changes are independent.** Area adds up to within 7 cells (and
   exactly in flip-flops), switching activity to within 0.1 point in every
   scenario, and each transmitter branch moves only its own block. Any
   subset can be combined with a predictable result; `ble-tx-sin8` with B2 is
   estimated at −61.6 % of the transmitter, and with the folded FIR, which
   keeps the taps programmable, at −60.4 %.
6. **Activity ranks the changes differently from area.** The debug
   infrastructure (A1 + A2) gives most of the 25–35 % proxy reduction, because
   it is logic clocked on every cycle; B1 lowers the clock load but raises data
   switching when the receiver has no traffic; B2 matters only while
   transmitting.
7. **Timing does not separate the branches.** All ten close 16 MHz with a
   factor of about 31, none of the transmitter branches puts the worst path in
   the transmitter, and the differences between them are within the flow's
   noise.

## 10. What this does not claim

- **No FPGA, no silicon, no power.** Area and timing are pre-layout (ideal
  wires, ideal clock, setup only, RAM macros not timed). Switching activity is
  a pin-capacitance proxy with no wires, no clock tree, no internal energy and
  no leakage, from zero-delay simulation, which does not count glitches.
- **The SRAM macros of § 4 are OpenRAM layouts in FreePDK45**, an academic
  PDK, generated without DRC/LVS and never placed with the logic. A commercial
  compiler would be denser, and its small macros relatively more so. Only the
  transmitter's RAMs are converted to area. The receiver's are the same on
  every branch, and the RAMs that `ble-opt` removes (the IQ-capture RAM, the
  Link Layer crossings) are counted in bits only.
- **One stimulus set** for activity (example 0 of the Python model, seed 1,
  100 000 cycles per scenario).
- **The resolution of the method.** The same block, with the same RTL and the
  same stimulus, can differ by up to about 3 % between two netlists
  (`btle_ll` toggles −2.0 % on `ble-tx-table`, whose Link Layer is the upstream
  RTL mapped to 29 fewer cells, and +3.0 % on `ble-tx-fir2`), and timing by up
  to about 0.15 ns (§ 5).
- **A1 and A2 are not isolated in a branch of their own**; their share is
  measured on their own blocks, and §§ 3.2 and 6.4 show it is consistent with
  the totals.
- **`ble-tx-sin8` combined with a Gaussian-filter branch is not built**; § 4
  estimates it from the parts.
- **The {cos, sin} memory of `ble-tx-sin8` is checked by simulation**, at
  module level against `ble-tx-sin4` and at gate level against upstream, not
  by a formal proof: the write port's contract (§ 8) is exercised, not
  proved.

## 11. Reproducing

From WSL, at the root of `ble-opt`, `ble-tx-table` or `ble-rx-dm`. The
harness is the same set of files on the three branches, and it reads every
branch through `git archive`, so the branch checked out does not matter:

```bash
scripts/compare/run_compare.sh <label>                          # about 1 h, master, ble-tx-table, ble-rx-dm, ble-opt
scripts/compare/run_compare.sh <label> master ble-tx-table-reg ble-tx-table-sram ble-tx-fir2 ble-tx-sin4
scripts/compare/run_compare.sh <label> master ble-tx-sin8
# the activity of these runs exactly: reuse their vectors
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> [name ...]
# the SRAM macros of § 4, about 20 + 10 min (OpenRAM in its own environment, see the script)
scripts/area/run_openram.sh <label> sram_1rw_8x2048 sram_1rw1r_8x2048 sram_1rw_8x512 sram_1rw1r_8x512
scripts/area/run_openram.sh <label> sram_1rw1r_16x512_m8 sram_1rw_16x512_m8
```

The first name is the reference of the summary, so it must be `master`. The
script refuses to overwrite a label. It records, per configuration, the
revision, commit, `verilog/` tree and parameters in `provenance.txt`
([`all-branches`](../../results/compare/all-branches/provenance.txt),
[`tx-variants`](../../results/compare/tx-variants/provenance.txt),
[`tx-sin8`](../../results/compare/tx-sin8/provenance.txt)), writes
`summary.md` and `data.json`, and fails if a consistency check fails. Area and
timing take about a minute; activity about 15 minutes per configuration.

Run `all-branches`' own summariser (`f540e99`) compared the capacitance sums of the
upstream side bit for bit and flagged them, although every count was
identical: the sums differ by about 10⁻¹⁵ relative, because `saif_activity.py`
adds them in Python-set order, which changes from one process to the next.
`696b036` compares counts exactly and sums to 10⁻⁹; the summary was
regenerated from the same measurements with it, and every check passes. No
measurement was repeated or changed.
