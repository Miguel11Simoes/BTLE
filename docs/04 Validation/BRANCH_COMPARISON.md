# Comparison of the branches: upstream, B2 alone, B1 alone and `ble-opt`

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** every branch carries this same file (`master`, `risc-v-ble`, `ble-tx-table`, `ble-rx-dm`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-28  
**Author:** Miguel Simões  
**Status:** executed: run `all-branches`, harness `scripts/compare/` at `f540e99` (summary
regenerated at `696b036`, § 10). Pre-layout area and static timing; gate-level switching
activity, which is a proxy and **not power**.

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

Two new branches isolate the signal-processing changes: `ble-tx-table` holds
only B2 and `ble-rx-dm` only B1. This document measures every branch with the
same ruler, in one run, and answers three questions: what each change buys on
its own, whether the changes add up, and what each one costs in function.

This file is identical on every branch. The raw results it cites are in
`results/compare/all-branches/` and in the per-configuration folders
`results/{area,timing,power}/all-branches/`, which exist on `ble-opt`,
`ble-tx-table` and `ble-rx-dm`; the relative links below resolve there.

## 1. The branches

| Branch | What it is | RTL (`verilog/`) against upstream | Measured as |
|---|---|---|---|
| `master` | upstream BTLE at tag `upstream-baseline` (`8540186`) | the reference; tree `4bacca3` | defaults |
| `risc-v-ble` | `master` + the thesis documentation | **identical**: same tree `4bacca3` | same as `master` |
| `ble-tx-table` | B2 alone | 5 RTL files and the testbench fix U9; tree `2d36551` | `GAUSS_TABLE=1` |
| `ble-rx-dm` | B1 alone | `btle_rx.v`, `btle_rx_core.v`, new `gfsk_demodulation_shared.v`, file lists, U9; tree `aa807f8` | defaults (B1 is not a parameter) |
| `ble-opt` | B1 + B2 + A1 + A2, plus the model-update firmware | 11 RTL files (1 new), the Vivado file list, 2 testbenches; tree `b78aa37` | `ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1` |

How they relate:

```
master  (= upstream-baseline, 8540186)
 └─ risc-v-ble                   70cab42, 3e3086e: documentation only
     └─ 74bb17c, 69c8b51         area flow; upstream baseline measured
         ├─ ble-tx-table         + B2 alone (dfcc15c), U9 (4c8d66a), its validation
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
the B2 lines of `39f5851`.

A branch is measured in **its configuration: every optional reduction its
`btle_controller` declares, switched on** (`scripts/branch_config.sh`). The
parameters default to the original design on every branch, so the Vivado flow
of the boards sees upstream unless it asks otherwise; B1 is the exception,
because it is structural.

## 2. The comparison

Differences are against `master`. `risc-v-ble` has the same `verilog/` tree
as `master`, so its figures are the same by construction: the flows are
deterministic for identical inputs, and `master` itself reproduces the
committed `baseline-upstream` area run exactly.

| | `master` | `risc-v-ble` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---|---|---|---|---|
| **Content** | upstream BTLE | `master` + thesis docs | **B2** | **B1** | **B1 + B2 + A1 + A2** |
| Configuration measured | defaults | defaults | `GAUSS_TABLE=1` | defaults | `ENABLE_IQ_CAPTURE=0`, `LL_MINIMAL=1`, `GAUSS_TABLE=1` |
| GFSK demodulators in `btle_rx` | 8 | 8 | 8 | **1, shared** | **1, shared** |
| Gaussian filter | FIR, runtime taps | FIR, runtime taps | **fixed-tap table** | FIR, runtime taps | **fixed-tap table** |
| IQ-capture debug RAM (1 Mbit) | yes | yes | yes | yes | **removed** |
| Link Layer | full | full | full | full | **minimal** |
| **Std cells, `btle_controller`** | 50 295 | 50 295 | 48 227 (−4.1 %) | 23 346 (−53.6 %) | **16 102 (−68.0 %)** |
| Flip-flops | 4 578 | 4 578 | 4 422 (−3.4 %) | 3 926 (−14.2 %) | 2 673 (−41.6 %) |
| Cell area (µm²) | 71 706 | 71 706 | 68 667 (−4.2 %) | 38 782 (−45.9 %) | 26 681 (−62.8 %) |
| **SRAM bits** | 1 136 070 | 1 136 070 | 1 136 070 | 1 136 070 | **87 046 (−92.3 %)** |
| Min period at 16 MHz (62.5 ns) | 1.991 ns | 1.991 ns | 1.905 ns | 1.834 ns | 1.944 ns |
| Slack / Fmax | +60.509 ns / 502 MHz | same | +60.595 ns / 525 MHz | +60.666 ns / 545 MHz | +60.556 ns / 514 MHz |
| Worst path | demodulator multiply, one of 8 copies | same | Link Layer 64-bit timestamp | shared demodulator multiply | Link Layer 64-bit timestamp |
| **Data + clock switched capacitance, `mixed`** | 1.25 × 10⁹ fF | same | −3.2 % | −9.5 % | **−30.3 %** |
| … over the 5 scenarios | — | — | −2.3 to −5.0 % | −5.9 to −12.9 % | −25.5 to −34.7 % |
| Clock pins (load × toggles) | 8.76 × 10⁸ fF | same | −3.4 % | −14.1 % | −41.4 % |
| Non-clock toggles / cycle, `mixed` | 984.3 | same | 956.4 (−2.8 %) | 1 004.5 (+2.1 %) | 939.7 (−4.5 %) |
| Nets with activity > 10 %, `mixed` | 839 | same | 827 | 4 002 (×4.8) | 3 908 (×4.7) |
| RAM-port toggles, `mixed` | 3 044 741 | same | unchanged | unchanged | −40.0 % |
| Functions removed | — | — | runtime Gaussian taps | **none** | runtime taps, IQ capture, UART HCI, 1 PPS, latency counter |
| Gate-level outputs vs upstream, 5 scenarios | — | — | identical, every output | identical, every output | identical, except the 3 removed outputs |

## 3. Area

Same flow as every earlier run: Yosys 0.68, `synth -flatten`, `dfflibmap`,
`abc -liberty`, Nangate45, SRAMs blackboxed and counted in bits. All 16 tops
were synthesised for each branch; results in
[`results/area/all-branches/`](../../results/area/all-branches/). Every
configuration reproduces its earlier area run top for top, all 16 identical:
`master` = `baseline-upstream`, `ble-tx-table` = `tx-table`, `ble-rx-dm` =
`shared-demod`, `ble-opt` = `sticker`.

### 3.1 Per block (std cells, each top synthesised alone)

| Top | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|
| `gauss_filter` | 2 286 | **253** (−88.9 %) | 2 286 | **253** (−88.9 %) |
| `btle_tx` | 3 409 | **1 392** (−59.2 %) | 3 411 | **1 392** (−59.2 %) |
| `btle_rx` | 36 864 | 36 884 | **10 068** (−72.7 %) | **10 068** (−72.7 %) |
| `btle_phy` | 40 339 | 38 083 (−5.6 %) | 13 536 (−66.4 %) | 11 394 (−71.8 %) |
| `auxiliary_daemon` | 299 | 299 | 299 | **233** (−22.1 %) |
| `btle_ll` | 9 453 | 9 453 | 9 453 | **4 336** (−54.1 %) |
| **`btle_controller`** | **50 295** | **48 227** (−4.1 %) | **23 346** (−53.6 %) | **16 102** (−68.0 %) |

Each change moves only its own block. The small moves elsewhere (`btle_rx`
36 864 → 36 884 on `ble-tx-table`, `btle_tx` 3 409 → 3 411 on `ble-rx-dm`)
are the flow noise already recorded on `ble-opt`: ABC's result depends on
everything Yosys reads.

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

### 3.3 Share of each change in the total reduction

| Change | Share of the cells saved | Share of the SRAM bits saved |
|---|---:|---:|
| B1, shared demodulator | 78.8 % | 0 |
| A1 + A2, debug infrastructure | 15.2 % | 100 % |
| B2, Gaussian table | 6.0 % | 0 |

Shares of the sum of the parts (34 200 cells). B1 is most of the logic saving
because upstream replicates the demodulator 8 times (62 % of the controller).
B2 removes 89 % of the Gaussian filter, but the filter is only 4.5 % of the
controller. The memory saving comes only from removing debug infrastructure.

## 4. Static timing

`scripts/timing/run_sta.sh` with `STA_SET=controller`: the netlist of the area
flow, flip-flops and RAM macros cut to a register-to-register network, fanout
legalised (maximum 16) and gates sized, ABC `stime`, and the worst liberty
clock-to-Q and setup added. Results in
[`results/timing/all-branches/`](../../results/timing/all-branches/).
Target: the 16 MHz baseband clock, 62.5 ns.

| | `master` / `risc-v-ble` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.546 ns | 3.913 ns | 4.044 ns |
| Logic path (buffered, sized) | 1.631 ns | 1.546 ns | 1.475 ns | 1.597 ns |
| Register overhead | 0.359 ns | 0.359 ns | 0.359 ns | 0.347 ns |
| **Min period** | **1.991 ns** | **1.905 ns** (−4.3 %) | **1.834 ns** (−7.9 %) | **1.944 ns** (−2.4 %) |
| Slack at 62.5 ns | +60.509 ns | +60.595 ns | +60.666 ns | +60.556 ns |
| Fmax | 502.3 MHz | 524.9 MHz | 545.3 MHz | 514.3 MHz |
| Flip-flops / gates timed | 4 578 / 45 716 | 4 422 / 43 804 | 3 926 / 19 419 | 2 673 / 13 428 |
| Worst path | `genblk1[2]…gfsk_demodulation_i.i1[5]` → `signal_for_decision[31]`: the multiply of one demodulator copy | `btle_ll_i…write_data[16]` → `[76]`: the 64-bit `timestamp` counter | `gfsk_demodulation_shared_i.old_q[7]` → `signal_for_decision[30]`: the shared multiply | `btle_ll_i…write_data[16]` → `[76]`: the 64-bit `timestamp` counter |

What can be said, and what cannot:

1. **Every branch closes 16 MHz with a factor of about 31 in hand**
   (1.83–1.99 ns of a 62.5 ns period). None of the changes makes timing a
   constraint.
2. **No change lengthens the critical path.** Sharing the demodulator (B1) does
   not: `ble-rx-dm` has the shortest period of the four, because the sharing is
   in time, not in logic depth.
3. **Differences below about 0.1 ns are flow noise, not design effects.** The
   `timestamp` counter of `btle_ll` is the same RTL on `master`, `ble-tx-table`
   and `ble-rx-dm`, yet it times at 1.546 ns in the `ble-tx-table` netlist,
   where it is the worst path, and at most 1.475 ns in the `ble-rx-dm` one,
   where the demodulator is worse. Likewise the 8 demodulator copies of
   `ble-tx-table` are the upstream RTL, and time below 1.546 ns there against
   1.631 ns on `master`. Buffering and sizing are heuristics over the whole
   netlist, so ranking the branches within 0.1 ns means nothing.
4. The unbuffered column only shows that Yosys builds no buffer trees
   (explained in `STATIC_TIMING.md` on `ble-opt`); it is kept for completeness.

## 5. Switching activity

### 5.1 Method

`scripts/power/run_activity.sh`, the harness of `SWITCHING_ACTIVITY.md` on
`ble-opt`, once per branch. Results in
[`results/power/all-branches/`](../../results/power/all-branches/).

- Both **gate-level** netlists, upstream and the branch, run side by side in one
  Verilator simulation per scenario, and every output is compared on every
  clock. For `ble-tx-table` and `ble-rx-dm`, which remove nothing, the
  comparison covers **every** output and every register read (`FULL_COMPARE`);
  for `ble-opt` the three outputs removed on purpose are skipped. **No
  mismatch in any scenario, on any branch.**
- Five scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`), each a window of
  exactly 100 000 `bb_clk` cycles after the same setup, which is subtracted.
- **One vector set for every branch** (`vectors.tar.gz`, example 0 of the
  Python model, 20 dB, 20 ppm). The generator's channel noise is not seeded;
  a first attempt of this run generated vectors per branch, so each branch saw
  a different packet noise, and it was stopped and repeated with one set.
- Measures, as on `ble-opt`: toggles per net where it is driven; nets with a
  toggle rate > 0.1; and the **switched-capacitance proxy** Σ toggles × liberty
  input-pin capacitance, split into data pins and flip-flop `CK` pins. No
  wires, no clock tree, no internal energy, no leakage.

The upstream side of every run is the same design on the same stimulus, and
it comes out identical in the four runs; `master` against upstream shows no
difference at all (the consistency checks at the end of
[`summary.md`](../../results/compare/all-branches/summary.md)). The scenarios
that do not use the packet vectors (`tx`, `idle`, `idle0`) also reproduce the
earlier `ble-opt` run `sticker-vs-upstream` exactly, every count of every
block, upstream and reduced alike; `rx` and `mixed` cannot, because that run's
vectors were not kept.

### 5.2 Data + clock switched capacitance, every scenario

| Scenario | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|
| `rx` | 1.23 × 10⁹ fF | −2.4 % | −12.9 % | **−33.2 %** |
| `tx` | 1.00 × 10⁹ fF | −5.0 % | −8.0 % | **−34.7 %** |
| `mixed` | 1.25 × 10⁹ fF | −3.2 % | −9.5 % | **−30.3 %** |
| `idle` | 1.26 × 10⁹ fF | −2.3 % | −5.9 % | **−25.5 %** |
| `idle0` | 0.95 × 10⁹ fF | −3.1 % | −8.5 % | **−34.4 %** |

### 5.3 The measures of `SWITCHING_ACTIVITY.md`, scenario `mixed`, every branch

| Measure | `master` / `risc-v-ble` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Toggles / cycle, non-clock nets | 984.3 | 956.4 (−2.8 %) | 1 004.5 (+2.1 %) | 939.7 (−4.5 %) |
| Nets with activity > 10 % | 839 | 827 | 4 002 (×4.8) | 3 908 (×4.7) |
| `btle_rx` toggles / cycle | 791.1 | 790.6 | 811.5 (+2.6 %) | 808.8 (+2.2 %) |
| `btle_ll` toggles / cycle | 41.5 | 40.6 | 41.7 | 11.0 (**−73.4 %**) |
| Gaussian filter toggles / cycle | 39.1 | 12.6 (**−67.8 %**) | 39.1 | 12.3 (**−68.6 %**) |
| Clock network (CK-pin load × toggles) | 8.76 × 10⁸ | −3.4 % | −14.1 % | **−41.4 %** |
| Memory: toggles on RAM ports | 3 044 741 | unchanged | unchanged | **−40.0 %** |
| Data load × toggles | 3.73 × 10⁸ | −2.8 % | +1.5 % | −4.3 % |
| **Data + clock proxy** | 1.25 × 10⁹ | **−3.2 %** | **−9.5 %** | **−30.3 %** |

The full tables (every scenario, every block, the most active nets) are in
[`results/compare/all-branches/summary.md`](../../results/compare/all-branches/summary.md)
and in each branch's `results/power/all-branches/<branch>/summary.md`.

### 5.4 The activity savings add up too

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
(−16.6 %); every other block stays within 1 %.

### 5.5 What each change does to activity

- **B2, Gaussian table.** The filter switches 68 % less (79.1 → 25.4 toggles per
  cycle while transmitting) and loses 156 of its 178 clocked flip-flops. It
  only works while transmitting, so the gain is largest in `tx` (−18.7 % of all
  non-clock toggles, −5.0 % of the proxy) and in `idle` it is the clock pins
  alone (−2.3 %).
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

## 6. Evidence per branch

Every branch that changes the RTL has its own proof that nothing needed was
lost, plus the gate-level lockstep of this run (§ 5.1), in which every output
of the synthesised netlist is compared with upstream on every clock.

| | `ble-tx-table` (B2) | `ble-rx-dm` (B1) | `ble-opt` (B1 B2 A1 A2) |
|---|---|---|---|
| Formal proof of the change | table ≡ upstream FIR, **unbounded** (k-induction), 3/3 mutants rejected | shared ≡ the 8 upstream demodulators, **unbounded at 16 bits**, 4/4 mutants rejected | both proofs (B1, B2) |
| Defaults ≡ original (formal, per module) | 5 modules against `upstream-baseline` (96 609 `$equiv` cells for the controller) | — (B1 is not optional) | 7 modules against `88f2250` |
| Lockstep against upstream | controller through the registers, `GAUSS_TABLE=1`: 15/15, 923 385 clocks, **every output and register**, 4/4 mutants | `btle_rx`: 60/60, 25 367 270 clocks, 4/4 mutants | controller through the registers: 15/15, 923 385 clocks (removed outputs skipped), 3/3 mutants |
| Upstream testbenches, 270 runs | 270/270 identical **with the table on** | 270/270 identical | 270/270 identical (defaults) |
| Gate-level lockstep, this run | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches |
| Report | `docs/04 Validation/TX_TABLE_VALIDATION.md` | `docs/04 Validation/SHARED_DEMOD_VALIDATION.md` | `SHARED_DEMOD_VALIDATION.md`, `STICKER_REDUCTIONS_VALIDATION.md` |

## 7. What each branch gives up

| Branch | Functions removed |
|---|---|
| `master`, `risc-v-ble` | none (the reference) |
| `ble-rx-dm` | **none**: B1 is an exact rewrite; the 8 phase hypotheses and the CRC-based selection are kept |
| `ble-tx-table` | the runtime change of the Gaussian taps (register 1): the taps become a synthesis parameter |
| `ble-opt` | the runtime Gaussian taps; the IQ capture (`btle_ll -q`); the UART HCI; the 1 PPS input; the latency statistic of `btle_ll.c`; removed registers read 0 |

## 8. Conclusions

1. **B1 is the change that matters for logic.** On its own it removes 53.6 %
   of the controller's cells, 79 % of all that `ble-opt` saves, costs no
   function and does not slow the design. B2 is a small exact gain (−4.1 %)
   that costs the runtime-programmable taps.
2. **All the memory saving is debug infrastructure.** Neither B1 nor B2 touches
   the SRAM; A1 and A2 remove 92.3 % of it, almost all of it the 1 Mbit
   IQ-capture RAM.
3. **The four changes are independent.** Area adds up to within 7 cells (and
   exactly in flip-flops), switching activity to within 0.1 point in every
   scenario. Each branch's figure is that change's contribution, and any
   subset can be combined with a predictable result.
4. **Activity ranks the changes differently from area.** The debug
   infrastructure (A1 + A2) gives most of the 25–35 % proxy reduction, because
   it is logic clocked on every cycle; B1 lowers the clock load but raises data
   switching when the receiver has no traffic; B2 matters only while
   transmitting.
5. **Timing does not separate the branches.** All close 16 MHz with a factor
   of about 31, and the differences between them are within the flow's noise.

## 9. What this does not claim

- **No FPGA, no silicon, no power.** Area and timing are pre-layout (ideal
  wires, ideal clock, setup only, RAM macros not timed). Switching activity is
  a pin-capacitance proxy with no wires, no clock tree, no internal energy and
  no leakage, from zero-delay simulation, which does not count glitches.
- **One stimulus set** for activity (example 0 of the Python model, seed 1,
  100 000 cycles per scenario).
- **The resolution of the method.** The same block, with the same RTL and the
  same stimulus, can differ by up to about 2 % between two netlists
  (`btle_ll` toggles −2.0 % on `ble-tx-table`, whose Link Layer is the upstream
  RTL mapped to 29 fewer cells), and timing by up to about 0.1 ns (§ 4).
- **A1 and A2 are not isolated in a branch of their own**; their share is
  measured on their own blocks, and §§ 3.2 and 5.4 show it is consistent with
  the totals.

## 10. Reproducing

From WSL, at the root of `ble-opt`, `ble-tx-table` or `ble-rx-dm`. The
harness is the same set of files on the three branches, and it reads every
branch through `git archive`, so the branch checked out does not matter:

```bash
scripts/compare/run_compare.sh <label>                          # about 1 h, all four configurations
scripts/compare/run_compare.sh <label> ble-tx-table ble-rx-dm   # a subset
# the activity of this run exactly: reuse its vectors
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label>
```

The script refuses to overwrite a label. It records, per configuration, the
revision, commit, `verilog/` tree and parameters in
[`results/compare/all-branches/provenance.txt`](../../results/compare/all-branches/provenance.txt),
writes [`summary.md`](../../results/compare/all-branches/summary.md) and
`data.json`, and fails if a consistency check fails. Area and timing take
about a minute; activity about 15 minutes per configuration.

This run's own summariser (`f540e99`) compared the capacitance sums of the
upstream side bit for bit and flagged them, although every count was
identical: the sums differ by about 10⁻¹⁵ relative, because `saif_activity.py`
adds them in Python-set order, which changes from one process to the next.
`696b036` compares counts exactly and sums to 10⁻⁹; the summary was
regenerated from the same measurements with it, and every check passes. No
measurement was repeated or changed.
