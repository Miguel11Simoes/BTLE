# Switching activity: upstream vs the reduced configuration

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Date:** 2026-09-19  
**Author:** Miguel Simões  
**Status:** executed (harness commit `507a8e7`, RTL `3c2c86e`). Post-synthesis
switching activity only, **not power**.

---

## Purpose

This report answers two questions. Did the area reduction also reduce dynamic
switching activity? And which blocks still switch more than they need to?
The comparison is upstream `btle_controller` (default parameters) against the
`ble-opt` reduced configuration (`ENABLE_IQ_CAPTURE=0, LL_MINIMAL=1,
GAUSS_TABLE=1`), with **exactly the same stimuli and the same number of cycles**.

## 1. Method

`scripts/power/run_activity.sh`; results in
[`results/power/sticker-vs-upstream/`](../../results/power/sticker-vs-upstream/summary.md).

1. **Netlists.** Both controllers are synthesised with the flow of the area
   runs (Yosys, Nangate45, RAMs as macros). The logic is flattened inside each
   block, with hierarchy kept at the boundaries of `btle_rx`, `btle_tx`,
   `gauss_filter`, `btle_ll`, `auxiliary_daemon` and
   `clock_domain_conversion_iq`, so activity can be attributed. Cell areas
   are within 2 % of the flattened area runs: 72 191 vs 71 706 µm², and
   27 111 vs 26 681 µm².
2. **Simulation.** Both **gate-level** netlists run side by side in one
   Verilator simulation per scenario. The Nangate cell models are generated
   from the liberty itself. Every output is compared on every clock (except the
   three removed on purpose), and **there were no mismatches in any scenario**:
   the synthesised netlists behave identically.
3. **Counting.** Verilator writes a SAIF, giving toggle counts per net. The
   setup phase (reset, loading of the COS/SIN tables and taps, RX
   configuration; 20 651 cycles, identical in every run) is subtracted net by
   net. Each scenario then has a window of exactly **100 000 bb_clk cycles**
   (6.25 ms at 16 MHz).
4. **Metrics.**
   - toggles, counted once per net where the net is driven;
   - toggle rate = toggles / window cycles;
   - "hot" nets = non-clock nets with a toggle rate > 0.1;
   - a **switched-capacitance proxy** = Σ toggles × liberty input-pin
     capacitance of the loads, split into data pins and flip-flop `CK` pins.
     It includes **no wires, no clock tree, no internal cell energy and no
     parasitics**, so it ranks designs but is not a power figure.

| Scenario | Stimulus (identical for both designs) | Events in the window |
|---|---|---|
| `rx` | packets of the Python model between random noise, one third with a corrupted tail; firmware reads of each packet | 18 packets, 17 decoded, 14 CRC OK, 306 register reads |
| `tx` | RX input zero; packets transmitted through the registers | 17 packets |
| `mixed` | RX packets + firmware reads + a TX after each + status polling | 9 RX (6 CRC OK), 8 TX, 202 reads |
| `idle` | radio listening to low-level noise; no packet, no TX, no register access | none |
| `idle0` | RX input zero; nothing else (structural activity only) | none |

## 2. Results

### 2.1 The measures requested, scenario `mixed`

| Measure | Upstream | `ble-opt` | Change | What it shows |
|---|---:|---:|---:|---|
| Toggle count, non-clock nets | 98 184 282 | 93 779 441 | −4.5 % | global activity |
| Toggles / cycle | 981.8 | 937.8 | −4.5 % | normalised by duration |
| Nets with activity > 10 % | 838 | 3 911 | **×4.7** | hotspots (see § 3) |
| `btle_rx` toggles / cycle | 788.8 | 807.1 | +2.3 % | effect of the shared demodulator |
| `btle_ll` toggles / cycle | 41.5 | 11.0 | **−73.4 %** | effect of the simplification |
| Gaussian filter toggles / cycle | 39.1 | 12.3 | **−68.6 %** | table vs FIR |
| Clock network (CK-pin load × toggles) | 8.76 × 10⁸ | 5.14 × 10⁸ | **−41.4 %** | structural overhead: 4 578 → 2 673 flip-flops |
| Reset networks | 0 | 0 | — | resets are static during the window |
| Memory: toggles on RAM ports | 3 044 577 | 1 826 221 | −40.0 % | the IQ-capture RAM (1 Mbit, written on **every** 16 MHz cycle in upstream) is gone |
| Data load × toggles (fF-toggles) | 3.72 × 10⁸ | 3.56 × 10⁸ | −4.3 % | data switched capacitance |
| **Data + clock proxy** | 1.25 × 10⁹ | 8.70 × 10⁸ | **−30.3 %** | total pin switched capacitance |

### 2.2 Every scenario

| Scenario | Non-clock toggles / cycle | Δ | Hot nets | Data proxy Δ | Clock proxy Δ | **Data + clock Δ** | RAM-port toggles Δ |
|---|---|---:|---|---:|---:|---:|---:|
| `rx` | 914.0 → 789.9 | **−13.6 %** | 517 → 2 633 | −13.3 % | −41.4 % | **−33.3 %** | −40.7 % |
| `tx` | 292.2 → 328.5 | +12.4 % | 754 → 706 | +12.5 % | −41.4 % | **−34.7 %** | −25.5 % |
| `mixed` | 981.8 → 937.8 | −4.5 % | 838 → 3 911 | −4.3 % | −41.4 % | **−30.3 %** | −40.0 % |
| `idle` | 989.4 → 1 101.5 | +11.3 % | 631 → 4 180 | +10.8 % | −41.4 % | **−25.5 %** | −48.3 % |
| `idle0` | 134.8 → 224.8 | +66.7 % | 339 → 384 | +49.6 % | −41.4 % | **−34.4 %** | −30.4 % |

### 2.3 `btle_rx`, the block with the shared demodulator

| Scenario | Toggles / cycle | Data proxy | Clock proxy | Mean toggle rate per net |
|---|---|---:|---:|---|
| `rx` | 813.5 → 725.1 (−10.9 %) | −11.0 % | −31.5 % | 0.021 → 0.063 |
| `mixed` | 788.8 → 807.1 (+2.3 %) | +1.5 % | −31.5 % | 0.020 → 0.070 |
| `idle` | 869.9 → 1 006.0 (+15.6 %) | +13.7 % | −31.5 % | 0.022 → 0.088 |
| `tx` / `idle0` | 91.6 → 205.3 (+124 %) | +71.0 % | −31.5 % | 0.002 → 0.018 |

## 3. What the numbers say

**1. The data + clock switched-capacitance proxy falls in every scenario, by
25–35 %.** It is dominated by the flip-flop clock pins, which fall by 41 %
because 1 905 flip-flops are gone. With identical stimuli, this is what can be
defended now:

> "Post-synthesis pin switched capacitance (data + clock pins, no wires)
> decreased by 25–35 % under identical workloads."

It is **not** "power decreased by X %" (§ 4).

**2. Non-clock toggles do not fall everywhere.** They fall with real
traffic: −13.6 % in RX and −4.5 % in mixed. They rise when the receiver
listens to nothing or to noise: +12 % in TX, +11 % in idle, +67 % in idle0.
The whole difference is in `btle_rx`. Every other block falls or stays equal:
- `btle_ll`: −64 to −74 %;
- Gaussian filter: −69 % in toggles;
- IQ capture: −13 to −100 %;
- TX (other), clock-domain crossing, glue: unchanged.

**3. Fewer cells, each switching more.**
In `btle_rx` the mean toggle rate per net goes up about 3–8× (0.02 → 0.06–0.09),
and its hot nets go up about 14× (242 → 3 410 in `mixed`). There are two causes, visible in the most
active nets:

- **Data-independent control with large fanout.** `s_valid`, `valid1` and
  `valid2` of the shared demodulator change on **every** cycle (samples arrive
  on every other cycle), and so do the buffer nets synthesis inserted to drive
  them. They are the enables of 256 history flip-flops and of the pipeline
  registers. Nangate45 has no enable flip-flop, so each enable is a
  multiplexer whose select pin switches with `s_valid`. In upstream, each copy's
  valid changed 8× less often and drove a small fanout. With a zero input
  (`idle0`, `tx`) this is almost all of the `btle_rx` increase:
  +114 toggles/cycle.
- **Data-dependent.** The shared multiplier receives an unrelated pair of
  operands (a different phase) on every sample, whereas each upstream copy saw
  one phase. With noise (`idle`) this adds switching. With real packets (`rx`)
  it no longer dominates, and `btle_rx` falls by 11 %.

**4. The lower capacitance outweighs the higher activity.** Even in `btle_rx`,
data + clock falls in every scenario (−10 % to −22 %). The one exception is
the data part alone, in scenarios without traffic.

## 4. What this does not claim

- **Not power.** There are no wires, no clock tree, no internal cell energy
  (flip-flop clock energy is large, and it falls with the flip-flop count) and
  no leakage. There is no STA, so no frequency or voltage point. A defensible
  power number needs place and route, timing, and power analysis with this
  SAIF.
- **One stimulus set.** One packet type (example 0), one seed, 100 000 cycles
  per scenario. The hot-net counts and ratios are stable across scenarios, but
  have not been checked against other seeds or packets.
- **Gate level with ideal cells.** Zero-delay simulation: no glitches. Real
  multipliers glitch, and the shared one switches its operands on every
  sample, so this probably under-counts `btle_rx` a little more for `ble-opt`
  than for upstream.
- About 12 nets per design (≈ 0.02 %) appear in the netlist but not in the SAIF
  and are ignored.

## 5. Follow-up

1. **Clock gating of the shared demodulator's registers** (history and
   pipeline): replace the enable multiplexers by an integrated clock-gating
   cell per phase group. This removes the select-pin switching found in § 3 and
   saves further flip-flop clock power. An ASIC flow does this automatically
   from the enables. It should be measured with this same harness.
2. **STA next**, as agreed: close frequency on the reduced netlist before any
   further area work. It also gives the timing needed for a real power
   analysis.

## 6. Reproducing

```bash
scripts/power/run_activity.sh <label> [window-cycles] [seed]   # WSL/Linux, repository root
```

The script refuses to overwrite a label. It records the commits, tools and
liberty hash, keeps the logs, the per-scenario JSON and the summary, and
stores only the hashes of the netlists (the SAIFs, about 40 MB each, are not
kept).
