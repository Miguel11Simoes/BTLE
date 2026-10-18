# Comparison of the receiver branches: upstream, `ble-rx-dm` and `ble-rx-dmult`

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** these branches carry this same file, with its companion [TX_BRANCH_COMPARISON.md](TX_BRANCH_COMPARISON.md) (`master`, `risc-v-ble`, `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw`, `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, `ble-tx-cordic`, `ble-tx-min`, `ble-rx-dm`, `ble-rx-dmult`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`); reference of the measurements: corrected `master` (`fca6ac6`)  
**Date:** 2026-10-18 (split from `BRANCH_COMPARISON.md`, whose receiver branch was `ble-rx-dm`; `ble-rx-dmult` and run `rx-dmult`)  
**Author:** Miguel Simões  
**Status:** executed: run `rx-dmult`, harness `scripts/compare/` at `11a602b` (on `ble-rx-dmult`),
`REF_REV=master`, for corrected `master`, `ble-rx-dm` and `ble-rx-dmult` at their heads, on the
RTL after the product audit and the lint closure, with the activity vectors of run `all-branches`;
the demodulator alone in run `rx-dmult-demod`, `btle_rx` timed alone in run `rx-dmult-full`; the
figures of `ble-rx-dm` before the audit from run `all-branches` (§ 8). Pre-layout area and static
timing, and gate-level switching activity, which is a proxy and **not power**.

---

## Purpose

The receiver samples the signal 8 times per symbol (8 MS/s for 1 Mbit/s) and does not know in
advance which of the 8 sampling phases is the best one. Upstream's `btle_rx` therefore decodes
all 8: each phase has its own `btle_rx_core` (Access Address search, de-whitening, CRC, packet
buffer), and inside each a GFSK demodulator that computes, one symbol apart,

  signal = i[n−8]·q[n] − i[n]·q[n−8],  phy_bit = (signal > 0),

with two 16 × 16 signed multipliers: 8 × 2 = **16 multipliers**. The packet whose CRC is right
selects the phase. Two branches change only that demodulation, and keep the 8 decoders and the
CRC selection:

| Branch | Change | Multipliers |
|---|---|---:|
| `master` | upstream's receiver, corrected by the product audit (the reference) | 16 |
| `ble-rx-dm` | **B1**: one demodulator shared by the 8 phases, with one history entry (I, Q) per phase; the two products of a sample in one clock | 2 |
| `ble-rx-dmult` | B1 with **one multiplier**: the two products of a sample in two consecutive clocks, the first in the clock that reads the history, the second in the next one, so the decision keeps its clock | **1** |

`ble-rx-dmult` uses the time the receiver leaves free: the baseband clock is 16 MHz and the
samples come at 8 MS/s, so a sample arrives at most every second clock, and one multiplier can
compute both of its products before the next one. The clock-domain crossing of the RF
interface (`clock_domain_conversion_iq`) gives that by construction: it raises the sample
valid only when its 2:1 phase is 0, whatever the RF side does (§ 6).

`ble-opt` also carries B1, together with transmitter and debug changes; it is compared in
[TX_BRANCH_COMPARISON.md](TX_BRANCH_COMPARISON.md), which shows that B1 adds up with them.

This document measures the three with the same ruler and answers three questions: what each
change buys, what it costs in function, and whether the receiver's outputs stay the same.

This file is identical on every branch listed above. The results it cites are on
`ble-rx-dmult`, in `results/compare/rx-dmult/`, `results/{area,timing,power}/rx-dmult/`,
`results/area/rx-dmult-demod/`, `results/timing/rx-dmult-full/` and `results/validation/dmult*/`;
those of § 8 are in `results/compare/all-branches/` and `results/{area,timing,power}/all-branches/`,
on `ble-rx-dm`, `ble-rx-dmult` and the measurement branches of the TX comparison. The relative
links below resolve on `ble-rx-dmult`.

## 1. The branches

| Branch | What it is | RTL (`verilog/`) | Measured as |
|---|---|---|---|
| `master` | upstream BTLE (`upstream-baseline`) with the corrections of the product audit and the lint closure (`PRODUCT_VALIDATION.md`, `LINT_CLOSURE.md`): the reference | tree `6e670a6`, commit `fca6ac6` | defaults |
| `ble-rx-dm` | corrected `master` + B1 | `btle_rx.v`, `btle_rx_core.v` (`EXTERNAL_DEMOD`, default 0, keeps it upstream's when used alone), new `gfsk_demodulation_shared.v`; elsewhere only comments and file lists; tree `66ff2c2`, commit `38755a0` | defaults (B1 is not a parameter) |
| `ble-rx-dmult` | `ble-rx-dm` with one multiplier in the shared demodulator | `gfsk_demodulation_shared.v` only; tree `ee1dabc`, commit `f00bd9e` (later commits add harness, results and documents) | defaults (not a parameter) |

How they relate:

```
master  (corrected: upstream-baseline + the product audit + the lint closure, fca6ac6)
 └─ ble-rx-dm      B1 (aa8a014 … 88f2250 on the history of ble-opt), then the audit and the
     │             lint closure as on master: master + B1, 38755a0
     └─ ble-rx-dmult  from 38755a0: one multiplier (f00bd9e); its harness (aa83311, 11a602b)
ble-opt  B1 + B2 + A1 + A2 (TX_BRANCH_COMPARISON.md)
```

## 2. The comparison

Run `rx-dmult`. Differences are against corrected `master`, and, in brackets, of `ble-rx-dmult`
against `ble-rx-dm`.

| | `master` | `ble-rx-dm` | `ble-rx-dmult` |
|---|---|---|---|
| **Content** | upstream BTLE, corrected | **B1**: one shared demodulator | B1 with **one multiplier**, time-shared |
| Configuration measured | defaults | defaults | defaults |
| GFSK demodulators / multipliers in `btle_rx` | 8 / 16 | **1, shared / 2** | **1, shared / 1** |
| Decoders (AA search, de-whitening, CRC, packet buffer), CRC selection | 8, yes | 8, yes | 8, yes |
| **Std cells, `btle_controller`** | 52 357 | 25 445 (−51.4 %) | **24 205 (−53.8 %)** [−1 240, −4.9 %] |
| Flip-flops | 4 722 | 4 070 (−13.8 %) | 4 073 (−13.7 %) [+3] |
| Cell area (µm²) | 74 684.8 | 41 794.7 (−44.0 %) | **40 164.1 (−46.2 %)** [−1 630.6, −3.9 %] |
| SRAM bits | 1 136 070 | 1 136 070 | 1 136 070 |
| **Std cells, `btle_rx`** | 36 782 | 9 973 (−72.9 %) | **8 441 (−77.1 %)** [−1 532, −15.4 %] |
| The demodulator alone: cells / µm² (§ 3.2) | 8 × 3 899 / 8 × 4 757.4 | 5 051 / 7 027.7 | **3 439 / 5 226.6** [−31.9 % / −25.6 %] |
| Min period of the controller at 16 MHz (62.5 ns) | 3.410 ns | 3.374 ns | 3.357 ns |
| Worst path of the controller | the Gaussian tail of the transmitter | the same | the same |
| Min period of `btle_rx` alone (§ 4) | 1.991 ns | 1.849 ns | 1.972 ns [+0.123 ns] |
| **Data + clock switched capacitance, `mixed`** | *running* | *running* | *running* |
| … over the 5 scenarios | — | *running* | *running* |
| Clock pins (load × toggles) | *running* | *running* | *running* |
| Non-clock toggles / cycle, `mixed` | *running* | *running* | *running* |
| Nets with activity > 10 %, `mixed` | *running* | *running* | *running* |
| RAM-port toggles, `mixed` | *running* | *running* | *running* |
| Functions removed | — | **none** | **none**; `btle_rx` takes at most one sample every two clocks, which is what the RF interface gives (§ 7) |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | *running* | *running* |
| Validation (§ 6) | the reference | formal ≡ upstream (B1), lockstep, 270/270 | formal ≡ `ble-rx-dm`, lockstep 60/60, *running* |

## 3. Area

Same flow as every earlier run (`scripts/area/run_area.sh`: Yosys 0.68, `synth -flatten`,
`dfflibmap`, `abc -liberty`, Nangate45, SRAMs blackboxed and counted in bits), the 16 tops of
the controller for each configuration ([`results/area/rx-dmult/`](../../results/area/rx-dmult/)),
and the shared demodulator synthesised alone
([`results/area/rx-dmult-demod/`](../../results/area/rx-dmult-demod/)).

### 3.1 Per block (std cells, each top synthesised alone)

| Top | `master` | `ble-rx-dm` | `ble-rx-dmult` | `ble-rx-dmult` − `ble-rx-dm` |
|---|---:|---:|---:|---:|
| `gfsk_demodulation` (one upstream copy) | 3 899 | 3 899 | 3 899 | 0 |
| `btle_rx_core` | 4 477 | 4 468 | 4 468 | 0 |
| **`btle_rx`** | 36 782 | **9 973** (−72.9 %) | **8 441** (−77.1 %) | **−1 532** |
| `btle_tx` | 5 823 | 5 947 (+2.1 %) | 5 917 (+1.6 %) | −30 |
| `gauss_filter` | 2 286 | 2 286 | 2 286 | 0 |
| `btle_phy` | 42 844 | 15 934 (−62.8 %) | 14 387 (−66.4 %) | −1 547 |
| `clock_domain_conversion_iq` | 186 | 186 | 186 | 0 |
| `auxiliary_daemon` | 299 | 299 | 299 | 0 |
| `btle_ll` | 9 523 | 9 523 | 9 523 | 0 |
| **`btle_controller`** | **52 357** | **25 445** (−51.4 %) | **24 205** (−53.8 %) | **−1 240** |

Cell area: `btle_rx` 48 619.2 → 15 741.1 → 13 988.4 µm² (−1 752.7 µm² for `ble-rx-dmult`), the
controller 74 684.8 → 41 794.7 → 40 164.1 µm² (−1 630.6 µm²).

- **Each change moves only the receiver.** `btle_rx_core`, the decoders and every block outside
  the receiver synthesise to the same cells on the three branches, but for `btle_tx`, whose RTL is
  the same on all three: 5 823, 5 947 and 5 917 cells, the flow noise already recorded
  (`TX_BRANCH_COMPARISON.md` § 4.4: the runtime FIR's multipliers map differently when the other
  modules read differ). It is why the controller saves 1 240 cells and `btle_rx` 1 532.
- **B1 is most of the receiver.** On the audited RTL it removes 26 809 cells of `btle_rx`
  (−72.9 %) and 26 912 of the controller (−51.4 %), as before the audit (−72.7 % and −53.6 %, § 8).

### 3.2 The demodulator alone

| `gfsk_demodulation_shared` | `ble-rx-dm` | `ble-rx-dmult` | Δ |
|---|---:|---:|---:|
| Std cells | 5 051 | **3 439** | **−1 612 (−31.9 %)** |
| Flip-flops | 412 | 415 | +3 |
| Cell area (µm²) | 7 027.7 | **5 226.6** | **−1 801.1 (−25.6 %)** |

- **The saving is one 16 × 16 signed multiplier**: 1 612 cells and 1 801.1 µm², less the operand
  multiplexer that now feeds it (two 16-bit 2:1 multiplexers) and the enable of the decision
  register. For comparison, one whole upstream demodulator copy, with its two multipliers, its
  operand registers and its decision, is 3 899 cells and 4 757.4 µm².
- **The flip-flops stay**: in the RTL the 32-bit first product replaces the operands `old_i` and
  `new_q`, 412 flip-flops on both branches. The 3 more that Yosys reports are a copy of the 3-bit
  phase register: on `ble-rx-dmult` the history entry of I goes straight into the multiplier, not
  into a register, so `memory_dff` merges the address register into its read port instead of the
  output register (`hist_i$rdreg` in the netlist; the synthesis log of
  [`rx-dmult-demod/ble-rx-dmult`](../../results/area/rx-dmult-demod/ble-rx-dmult/gfsk_demodulation_shared/)).
- **The SRAMs do not move**: no change touches a memory of the receiver (32 768 bits in its packet
  buffers, the same on the three).

## 4. Static timing

`scripts/timing/run_sta.sh` (the netlist of the area flow cut to a register-to-register network,
fanout legalised and gates sized, ABC `stime`, the worst liberty clock-to-Q and setup added),
against corrected `master`: the controllers in run
[`rx-dmult`](../../results/timing/rx-dmult/) (`STA_SET=controller`), and `btle_rx` and the
demodulator alone in run [`rx-dmult-full`](../../results/timing/rx-dmult-full/)
(`STA_SET=full`). Target: the 16 MHz baseband clock, 62.5 ns.

| | `master` | `ble-rx-dm` | `ble-rx-dmult` |
|---|---:|---:|---:|
| Controller: logic path (buffered, sized) | 3.050 ns | 3.015 ns | 2.998 ns |
| Controller: **min period** / slack / Fmax | **3.410 ns** / +59.090 ns / 293.3 MHz | **3.374 ns** / +59.126 ns / 296.4 MHz | **3.357 ns** / +59.143 ns / 297.9 MHz |
| Controller: worst path | the Gaussian tail of the transmitter (`tail_i.remaining` → `tail_i.correction`) | the same | the same |
| `btle_rx`: logic path | 1.644 ns | 1.502 ns | 1.624 ns |
| `btle_rx`: **min period** / Fmax | **1.991 ns** / 502.1 MHz | **1.849 ns** / 540.9 MHz | **1.972 ns** / 507.2 MHz |
| `btle_rx`: worst path | a demodulator copy, `i0[6]` → `signal_for_decision[31]` | `old_i[6]` → `signal_for_decision[31]` | the history's read address (`hist_i$rdreg`) → the multiplier → `signal_for_decision[31]`: a false path (below) |
| Shared demodulator alone: logic path / min period | — | 1.493 / 1.840 ns | 1.618 / 1.965 ns |

- **The controller's worst path is not in the receiver** on any of the three: it is the Gaussian
  tail that the product audit added to the transmitter, with the runtime taps, as on corrected
  `master` in `TX_BRANCH_COMPARISON.md` § 5.1. The three periods differ by less than the flow's
  noise (0.15 ns).
- **The receiver's path is 0.12 ns longer, and the one reported is a false path**: 1.502 →
  1.624 ns of logic. The path the flow reports on `ble-rx-dmult` starts at the read address of
  the history (the phase register, which Yosys merges into the read port, § 3.2) and goes through
  the history read, the operand multiplexer, the multiplier and the subtraction into the decision
  register. No sample takes it: in a clock in which the decision register loads (E2), the
  multiplexer gives the multiplier the operands of E2, not the history, and the history goes
  through it only in the clock of a capture (E1), into the first product. A static analysis does
  not know that the two clocks exclude each other, so 1.624 ns is an upper bound; the true paths
  are the history read into the first product and the operands of E2 into the decision, each one
  multiplier and a multiplexer deep. Either way `btle_rx` keeps a factor of 31 at 16 MHz, and the
  difference is within the flow's noise.

## 5. Switching activity

`scripts/power/run_activity.sh`, the harness of the TX comparison, once per configuration,
against corrected `master` (`REF_REV=master`): both gate-level netlists, the reference and the
branch, side by side in one Verilator simulation per scenario, every output and every register
read compared on every clock (`FULL_COMPARE`); five scenarios (`rx`, `tx`, `mixed`, `idle`,
`idle0`) of 100 000 `bb_clk` cycles after the same setup, which is subtracted; **the vector set of
run `all-branches`** (example 0 of the Python model, 20 dB, 20 ppm; the same `vectors.sha256`);
toggles per net, nets above a toggle rate of 0.1, and the switched-capacitance proxy Σ toggles ×
liberty input-pin capacitance, split into data pins and flip-flop `CK` pins (no wires, no clock
tree, no internal energy, no leakage). Results in
[`results/power/rx-dmult/`](../../results/power/rx-dmult/) and
[`results/compare/rx-dmult/summary.md`](../../results/compare/rx-dmult/summary.md).

*Running (2026-10-18): the activity of run `rx-dmult` is being measured; this section, the activity rows of § 2 and § 6, and § 9 are completed when it ends. The run's lockstep has already passed on `master` and `ble-rx-dm`, every output identical in the 5 scenarios.*

## 6. Evidence per branch

| | `ble-rx-dm` (B1) | `ble-rx-dmult` |
|---|---|---|
| Formal proof of the change | shared ≡ the 8 upstream demodulators, **unbounded at 16 bits**, 4/4 mutants rejected (`SHARED_DEMOD_VALIDATION.md`, before the audit) | time-shared ≡ the shared demodulator of `ble-rx-dm`, **unbounded at 16 bits** (every product a free value constrained to be one function of its operands) and with the real multipliers at 4 bits; 6/6 mutants rejected by both; without the contract the proof fails, as it must; the contract proved on `clock_domain_conversion_iq`, unbounded |
| Lockstep of `btle_rx` | against upstream: 60/60, 25 367 270 clocks, 4/4 mutants (before the audit) | against corrected `master`, samples never in consecutive clocks: **60/60, 37 054 155 clocks, 17 558 142 samples, 7 521 packets with a correct CRC, 1 632 resets**; 6/6 mutants; samples in consecutive clocks caught |
| The product audit's matrix, 270 cases | 270/270 (lint closure, reference `9d6c383`) | *running* |
| TX waveforms | 167/167 | *running* |
| Lint gate (Verilator 5.020, `--Wall`) | 1/1 configuration, 12 reviewed exceptions | 1/1 configuration, 12 reviewed exceptions |
| Illegal-state recovery, lint negative controls | 3 checks, 10 controls | 3 checks, 12 controls |
| Product defects, RF contract, Gaussian tail, bit repeat, register readback, Yosys structure | 4/4; pass; pass; pass; pass; pass | 4/4; 12/12 scenarios, 2/2 mutants; pass; pass; pass; *running* |
| Harness tests | 23 passed | *running* |
| Gate-level lockstep, run `rx-dmult` | *running* | *running* |
| Report | `docs/Validation/SHARED_DEMOD_VALIDATION.md`, `LINT_CLOSURE.md` | `docs/Validation/RX_DMULT_VALIDATION.md` (on `ble-rx-dmult`) |

## 7. What each branch gives up

| Branch | Functions removed |
|---|---|
| `master` | none (the reference) |
| `ble-rx-dm` | **none**: B1 is an exact rewrite; the 8 phase hypotheses and the CRC-based selection are kept, and the shared unit takes a sample on every clock |
| `ble-rx-dmult` | **none at the controller**: the same outputs as `ble-rx-dm` on every clock. `btle_rx` and its shared demodulator take **at most one sample every two clocks** (`iq_valid` never high in two consecutive clocks), where upstream's took one per clock; the RF interface gives one every second clock at most, by construction (proved, § 6), and the upstream testbenches deliver one every other clock. A `btle_rx` reused alone, with a source that can give samples on consecutive clocks, would need that source to keep a gap |

## 8. Before the product audit: `ble-rx-dm` in run `all-branches`

`BRANCH_COMPARISON.md` measured `ble-rx-dm` before the product audit, in run `all-branches`
(harness `f540e99`, summary regenerated at `696b036`), against upstream at `upstream-baseline`,
with the same flows. These figures describe that RTL, not the corrected circuit; they are kept as
the record of B1 on its own. Their activity was read with `saif_activity.py` before `4657113`, which
gave some bits of vectors whose LSB is not 0 the activity of others (in `btle_ll` and `btle_rx`); run
`rx-dmult` reads them with the corrected parser, so § 5 and this section are not compared figure for figure.

| | `master` (= `upstream-baseline`) | `ble-rx-dm` |
|---|---:|---:|
| Std cells, `btle_controller` | 50 295 | 23 346 (−53.6 %) |
| Flip-flops | 4 578 | 3 926 (−14.2 %) |
| Cell area (µm²) | 71 706 | 38 782 (−45.9 %) |
| SRAM bits | 1 136 070 | 1 136 070 |
| Std cells: `btle_rx` / `btle_phy` / `btle_tx` | 36 864 / 40 339 / 3 409 | 10 068 (−72.7 %) / 13 536 (−66.4 %) / 3 411 |
| Transmitter with its SRAM macros (µm²) | 167 731 | 167 737 (0) |
| Min period at 16 MHz | 1.991 ns | 1.834 ns (−7.9 %) |
| Slack / Fmax | +60.509 ns / 502 MHz | +60.666 ns / 545 MHz |
| Worst path | demodulator multiply, one of 8 copies | shared demodulator multiply (`old_q[7]` → `signal_for_decision[30]`) |
| Data + clock switched capacitance, `mixed` | 1.25 × 10⁹ fF | −9.5 % |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | −12.9, −8.0, −9.5, −5.9, −8.5 % |
| Clock pins (load × toggles) | 8.76 × 10⁸ fF | −14.1 % |
| Non-clock toggles / cycle, `mixed` | 984.3 | 1 004.5 (+2.1 %) |
| Nets with activity > 10 %, `mixed` | 839 | 4 002 (×4.8) |
| `btle_rx` toggles / cycle, `mixed` | 791.1 | 811.5 (+2.6 %) |
| Data load × toggles, `mixed` | 3.73 × 10⁸ | +1.5 % |
| RAM-port toggles | 3 044 741 | unchanged |
| Gate-level outputs vs upstream, 5 scenarios | — | identical, every output |

B1 removed 652 flip-flops (−14 % of the clock load, the same in every scenario). With real
packets (`rx`) the receiver also switched less (`btle_rx` −10.2 %); with no traffic it switched
**more** (`btle_rx` +16 % in `idle`, +125 % in `tx`, receiver input zero), and the nets above 10 %
activity grew ×4.8 in `mixed` and ×6.7 in `idle`: the shared unit's valid and enable network
toggles on every sample whatever the data. The proxy still fell in every scenario because the
clock pins dominate it. Only `btle_rx`'s proxy moved (−16.6 % in `mixed`); every other block stayed
within 1 %, and B1 adds up with B2, A1 and A2 inside `ble-opt` to within 7 cells and 0.1 point
of activity (`TX_BRANCH_COMPARISON.md` §§ 3.2, 6.4).

## 9. Conclusions

*Completed with § 5. On what is measured so far: `ble-rx-dmult` removes one 16 × 16 multiplier (−1 612 cells, −31.9 %, of the shared demodulator; −1 240 cells, −4.9 %, of the controller against `ble-rx-dm`, −53.8 % against corrected `master`), keeps every output and every flip-flop, and costs 0.12 ns of the receiver's path, within the flow's noise, for one condition that the RF interface gives by construction: a sample never in two consecutive clocks.*

## 10. What this does not claim

- **No FPGA, no silicon, no power of the logic.** Area and timing are pre-layout (ideal wires,
  ideal clock, setup only, RAM macros not timed). Switching activity is a pin-capacitance proxy
  with no wires, no clock tree, no internal energy and no leakage, from zero-delay simulation,
  which does not count glitches.
- **One stimulus set** for activity (example 0 of the Python model, 100 000 cycles per scenario),
  the one of run `all-branches`.
- **The resolution of the method.** The same RTL moves by up to 2.1 % of the transmitter's cells
  between netlists here (`btle_tx`, § 3.1), and timing by up to about 0.15 ns
  (`TX_BRANCH_COMPARISON.md` § 5); the 0.12 ns of § 4 is inside it.
- **The 16-bit proof abstracts the products**: in both designs every 16 × 16 product is a free
  value constrained only to be one function of its operands, which the real products are; the
  proof with the real 16 × 16 multipliers did not close (§ 6 and `RX_DMULT_VALIDATION.md`), and
  with them it is proved at 4 bits. The equivalence with upstream's 8 demodulators follows from
  this proof and B1's (`SHARED_DEMOD_VALIDATION.md`), whose demodulator has not changed since.
- **The contract is proved on the RF interface, and checked by simulation above it**: that
  `clock_domain_conversion_iq` never raises the sample valid in two consecutive clocks is proved;
  that `btle_phy` and `btle_controller` pass it to `btle_rx` unchanged is a direct connection in
  their RTL, exercised by the regression matrix and the activity runs, not proved.

## 11. Reproducing

From WSL, at the root of `ble-rx-dmult` (the harness reads every branch through `git archive`;
the first name must be `master`):

```bash
# §§ 2-5, run rx-dmult: the vectors of run all-branches, corrected master as the reference
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
REF_REV=master VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> master ble-rx-dm ble-rx-dmult
# § 3.2, the demodulator alone; § 4, btle_rx and the demodulator timed alone
for b in ble-rx-dm ble-rx-dmult; do
  RTL_REV=$b scripts/area/run_area.sh <label>-demod/$b gfsk_demodulation_shared
  DUT_REV=$b STA_SET=full scripts/timing/run_sta.sh <label>-full/$b 62.5 master
done
# § 6, ble-rx-dmult (RX_DMULT_VALIDATION.md lists the whole campaign)
scripts/validation/formal_dmult/run_formal_dmult.sh <label> ble-rx-dm
scripts/validation/rx_lockstep/run_rx_lockstep.sh <label> 20 200 master
```

The scripts refuse to overwrite a label, and record the revision, commit, `verilog/` tree and
parameters of every configuration in `provenance.txt`
([`rx-dmult`](../../results/compare/rx-dmult/provenance.txt)). Area and timing take about a
minute; activity about 15 minutes per configuration.
