# Comparison of the receiver branches: upstream, `ble-rx-dm`, `ble-rx-dmult`, `ble-rx-aa`, `ble-rx-shared`, `ble-rx-adv`, `ble-rx-min`, `ble-rx-best` and `ble-rx-micro`

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** these branches carry this same file, with its companion [TX_BRANCH_COMPARISON.md](TX_BRANCH_COMPARISON.md) (`master`, `risc-v-ble`, `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw`, `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, `ble-tx-cordic`, `ble-tx-min`, `ble-rx-dm`, `ble-rx-dmult`, `ble-rx-aa`, `ble-rx-shared`, `ble-rx-adv`, `ble-rx-min`, `ble-rx-best`, `ble-rx-micro`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`); reference of the measurements: corrected `master` (`fca6ac6`)  
**Date:** 2026-10-18 (split from `BRANCH_COMPARISON.md`, whose receiver branch was `ble-rx-dm`; `ble-rx-dmult` and run `rx-dmult`)  
**Author:** Miguel Simões  
**Status:** executed: run `rx-dmult`, harness at `2cf1e17` (on `ble-rx-dmult`; its activity parser as on `ble-tx-min`, `4657113`),
`REF_REV=master`, for corrected `master`, `ble-rx-dm` and `ble-rx-dmult` at their heads, on the
RTL after the product audit and the lint closure, with the activity vectors of run `all-branches`;
the demodulator alone in run `rx-dmult-demod`, `btle_rx` timed alone in run `rx-dmult-full`; the
figures of `ble-rx-dm` before the audit from run `all-branches` (§ 8). `ble-rx-aa`: run `rx-aa`
(§ 12), the same flows, liberty, reference (`fca6ac6`) and activity vectors, on `ble-rx-aa`. `ble-rx-shared`:
run `rx-shared` (§ 13), the flows of run `rx-aa`, the same reference and vectors, on `ble-rx-shared`. `ble-rx-adv`:
run `rx-adv` (§ 14), the flows of run `rx-shared`, the same reference and vectors, and OpenRAM macros, on
`ble-rx-adv`. `ble-rx-min`: run `rx-min` (§ 15), the flows of run `rx-adv`, the same reference and vectors, on
`ble-rx-min`. `ble-rx-best`: run `rx-best` (§ 16), the flows of run `rx-min`, the same reference and
vectors, on `ble-rx-best`. `ble-rx-micro`: run `micro` (§ 17), the area flow of run `rx-best` and the
packet-error-rate harness `rx_per`; no timing or activity. Pre-layout
area and static timing, and gate-level switching activity, which is a proxy and **not power**.

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

A third branch, `ble-rx-aa`, leaves the demodulators as they are and changes the **Access Address
search** of the 8 decoders: upstream gives each phase a 32-bit shift register of its last bits and
a 32-bit comparator against the configured address, 8 × 32 = 256 flip-flops and 8 comparators.
`ble-rx-aa` has two configurations, measured side by side (§ 12):

| `ble-rx-aa` configuration | `RX_ADV_AA_ONLY` | Access Address search | Receives data-channel packets? |
|---|---:|---|---|
| `ble-rx-aa` | `0` (default) | **one comparator** for the 8 phases, on one interleaved shift line of 249 flip-flops; the address stays configurable; an exact rewrite | **yes**, like `master` |
| `ble-rx-aa` (advertising only) | `1` | **one pattern automaton** (KMP) for the advertising address `0x8E89BED6`: 8 states of 6 bits, 48 flip-flops, one next-state table | **no**: only the advertising address is detected; the input `unique_bit_sequence` is ignored |

The first is compared with the full functional reference; the second is the **additional** saving
bought by restricting the receiver to advertising, and is not equivalent to it.

This document measures the three with the same ruler and answers three questions: what each
change buys, what it costs in function, and whether the receiver's outputs stay the same.

This file is identical on every branch listed above. The results it cites are on
`ble-rx-dmult`, in `results/compare/rx-dmult/`, `results/{area,timing,power}/rx-dmult/`,
`results/area/rx-dmult-demod/`, `results/timing/rx-dmult-full/` and `results/validation/dmult*/`;
those of § 8 are in `results/compare/all-branches/` and `results/{area,timing,power}/all-branches/`,
on `ble-rx-dm`, `ble-rx-dmult` and the measurement branches of the TX comparison. The relative
links below resolve on `ble-rx-dmult`. Those of `ble-rx-aa` (§ 12) are on `ble-rx-aa`, in
`results/{area,timing,power}/rx-aa/` and `results/validation/aa-*/`.

## 1. The branches

| Branch | What it is | RTL (`verilog/`) | Measured as |
|---|---|---|---|
| `master` | upstream BTLE (`upstream-baseline`) with the corrections of the product audit and the lint closure (`PRODUCT_VALIDATION.md`, `LINT_CLOSURE.md`): the reference | tree `6e670a6`, commit `fca6ac6` | defaults |
| `ble-rx-dm` | corrected `master` + B1 | `btle_rx.v`, `btle_rx_core.v` (`EXTERNAL_DEMOD`, default 0, keeps it upstream's when used alone), new `gfsk_demodulation_shared.v`; elsewhere only comments and file lists; tree `66ff2c2`, commit `38755a0` | defaults (B1 is not a parameter) |
| `ble-rx-dmult` | `ble-rx-dm` with one multiplier in the shared demodulator | `gfsk_demodulation_shared.v` only; tree `ee1dabc`, commit `f00bd9e` (later commits add harness, results and documents) | defaults (not a parameter) |
| `ble-rx-aa` | corrected `master` + one Access Address detector for the 8 phases (§ 12) | `btle_rx.v`, `btle_rx_core.v` (`EXTERNAL_AA_SEARCH`, default 0, keeps its own search when used alone), new `search_unique_bit_sequence_shared.v`, `RX_ADV_AA_ONLY` (default 0) passed down by `btle_phy.v` and `btle_controller.v`; elsewhere only comments and file lists; tree `a4ca2f5`, commit `6ea9a0e` | defaults, and `RX_ADV_AA_ONLY=1` |
| `ble-rx-shared` | `ble-rx-dm` + the AA detector of `ble-rx-aa` + one decoder (scrambler, CRC, state machine) for the 8 phases (§ 13) | `btle_rx.v` (no `btle_rx_core`), new `rx_decoder_shared.v`, `search_unique_bit_sequence_shared.v` of `ble-rx-aa`, `RX_ADV_AA_ONLY` as on `ble-rx-aa`; elsewhere only comments and file lists; tree `1317e6c`, commit `ed8412f` | defaults, and `RX_ADV_AA_ONLY=1` |
| `ble-rx-adv` | `ble-rx-shared` + the packet memory for Legacy Advertising: 64-word packet RAMs, and one RAM for the 8 phases (§ 14) | `btle_rx.v` (`RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM`, default 0), new `rx_pdu_ram_shared.v`, both passed down by `btle_phy.v` and `btle_controller.v`; elsewhere only comments and file lists; tree `f1edf2c`, commit `198d9a6d` | `RX_ADV_AA_ONLY=1` with `RX_PDU_ADV_DEPTH=1`, and with both |
| `ble-rx-min` | `ble-rx-adv` + the demodulator of one multiplier of `ble-rx-dmult` + the packet RAM on one single-port macro; the receiver of Legacy Advertising by default (§ 15) | `gfsk_demodulation_shared.v` of `ble-rx-dmult`, new `rx_pdu_ram_1rw.v`, `RX_PDU_1RW` in `btle_rx.v`, `btle_phy.v`, `btle_controller.v`; the defaults of `RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM`, `RX_PDU_1RW` set to 1; tree `054fd05`, commit `a0e3fe47` | its defaults, and `RX_PDU_1RW=0` |
| `ble-rx-best` | `ble-rx-min` with the packet RAM sized to Legacy Advertising: 42 words per phase, packed, in one single-port macro of 336 × 8; each phase holds the word of its octet (§ 16) | `rx_pdu_ram_1rw.v` (`PHASE_WORDS`), `RX_PDU_PACKED` (default 1) in `btle_rx.v`, `btle_phy.v`, `btle_controller.v`, `sdpram_one_clk.v` (`DEPTH`); commit `3d92ea80` | its defaults |
| `ble-rx-micro` | `ble-rx-best` with **one stored phase**, chosen when the Access Address is found (the middle of the phases that find it), one decoder and the 42 octets in registers, no packet macro; and a **demodulator of 8 bits**, the samples saturated; **not equivalent**: about 2 dB of sensitivity (§ 17) | `rx_one_phase.v` (new), `RX_ONE_PHASE` (default 1), `RX_IQ_BITS`/`RX_IQ_SHIFT` (default 8/0) in `btle_rx.v`, `RX_ONE_PHASE` in `btle_phy.v`, `btle_controller.v`; commit `745e4bba` | its defaults |

How they relate:

```
master  (corrected: upstream-baseline + the product audit + the lint closure, fca6ac6)
 └─ ble-rx-dm      B1 (aa8a014 … 88f2250 on the history of ble-opt), then the audit and the
     │             lint closure as on master: master + B1, 38755a0
     ├─ ble-rx-dmult  from 38755a0: one multiplier (f00bd9e); its harness (aa83311 … 15fca3b), the
     │                activity parser of ble-tx-min (2cf1e17), results and documents
     └─ ble-rx-shared from 38755a0: the harness and AA detector of ble-rx-aa (9f3385f), one decoder
         │            for the 8 phases (ed8412f), its validation; compose with ble-rx-dmult (no common block)
         └─ ble-rx-adv  from 2b1fd10a: the packet memory for Legacy Advertising (198d9a6d), its
             │          validation (2064b38f, 103d9d37)
             └─ ble-rx-min  from cf3d4ca9: the demodulator of ble-rx-dmult (89549adc), the packet RAM on
                 │          one single-port macro (c2ea1118, a0e3fe47), the defaults of Legacy Advertising
                 └─ ble-rx-best  from 8e63e5ef: 42 words per phase packed in a 336 × 8 macro, the word held
                     │           with the octet (3d92ea80), its validation; the harness rx_per (951150c7)
                     └─ ble-rx-micro  from d9080f36: one stored phase chosen at the Access Address and an
                                      8-bit demodulator (745e4bba); not equivalent: rx_per, its validation
 └─ ble-rx-aa      from fca6ac6: one Access Address detector (76d1175 … 6ea9a0e), the harness of
                   ble-tx-min (a079b76), its own validation; independent of B1 (no common block)
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
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | −9.2 % | −2.7 % [+7.2 %] |
| … over the 5 scenarios | — | −5.9 to −12.7 % | −1.9 to −4.6 % [+3.8 to +11.5 %] |
| Clock pins (load × toggles) | 9.03 × 10⁸ fF | −13.7 % | −13.6 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 059.7 (+1.8 %) | 1 205.1 (+15.7 %) |
| Nets with activity > 10 %, `mixed` | 879 | 4 119 (×4.7) | 3 397 (×3.9) |
| RAM-port toggles, `mixed` | 3 165 890 | unchanged | unchanged |
| Functions removed | — | **none** | **none**; `btle_rx` takes at most one sample every two clocks, which is what the RF interface gives (§ 7) |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical, every output, 5/5 | identical, every output, 5/5 |
| Validation (§ 6) | the reference | formal ≡ upstream (B1), lockstep, 270/270 | formal ≡ `ble-rx-dm`, lockstep 60/60, 270/270 |

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

| Scenario | `master` | `ble-rx-dm` | `ble-rx-dmult` | `ble-rx-dmult` / `ble-rx-dm` |
|---|---:|---:|---:|---:|
| `rx` | 1.26 × 10⁹ fF | −12.7 % | −2.7 % | **+11.5 %** |
| `tx` | 1.04 × 10⁹ fF | −7.8 % | −4.3 % | +3.8 % |
| `mixed` | 1.30 × 10⁹ fF | −9.2 % | −2.7 % | **+7.2 %** |
| `idle` | 1.29 × 10⁹ fF | −5.9 % | −1.9 % | +4.3 % |
| `idle0` | 0.97 × 10⁹ fF | −8.3 % | −4.6 % | +4.0 % |

The measures of the TX comparison, scenario `mixed`:

| Measure | `master` | `ble-rx-dm` | `ble-rx-dmult` |
|---|---:|---:|---:|
| Toggles / cycle, non-clock nets | 1 041.3 | 1 059.7 (+1.8 %) | 1 205.1 (+15.7 %) |
| Nets with activity > 10 % | 879 | 4 119 (×4.7) | 3 397 (×3.9) |
| `btle_rx` toggles / cycle | 839.8 | 859.2 (+2.3 %) | 1 004.7 (+19.6 %) |
| `btle_ll` / Gaussian filter / rest of `btle_tx` toggles / cycle | 32.3 / 40.1 / 48.1 | 32.4 / 40.1 / 47.1 | 32.3 / 40.1 / 47.1 |
| Clock network (CK-pin load × toggles) | 9.03 × 10⁸ | −13.7 % | −13.6 % |
| Memory: toggles on RAM ports | 3 165 890 | unchanged | unchanged |
| Data load × toggles | 3.99 × 10⁸ | +0.9 % | **+22.2 %** |
| **Data + clock proxy** | 1.30 × 10⁹ | **−9.2 %** | **−2.7 %** |

Every block but `btle_rx` stays within 0.2 % of `master` on both branches (`btle_tx` 2.1 %, the same
on both: its netlist, § 3.1). Every scenario, every block and the most active nets:
[`rx-dmult/summary.md`](../../results/compare/rx-dmult/summary.md).

- **B1 on the audited RTL behaves as before the audit.** It removes 652 flip-flops, so the
  clock-pin load falls 13.7 % in every scenario, and the proxy 5.9 to 12.7 % (−5.9 to −12.9 %
  before, § 8). With real packets the receiver also switches less (`rx`: `btle_rx` −10.5 %); without
  traffic it switches more (`btle_rx` +15.6 % in `idle` and +146 % in `tx`, receiver input zero):
  the shared unit's valid and enable network toggles on every sample whatever the data.
- **One multiplier costs activity that two did not.** `ble-rx-dmult` keeps the clock load of
  `ble-rx-dm` (3 flip-flops more, −13.6 %) but its data switching rises: `btle_rx` switches 16.9 %
  more than on `ble-rx-dm` in `mixed`, the data load of the controller is +22.2 % against `master`
  where `ble-rx-dm`'s is +0.9 %, and the proxy is 3.8 to 11.5 % above `ble-rx-dm`'s, most with real
  packets (`rx`). It stays 1.9 to 4.6 % below `master`'s. The data load of `btle_rx` rises by
  3.6 × 10⁷ fF over `ble-rx-dm` with the receiver's input at zero (`idle0`), where the multiplier's
  operands do not move: the select of the operand multiplexers and the enable of the decision
  register, which change on every clock; and by up to 1.26 × 10⁸ fF with packets (`rx`): the
  multiplier's operands now alternate on every clock between (i[n−8], q[n]) and (i[n], q[n−8]),
  where each multiplier of `ble-rx-dm` saw one pair move to the next sample's.
- **Holding the operands does not help.** Selecting the E1 operands only in the clock of a capture,
  and holding those of E2 in every other clock (two lines, [`rx-dmult-hold`](../../results/power/rx-dmult-hold/README.txt)),
  moves the proxy by −0.12 to −0.36 %, with every output identical: at 8 MS/s the two clocks of a
  sample are all the clocks, so there is no idle clock whose operands could be held. It is not adopted.
- **The proxy is not power**: it has no wires and no glitches (zero-delay simulation). A multiplier
  array glitches in real gates, which the proxy does not count on either branch.

## 6. Evidence per branch

| | `ble-rx-dm` (B1) | `ble-rx-dmult` |
|---|---|---|
| Formal proof of the change | shared ≡ the 8 upstream demodulators, **unbounded at 16 bits**, 4/4 mutants rejected (`SHARED_DEMOD_VALIDATION.md`, before the audit) | time-shared ≡ the shared demodulator of `ble-rx-dm`, **unbounded at 16 bits** (every product a free value constrained to be one function of its operands) and with the real multipliers at 4 bits; 6/6 mutants rejected by both; without the contract the proof fails, as it must; the contract proved on `clock_domain_conversion_iq`, unbounded |
| Lockstep of `btle_rx` | against upstream: 60/60, 25 367 270 clocks, 4/4 mutants (before the audit) | against corrected `master`, samples never in consecutive clocks: **60/60, 37 054 155 clocks, 17 558 142 samples, 7 521 packets with a correct CRC, 1 632 resets**; 6/6 mutants; samples in consecutive clocks caught |
| The product audit's matrix, 270 cases | 270/270 (lint closure, reference `9d6c383`) | 270/270 |
| TX waveforms (Python decoding; and through the RTL receiver) | 167/167 | 167/167, and 167/167 decoded by its RTL receiver |
| Lint gate (Verilator 5.020, `--Wall`) | 1/1 configuration, 12 reviewed exceptions | 1/1 configuration, 12 reviewed exceptions |
| Illegal-state recovery, lint negative controls | 3 checks, 10 controls | 3 checks, 12 controls |
| Product defects, RF contract, Gaussian tail, bit repeat, register readback, Yosys structure | 4/4; pass; pass; pass; pass; pass | 4/4; 12/12 scenarios, 2/2 mutants; pass; pass; pass; pass |
| Harness tests | 23 passed | 21 of 23 passed, 2 skipped (they need `REGRESSION_VECTORS`) |
| Gate-level lockstep, run `rx-dmult` | identical, every output, 5/5 | identical, every output, 5/5 |
| Report | `docs/Validation/SHARED_DEMOD_VALIDATION.md`, `LINT_CLOSURE.md` | `docs/Validation/RX_DMULT_VALIDATION.md` (on `ble-rx-dmult`) |

## 7. What each branch gives up

| Branch | Functions removed |
|---|---|
| `master` | none (the reference) |
| `ble-rx-dm` | **none**: B1 is an exact rewrite; the 8 phase hypotheses and the CRC-based selection are kept, and the shared unit takes a sample on every clock |
| `ble-rx-dmult` | **none at the controller**: the same outputs as `ble-rx-dm` on every clock. `btle_rx` and its shared demodulator take **at most one sample every two clocks** (`iq_valid` never high in two consecutive clocks), where upstream's took one per clock; the RF interface gives one every second clock at most, by construction (proved, § 6), and the upstream testbenches deliver one every other clock. A `btle_rx` reused alone, with a source that can give samples on consecutive clocks, would need that source to keep a gap |
| `ble-rx-aa` | **none**: the one detector is an exact rewrite (proved, § 12.5); any Access Address, the 8 phase hypotheses and the CRC selection are kept; samples on consecutive clocks are accepted, as upstream |
| `ble-rx-aa` (advertising only) | **every Access Address but the advertising one** (`0x8E89BED6`): data-channel packets are never detected (`unique_bit_sequence` is ignored). On advertising traffic the same outputs as `master` on every clock (proved, § 12.5) |
| `ble-rx-shared` | **none**: the shared decoder and the one AA detector are exact rewrites (proved, § 13.5); any Access Address, the 8 phase hypotheses and the CRC selection are kept; samples on consecutive clocks are accepted, as upstream |
| `ble-rx-shared` (advertising only) | **every Access Address but the advertising one**, as `ble-rx-aa` (advertising only): data-channel packets are never detected. On advertising traffic the same outputs as `master` on every clock |
| `ble-rx-adv` depth | as `ble-rx-shared` (advertising only), and **packets of more than 63 octets** (the counter of a phase wraps at 64; no Legacy Advertising packet has more than 42) |
| `ble-rx-adv` one RAM | the same, and **the original's content of the raw read port outside the packet** (the words at and above each phase's counter, one read after a change of `best_phase`): the words of the packet are exact (proved, § 14.5) and are all the controller and the firmware read |
| `ble-rx-min` | as `ble-rx-adv` one RAM, and a read of the packet RAM that needs the port in the clock of a forced write keeps the previous word that clock: a reader must change its address on 64 consecutive clocks of the AXI clock to meet one (the link layer: 48 at most per packet); the newest word of a phase is read right 4 clocks after its octet. A sample never in two consecutive clocks (the demodulator of one multiplier; the controller gives it) |
| `ble-rx-best` | as `ble-rx-min`, and **decodes of more than 42 octets** keep only their first 42 (63 on `ble-rx-min`; no Legacy Advertising packet has more than 42) |

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

1. **One multiplier is enough, and it is exact.** The receiver takes one sample every two clocks,
   so the two products of a sample fit in two clocks of one multiplier. `ble-rx-dmult` has the
   outputs of `ble-rx-dm`, and so of upstream's 8 demodulators, on every clock: proved unbounded at
   16 bits, simulated in lockstep against corrected `master` (60/60, 37 million clocks), through the
   product audit's 270 cases and the 167 packets decoded by its RTL receiver, and at gate level in the
   five activity scenarios.
2. **It removes one 16 × 16 multiplier**: 1 612 cells (−31.9 %) and 1 801.1 µm² (−25.6 %) of the
   shared demodulator, 1 532 cells (−15.4 %) of `btle_rx` and 1 240 (−4.9 %) of the controller
   against `ble-rx-dm`; −53.8 % of the controller's cells against corrected `master`. The flip-flops
   stay (the first product replaces two operand registers), and no SRAM moves.
3. **Its price is one condition and some activity.** `btle_rx` takes at most one sample every two
   clocks, which the RF interface gives by construction (proved). And the one multiplier switches
   more than the two did: the activity proxy is 3.8 to 11.5 % above `ble-rx-dm`'s, still 1.9 to 4.6 %
   below `master`'s; B1 keeps most of its activity saving, from the clock pins of 652 flip-flops.
4. **Timing does not separate them.** The controller's worst path is the transmitter's Gaussian tail
   on all three (3.357–3.410 ns); in the receiver the multiplexer adds 0.12 ns on a path that no
   sample takes, within the flow's noise, a factor of 31 at 16 MHz.
5. **B1 is the receiver's change that matters; the shared multiplier refines it.** B1 removes 72.9 %
   of `btle_rx` on the audited RTL, as before the audit; one multiplier takes another 15.4 % of what
   is left, for area, at the cost of activity: the choice between `ble-rx-dm` and `ble-rx-dmult` is
   area against switching.

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
  proof with the real 16 × 16 multipliers did not close (1 h at k = 4 with bitwuzla, 90 min at k = 1
  with bitwuzla and yices; `RX_DMULT_VALIDATION.md`), and with them it is proved at 4 bits. The equivalence with upstream's 8 demodulators follows from
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

## 12. `ble-rx-aa`: one Access Address detector (run `rx-aa`)

Run `rx-aa`, on `ble-rx-aa`: the RTL of `6ea9a0e` (tree `a4ca2f5`), the area, timing and activity
flows of `ble-tx-min` (`a079b76`; the same files as those of run `rx-dmult`, but for
`scripts/compare/`, which run `rx-aa` does not use), the same liberty, corrected `master` (`fca6ac6`)
as the reference of timing and activity, and **the vector set of run `all-branches`**
(`d53f2d49ed8db456`). `master` measures here what it measures in run `rx-dmult`: 52 357 cells and
74 684.8 µm² for the controller, 36 782 cells for `btle_rx`, a controller of 3.410 ns. Two
configurations: `ble-rx-aa` (defaults: `RX_ADV_AA_ONLY=0`, the address configurable) and
`ble-rx-aa` (advertising only: `RX_ADV_AA_ONLY=1` on every level). **The second does not receive
data-channel packets** (§ 7): its figures are the additional saving of that restriction, not an
improvement equivalent to the first.

### 12.1 What changes

Upstream's `search_unique_bit_sequence`, one per phase, shifts the phase's bits into a 32-bit
register and compares it with the address: hit when the last 32 bits are the address. The
detector of `ble-rx-aa` (`search_unique_bit_sequence_shared.v`) serves the 8 phases at once, and
uses one property of `btle_rx`: sample n goes to phase n mod 8, and each phase's demodulator answers
a fixed 3 clocks later, so the phases deliver their bits **one per clock at most and always in
their cyclic order**; a decoder restart resets every phase in the same clock, so the order also
holds across restarts (proved, § 12.5).

- **`RX_ADV_AA_ONLY=0`**: all the bits go into one shift line, the newest at the top. The bits of one
  phase are every 8th place of it, so the last 32 bits of the phase that has just delivered a bit are
  **fixed taps** of the line, and **one 32-bit comparator** serves every phase, with no multiplexer.
  The line needs (32 − 1) × 8 + 1 = **249 flip-flops** (upstream: 256); the comparator, its zero-address
  rule and the 8 one-clock-delayed valid bits are those of upstream.
- **`RX_ADV_AA_ONLY=1`**: the address is fixed to the advertising one, and each phase keeps only **the
  length of the longest prefix of the address that ends its bits** (0–32, 6 bits): the pattern
  automaton of Knuth-Morris-Pratt, with its 66-entry next-state table computed at elaboration. The
  8 states rotate as the line does (the phase that delivers the next bit is always the oldest), so
  **one next-state table** serves them: 8 × 6 = **48 flip-flops**.

### 12.2 The comparison

Differences against corrected `master`.

| | `master` | `ble-rx-aa` | `ble-rx-aa` (advertising only) |
|---|---|---|---|
| **Content** | upstream BTLE, corrected | **one AA comparator** for the 8 phases, exact | **one AA automaton**, advertising address only |
| Configuration measured | defaults | defaults (`RX_ADV_AA_ONLY=0`) | `RX_ADV_AA_ONLY=1` on every level |
| **Receives data-channel packets** | yes | **yes** | **no** |
| Access Address search: flip-flops / comparators | 8 × 33 / 8 | 257 / **1** | **56** / none (one next-state table) |
| The search alone: cells / µm² (§ 12.3) | 8 × 202 / 8 × 324.8 | 1 007 / 1 897.6 (−37.7 % / −27.0 %) | **297 / 491.3 (−81.6 % / −81.1 %)** |
| **Std cells, `btle_rx`** | 36 782 | 36 496 (−286, −0.8 %) | **35 598 (−1 184, −3.2 %)** |
| Flip-flops, `btle_rx` | 2 068 | 2 061 (−7) | **1 860 (−208, −10.1 %)** |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 48 126.1 (−493.1, −1.0 %) | **46 731.4 (−1 887.8, −3.9 %)** |
| **Std cells, `btle_controller`** | 52 357 | 52 073 (−284, −0.5 %) | **51 303 (−1 054, −2.0 %)** |
| Flip-flops | 4 722 | 4 715 (−7) | **4 514 (−208, −4.4 %)** |
| Cell area (µm²) | 74 684.8 | 73 990.0 (−694.8, −0.9 %) | **72 694.9 (−1 989.9, −2.7 %)** |
| SRAM bits | 1 136 070 | 1 136 070 | 1 136 070 |
| Min period of the controller at 16 MHz (62.5 ns) | 3.410 ns | 3.360 ns | 3.397 ns |
| Worst path of the controller | the Gaussian tail of the transmitter | the same | the same |
| Min period of `btle_rx` alone | 1.991 ns | 1.886 ns | 1.974 ns |
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | **+9.1 %** | **−3.0 %** |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | +8.8, +7.2, +9.1, +10.3, +7.5 % | −3.1, −3.2, −3.0, −2.9, −3.2 % |
| Clock pins (load × toggles) | 9.03 × 10⁸ fF | −0.1 % | −4.4 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 341.1 (+28.8 %) | 1 017.4 (−2.3 %) |
| Nets with activity > 10 %, `mixed` | 879 | 2 169 (×2.5) | 975 (+10.9 %) |
| RAM-port toggles, `mixed` | 3 165 890 | unchanged | unchanged |
| Functions removed | — | **none** | **every Access Address but `0x8E89BED6`** |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical, every output | identical, every output (advertising traffic) |
| Validation (§ 12.5) | the reference | formal ≡ upstream's 8 searches (unbounded), lockstep 60/60, 270/270 | formal ≡ upstream's 8 searches fed the advertising address (unbounded), lockstep 60/60 |

### 12.3 Area

[`results/area/rx-aa/`](../../results/area/rx-aa/): the 17 tops for `ble-rx-aa` and its advertising
configuration (`search_unique_bit_sequence_shared` included), the 16 of `master` and of
`upstream-baseline`.

| Top | `master` | `ble-rx-aa` | `ble-rx-aa` (advertising only) |
|---|---:|---:|---:|
| `search_unique_bit_sequence` (one upstream copy) | 202 | 202 | 202 |
| `search_unique_bit_sequence_shared` | — | 1 007 (257 FFs) | 297 (56 FFs) |
| `btle_rx_core` | 4 477 | 4 470 | 4 470 |
| **`btle_rx`** | 36 782 | **36 496** (−0.8 %) | **35 598** (−3.2 %) |
| `btle_tx` | 5 823 | 6 234 (+7.1 %) | 6 234 (+7.1 %) |
| `btle_phy` | 42 844 | 42 355 (−1.1 %) | 41 432 (−3.3 %) |
| `clock_domain_conversion_iq`, `auxiliary_daemon`, `btle_ll` | 186, 299, 9 523 | the same | the same |
| **`btle_controller`** | **52 357** | **52 073** (−0.5 %) | **51 303** (−2.0 %) |

- **The one comparator saves little, because the flip-flops stay**: 8 detectors of 202 cells each
  become one of 1 007; standalone that is −609 cells, but most of an upstream detector is its 33
  flip-flops (with their load enables), and the line keeps 249 of the 256. Inside `btle_rx` the
  saving is smaller still, −286 cells, −493.1 µm² (−1.0 %): synthesised together, the 8 upstream
  copies already cost less than 8 standalone ones.
- **The automaton removes the flip-flops**: 297 cells and 56 flip-flops for the 8 phases, −1 184 cells
  and −208 flip-flops in `btle_rx` (−3.9 % of its area), the receiver's whole Access Address search
  reduced to a fifth.
- **`btle_tx` moves by +411 cells with the same RTL**: the flow noise of § 3.1 (here
  `gfsk_modulation`, 5 195 → 5 419). The controller therefore saves less than `btle_rx` and
  `btle_phy`; `btle_rx` is the figure of the change.
- **`RX_ADV_AA_ONLY=1` is applied as a default** (`AREA_DEFAULTS`, `DUT_DEFAULTS`: the archived copy
  edited, every substitution checked), not with `-chparam`: Yosys 0.68 asserts
  (`rtlil_bufnorm.cc:681`) on `hierarchy -top btle_rx -chparam RX_ADV_AA_ONLY 1`. Through `-chparam`
  on `btle_controller`, which works, the controller measured 51 064 cells, 239 fewer: the same flow
  noise.

### 12.4 Timing and activity

Timing ([`results/timing/rx-aa/`](../../results/timing/rx-aa/), `STA_SET=full`): the controller's worst
path stays the Gaussian tail of the transmitter (3.360 and 3.397 ns against 3.410 ns), and `btle_rx`'s
the demodulator's multiply (1.886 and 1.974 ns against 1.991 ns): the detector is on neither, and the
differences are inside the flow's noise (0.15 ns).

Activity ([`results/power/rx-aa/`](../../results/power/rx-aa/)): the harness of § 5, against corrected
`master`, every output and register compared on every clock in the 5 scenarios — **no mismatch** in
either configuration (`master` against itself: 0.0 % everywhere).

| `btle_rx`, scenario `mixed` | `master` | `ble-rx-aa` | `ble-rx-aa` (advertising only) |
|---|---:|---:|---:|
| Toggles / cycle | 839.8 | 1 136.8 (+35.4 %) | 822.6 (−2.1 %) |
| Data load × toggles | 3.42 × 10⁸ | +35.0 % | +0.4 % |
| Clock pins | 3.93 × 10⁸ | −0.3 % | **−10.1 %** |
| Nets with activity > 10 % | 257 | 1 541 | 367 |

- **The one-comparator line costs activity**: every bit shifts all 249 flip-flops of the line, where
  upstream shifted the 32 of one phase, so the line's data toggles grow about 8 times. The data
  capacitance of `btle_rx` rises by a third and the whole controller's data + clock by **7–10 %** in
  every scenario; the clock load hardly moves (the flip-flops had load enables before and after).
- **The automaton saves activity**: 208 fewer flip-flops (−10.1 % of `btle_rx`'s clock pins,
  −4.4 % of the controller's), and a 6-bit state that changes once per bit: **−2.9 to −3.2 %** of the
  controller's data + clock in every scenario.

### 12.5 Evidence

| | `ble-rx-aa` | `ble-rx-aa` (advertising only) |
|---|---|---|
| Formal proof of the change ([`aa-formal`](../../results/validation/aa-formal/formal_aa/)) | the 8 upstream searches ≡ the one detector, **unbounded** (k-induction, boolector), in `btle_rx`'s own environment: its sample distribution and the real demodulators' valid timing, every phase's bit, the resets, the decoder restarts and the address all free on every clock; helper invariants: the cyclic order of the phases since the last restart, and each phase's 32 bits equal to its taps on the line | the same, with the address assumed advertising; invariant: each phase's state is the longest prefix of the address that ends its 32 bits |
| Mutants of the proof | the same miter with a 4-bit address, bounded from reset (40 clocks), passes on the design; **3/3 mutants** give a failing trace of the hit flags (taps one place off, hit one clock early, zero address not replaced) | **2/2** (the state of the wrong phase read, a hit one state early) |
| Lockstep of `btle_rx` against corrected `master` ([`aa-lockstep`](../../results/validation/aa-lockstep/)): every output and the 8 per-phase hit flags on every clock; packets of examples 0–2 between noise, samples on every clock / every other / at random, resets, decoder restarts forced in both designs at random | **60/60**, 25 591 005 clocks, 17 597 919 samples, 3 501 hits, 557 packets with a correct CRC, 1 679 resets, 33 930 forced restarts; address per segment: the packet's (6 437), random (3 167), zero (3 179); **5/5 mutants** | **60/60**, 25 457 074 clocks, 17 618 865 samples, 2 378 hits, 1 755 resets, 34 050 forced restarts, the advertising address; **5/5 mutants** |
| The product audit's matrix, 270 cases ([`aa-matrix`](../../results/validation/aa-matrix/)) | **270/270** | 220 PASS, **50 ERROR: exactly the 50 data-channel cases the reference receives** (examples 1 and 2, `btle_rx_tb` and `btle_controller_tb`); the other 22 data-channel cases are rejected by both; example 0 90/90 ([`aa-matrix-adv`](../../results/validation/aa-matrix-adv/)) |
| Lint gate (Verilator 5.020, `--Wall`, [`aa-lint`](../../results/validation/aa-lint/)) | **2/2 configurations** (`RX_ADV_AA_ONLY` 0 and 1), 12 reviewed exceptions, none new | |
| Gate-level lockstep, run `rx-aa` | 5/5 scenarios, every output identical | 5/5 scenarios, every output identical |

### 12.6 Conclusions for `ble-rx-aa`

- **The exact detector (`RX_ADV_AA_ONLY=0`) is a small saving with an activity cost**: one comparator
  instead of 8, −286 cells and −1.0 % of `btle_rx`'s area (−0.5 % of the controller), every function
  kept and proved, but **+7 to +10 %** of the controller's switched capacitance, because the shared
  line shifts all its 249 flip-flops on every bit. The flip-flops are most of upstream's search, and
  sharing the comparator cannot remove them.
- **Restricting the receiver to advertising (`RX_ADV_AA_ONLY=1`) removes the flip-flops**: −208
  flip-flops, −3.9 % of `btle_rx`'s area (−2.7 % of the controller) and −3 % of its switched
  capacitance in every scenario, at the price of every data-channel packet. It is an option for a
  device that only advertises or scans, not a free improvement.
- **The change is independent of B1**: it touches the search, B1 the demodulator, and no block is
  common; on top of `ble-rx-dm`, whose `btle_rx` is 9 973 cells, the same −1 184 cells would be about
  12 % of the receiver.

### 12.7 Reproducing

From WSL, at the root of `ble-rx-aa` (the vectors: `results/compare/tx-pdu-we/vectors.tar.gz` of
`ble-tx-min`, set `d53f2d49ed8db456`, extracted in `/tmp/vec`; `ADV` sets `RX_ADV_AA_ONLY=1` as the
default of `search_unique_bit_sequence_shared.v`, `btle_rx.v`, `btle_phy.v` and `btle_controller.v`,
as `file:RX_ADV_AA_ONLY=1` items):

```bash
RTL_REV=fca6ac6 scripts/area/run_area.sh <label>/master <the 16 tops that exist on master>
RTL_REV=6ea9a0e scripts/area/run_area.sh <label>/ble-rx-aa
RTL_REV=6ea9a0e AREA_DEFAULTS="$ADV" scripts/area/run_area.sh <label>/ble-rx-aa-adv
DUT_REV=6ea9a0e DUT_PARAMS= scripts/timing/run_sta.sh <label>/ble-rx-aa 62.5 fca6ac6
DUT_REV=6ea9a0e DUT_PARAMS= DUT_DEFAULTS="$ADV" scripts/timing/run_sta.sh <label>/ble-rx-aa-adv 62.5 fca6ac6
DUT_REV=6ea9a0e DUT_PARAMS= VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-aa 100000 1 fca6ac6
DUT_REV=6ea9a0e DUT_PARAMS=RX_ADV_AA_ONLY=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-aa-adv 100000 1 fca6ac6
scripts/validation/formal_aa/run_formal_aa.sh <label> fca6ac6
scripts/validation/rx_aa_lockstep/run_rx_aa_lockstep.sh <label> line 20 200 fca6ac6
scripts/validation/rx_aa_lockstep/run_rx_aa_lockstep.sh <label> adv 20 200 fca6ac6
scripts/validation/run_rx_regression.sh <label> fca6ac6
DUT_DEFAULTS="$ADV" scripts/validation/run_rx_regression.sh <label>-adv fca6ac6
python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```

In WSL, a worktree of this repository created from Windows needs `GIT_DIR` and `GIT_WORK_TREE`
(its `.git` file names a Windows path, which git 2.43 does not follow).

## 13. `ble-rx-shared`: one decoder for the 8 phases (run `rx-shared`)

Run `rx-shared`, on `ble-rx-shared`: the RTL of `ed8412f` (tree `1317e6c`), the flows of run `rx-aa`
(the files of `ble-rx-aa` at `06bee7b`, § 12), the same liberty, corrected `master` (`fca6ac6`) as the
reference of timing and activity, and **the vector set of run `all-branches`** (`d53f2d49ed8db456`).
Four configurations measured together: `master`, `ble-rx-dm` (the base of this branch, to isolate the
change), `ble-rx-shared` (defaults: `RX_ADV_AA_ONLY=0`) and `ble-rx-shared` (advertising only:
`RX_ADV_AA_ONLY=1` on every level, as in § 12). `master` and `ble-rx-dm` measure here exactly what they
measure in runs `rx-dmult` and `rx-aa`. **The advertising configuration does not receive data-channel
packets** (§ 7): its figures are the additional saving of that restriction.

### 13.1 What changes

`ble-rx-shared` is `ble-rx-dm` (B1) with the Access Address detector of `ble-rx-aa` and **one decoding
chain for the 8 phases**: `btle_rx` has no `btle_rx_core` left. Each upstream `btle_rx_core` holds, per
phase, a scrambler (7-bit LFSR), a CRC24, the octet register, a 12-bit bit counter, the payload length
and a state machine; `rx_decoder_shared.v` keeps that state for every phase and **one copy of the
logic**, by two properties of `btle_rx`:

- **The phases deliver their bits one per clock at most, in cyclic order since the last decoder
  restart**, and a restart resets every phase (proved for `ble-rx-dm`'s demodulator, § 13.5; § 12
  proves it for upstream's).
- **A phase is busy only in the 4 clocks of its bit** (`t`: the scrambler takes it; `t+1`: the hit,
  the CRC and one clock of the state machine; `t+2`: the payload length, `octet_valid`, `decode_end`,
  `crc_ok`; `t+3`: those pulses cleared), and is at a fixed point until its next bit, 8 clocks later
  at the earliest.

So the bit is registered, and in the next clock one copy of the logic computes the three clocks
`t+1 … t+3` of the phase from its stored state (the state machine of `btle_rx_core` transcribed as a
function, applied three times); the pulses go through two shared registers and are seen in `t+3`, as in
the original. The state that survives between two bits of a phase, **54 bits** (the two LFSRs, the
state, the bit counter, the payload length), sits in a **ring of 8 entries that rotates by one entry
per bit**: by the cyclic order, the phase of a bit is always the oldest entry, so no multiplexer
reads it. Each phase **keeps its own octet register**, written at `t+1` and `t+3` as in the original,
because `serial_in_ram_out` writes it into the phase's packet RAM on every clock (the RAM's next word
shows it). The payload length and `crc_ok` are shared: `btle_rx` uses them only with their valid.

### 13.2 The comparison

Differences against corrected `master`, and, in brackets, against `ble-rx-dm`.

| | `master` | `ble-rx-dm` | `ble-rx-shared` | `ble-rx-shared` (advertising only) |
|---|---|---|---|---|
| **Content** | upstream BTLE, corrected | B1 | **B1 + one AA detector + one decoder** for the 8 phases, exact | the same, the AA automaton of § 12 (advertising address only) |
| Configuration measured | defaults | defaults | defaults (`RX_ADV_AA_ONLY=0`) | `RX_ADV_AA_ONLY=1` on every level |
| **Receives data-channel packets** | yes | yes | **yes** | **no** |
| Decoding chains (scrambler, CRC, state machine) | 8 | 8 | **1**, the state of 8 | **1**, the state of 8 |
| **Std cells, `btle_rx`** | 36 782 | 9 973 (−72.9 %) | **9 094 (−75.3 %)** [−879, −8.8 %] | **8 186 (−77.7 %)** [−1 787, −17.9 %] |
| Flip-flops, `btle_rx` | 2 068 | 1 416 | 1 413 [−3] | 1 212 [−204] |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 15 741.1 | 14 633.5 [−1 107.6, −7.0 %] | 13 147.3 [−2 593.8, −16.5 %] |
| **Std cells, `btle_controller`** | 52 357 | 25 445 (−51.4 %) | **25 109 (−52.0 %)** [−336, −1.3 %] | **24 257 (−53.7 %)** [−1 188, −4.7 %] |
| Flip-flops | 4 722 | 4 070 | 4 067 | 3 866 |
| Cell area (µm²) | 74 684.8 | 41 794.7 | 40 863.5 [−931.2, −2.2 %] | 39 480.5 [−2 314.2, −5.5 %] |
| SRAM bits | 1 136 070 | 1 136 070 | 1 136 070 | 1 136 070 |
| Min period of the controller / worst path | 3.410 ns, the transmitter's Gaussian tail | 3.374 ns, the same | 3.460 ns, the same | 3.402 ns, the same |
| Min period of `btle_rx` alone / worst path | 1.991 ns, a demodulator multiply | 1.849 ns, the shared demodulator's multiply | 1.795 ns, the same | 1.808 ns, the same |
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | −9.2 % | **+12.8 %** [+24.3 %] | **+0.9 %** [+11.1 %] |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | −12.7, −7.8, −9.2, −5.9, −8.3 % | +9.6, +15.4, +12.8, +17.3, +16.4 % | −2.3, +5.4, +0.9, +4.3, +5.7 % |
| Clock pins (load × toggles), `mixed` | 9.03 × 10⁸ fF | −13.7 % | −13.8 % | −18.0 % |
| Data load × toggles, `mixed` | 3.99 × 10⁸ fF | +0.9 % | +73.0 % | +43.6 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 059.7 | 1 528.3 | 1 215.2 |
| Nets with activity > 10 %, `mixed` | 879 | 4 119 | 6 332 | 5 185 |
| RAM-port toggles, `mixed` | 3 165 890 | unchanged | unchanged | unchanged |
| Functions removed | — | none | **none** | **every Access Address but `0x8E89BED6`** |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical | identical, every output | identical, every output (advertising traffic) |
| Validation (§ 13.5) | the reference | § 6 | formal ≡ the 8 chains (unbounded), lockstep 60/60 against `master` and 60/60 against `ble-rx-dm`, 270/270, lint 2/2 | the same proof; lockstep 60/60; the matrix as § 12 (220 + the 50 data-channel cases) |

### 13.3 Area

[`results/area/rx-shared/`](../../results/area/rx-shared/): the 16 tops of `master`, and of `ble-rx-dm`
with its shared demodulator, and every top of `ble-rx-shared` in both configurations.

| Top | `master` | `ble-rx-dm` | `ble-rx-shared` | `ble-rx-shared` (advertising only) |
|---|---:|---:|---:|---:|
| `gfsk_demodulation_shared` | — | 5 051 (412 FFs) | 5 051 (412 FFs) | 5 051 (412 FFs) |
| `search_unique_bit_sequence_shared` | — | — | 1 007 (257 FFs) | 297 (56 FFs) |
| `rx_decoder_shared` | — | — | **2 137 (564 FFs), 4 188.7 µm²** | 2 137 (564 FFs) |
| `btle_rx_core` (one upstream copy, alone) | 4 477 | 4 468 | 4 468 | 4 468 |
| **`btle_rx`** | 36 782 | 9 973 | **9 094** | **8 186** |
| `btle_tx` | 5 823 | 5 947 | 6 079 | 6 221 |
| `btle_phy` | 42 844 | 15 934 | 15 211 | 13 984 |
| **`btle_controller`** | **52 357** | **25 445** | **25 109** | **24 257** |

- **The decoder of the 8 phases is 2 137 cells**: its 564 flip-flops (the ring, 8 × 54; the octet
  registers, 8 × 8; the registered bit and the two output stages) and one copy of the logic. On top of
  `ble-rx-dm`, `btle_rx` loses 879 cells (−8.8 %), of which about 290 are the one AA comparator
  (`ble-rx-aa` saves 286 on `master`, § 12.3) and **about 590 the shared decoder**; with the AA automaton,
  1 787 (−17.9 %).
- **The flip-flops stay**, as in § 12: the state of 8 phases is still 8 states (1 416 → 1 413 in
  `btle_rx`); what goes is the logic around it. The 7 bits per phase that are always 0 or unused at rest
  (the scrambler's output register and the state machine's pulses) are not kept in the ring, but the
  registered bit and the two output stages take about as many: the decoder holds 564 flip-flops
  (432 + 64 + 68) where the 8 chains held 552 (8 × 69).
- **`btle_tx` moves by +132 and +274 cells with the same RTL**: the flow noise of §§ 3.1 and 12.3. The
  controller therefore saves less than `btle_rx`; `btle_rx` is the figure of the change.
- **The estimate of the plan was −13 to −20 % of `btle_rx` for the decoder alone; it is about −6 %**
  (about 590 of 9 973 cells): after B1 each chain with its search is about 570 cells (`btle_rx_core`
  alone, 4 468, less its own demodulator, 3 899), and its logic was already small next to its state,
  which stays.

### 13.4 Timing and activity

Timing ([`results/timing/rx-shared/`](../../results/timing/rx-shared/), `STA_SET=full`): the controller's
worst path stays the transmitter's Gaussian tail (3.460 and 3.402 ns against 3.410 ns), and
`btle_rx`'s the shared demodulator's multiply (1.795 and 1.808 ns against 1.849 ns on `ble-rx-dm`): the
decoder computes three clocks of the state machine in one, but on 54 bits of state, and is on neither.

Activity ([`results/power/rx-shared/`](../../results/power/rx-shared/)): the harness of § 5, against
corrected `master`, every output and register compared on every clock in the 5 scenarios — **no
mismatch** in any configuration (`master` against itself: 0.0 % everywhere).

- **The ring costs activity.** It shifts its 432 flip-flops on every bit, where each upstream chain
  updated its own state once per bit of its phase: the data capacitance of the controller rises by 73 %
  in `mixed` and the data + clock proxy by **+9.6 to +17.3 %** against `master`, **+24 %** against
  `ble-rx-dm`; the clock load does not move (the flip-flops had and keep their enables). With the AA
  automaton the 201 flip-flops fewer bring it back to **−2.3 to +5.7 %**.
- **An indexed bank instead of the ring halves that cost, for part of the area** (measured, not
  adopted; [`rx-shared-bank`](../../results/power/rx-shared-bank/README.txt)): the state of each phase
  written only when its bit is processed, read through a one-hot multiplexer. `btle_rx` 9 386 cells
  (−5.9 % against `ble-rx-dm`, 292 more than the ring) and the proxy **+3.1 to +9.3 %** against `master`;
  in the advertising configuration 8 451 cells and **−4.2 to −9.2 %**. Every output identical to `master`
  in the 5 scenarios, lockstep 3/3 with 6/6 mutants. The choice between the two is area against
  switching, as for `ble-rx-dmult` (§ 5): the ring is the branch's design because it is the smaller and
  it is the one proved.

| `mixed` | `btle_rx` cells | toggles / cycle, non-clock | data | clock | **data + clock** |
|---|---:|---:|---:|---:|---:|
| `master` | 36 782 | 1 041.3 | 3.99 × 10⁸ fF | 9.03 × 10⁸ fF | 1.30 × 10⁹ fF |
| `ble-rx-dm` | 9 973 | 1 059.7 | +0.9 % | −13.7 % | −9.2 % |
| `ble-rx-shared`, ring | 9 094 | 1 528.3 | +73.0 % | −13.8 % | **+12.8 %** |
| `ble-rx-shared`, bank (alternative) | 9 386 | 1 483.7 | +50.1 % | −13.8 % | +5.8 % |
| `ble-rx-shared` (advertising only), ring | 8 186 | 1 215.2 | +43.6 % | −18.0 % | +0.9 % |
| `ble-rx-shared` (advertising only), bank (alternative) | 8 451 | 1 160.7 | +19.3 % | −18.0 % | **−6.6 %** |

### 13.5 Evidence

| | `ble-rx-shared` | `ble-rx-shared` (advertising only) |
|---|---|---|
| The order of the phases ([`shared-formal`](../../results/validation/shared-formal/formal_shared/)) | in `btle_rx` with `gfsk_demodulation_shared`, free inputs: the bit valids one-hot and in cyclic order since the last restart, **unbounded** | the same (the demodulator does not depend on the address) |
| Formal proof of the decoder | the 8 decoding chains of `ble-rx-dm`'s `btle_rx_core` ≡ `rx_decoder_shared`, **unbounded** (k-induction, bitwuzla), in `btle_rx`'s environment: bits, restarts, address, channel and CRC seed free on every clock, the hit flags of the reference's searches; property: per phase, the octet on every clock and every pulse with its value; helper invariants: the phase of every ring entry, each phase at rest equal to its entry and well formed, the three phases in flight equal to their entry once the remaining clocks are applied. **7/7 mutants** make the proof fail (1 counterexample from reset, 6 induction failures); a 30-clock BMC from reset passes | the decoder does not depend on the address: the same proof; the AA automaton is proved in § 12.5 |
| Lockstep of `btle_rx` ([`shared`](../../results/validation/shared/)): every output and, per phase, the hit, the octet on every clock, `octet_valid`, `payload_length(_valid)`, `decode_end`, `crc_ok`; samples on every clock / every other / at random, resets, forced restarts, address and channel / CRC seed changed in mid-segment | against corrected `master`: **60/60**, 25 481 557 clocks, 17 575 367 samples, 17 435 phase hits, 103 790 phase octets, 1 245 phase decode ends, 419 packets with a correct CRC, 34 033 forced restarts; against `ble-rx-dm`: **60/60**, the same stimulus; **7/7 mutants** each (on packets decoded to the end) | against corrected `master`: **60/60**, 25 399 407 clocks, 11 848 phase hits, 83 244 phase octets, 62 phase decode ends (the long advertising packet seldom ends between forced restarts); **7/7 mutants** (with restarts 128 times rarer) |
| The product audit's matrix, 270 cases ([`shared-matrix`](../../results/validation/shared-matrix/)) | **270/270** | 220 PASS, **50 ERROR: the 50 data-channel cases the reference receives** (examples 1 and 2, `btle_rx_tb` and `btle_controller_tb`), as in § 12.5 |
| Lint gate (Verilator 5.020, `--Wall`) | **2/2 configurations**, 12 reviewed exceptions, none new | |
| Gate-level lockstep, run `rx-shared` | 5/5 scenarios, every output identical | 5/5 scenarios, every output identical |
| Report | `docs/Validation/RX_SHARED_VALIDATION.md` (on `ble-rx-shared`) | |

### 13.6 Conclusions for `ble-rx-shared`

- **One decoder for the 8 phases is exact and proved**, and costs no function: every Access Address,
  the 8 phase hypotheses and the CRC selection are kept, and samples on consecutive clocks are accepted,
  as on `ble-rx-dm`.
- **It saves less than estimated, because the state stays**: −879 cells of `btle_rx` against
  `ble-rx-dm` (−8.8 %), of which about 590 are the decoder; with the advertising automaton −1 787
  (−17.9 %), the smallest receiver built: 8 186 cells, −77.7 % against `master`.
- **The ring costs activity**: +24 % of the switched capacitance against `ble-rx-dm`; the indexed bank
  halves that cost for 292 cells, and in the advertising configuration it is 6.6 % below `master`. For a
  receiver that only advertises or scans, **`ble-rx-shared` with the AA automaton and the bank** would be
  the smallest receiver that also switches less than upstream's.

### 13.7 Reproducing

From WSL, at the root of `ble-rx-shared` (the vectors: `results/compare/all-branches/vectors.tar.gz`,
set `d53f2d49ed8db456`, extracted in `/tmp/vec`; `ADV` as in § 12.7):

```bash
T16="crc24 scramble bit_repeat_upsample gauss_filter vco gfsk_modulation btle_tx gfsk_demodulation search_unique_bit_sequence btle_rx_core btle_rx btle_phy clock_domain_conversion_iq auxiliary_daemon btle_ll btle_controller"
RTL_REV=fca6ac6 scripts/area/run_area.sh <label>/master $T16
RTL_REV=ble-rx-dm scripts/area/run_area.sh <label>/ble-rx-dm $T16 gfsk_demodulation_shared
RTL_REV=ed8412f scripts/area/run_area.sh <label>/ble-rx-shared
RTL_REV=ed8412f AREA_DEFAULTS="$ADV" scripts/area/run_area.sh <label>/ble-rx-shared-adv
DUT_REV=ed8412f DUT_PARAMS= scripts/timing/run_sta.sh <label>/ble-rx-shared 62.5 fca6ac6
DUT_REV=ed8412f DUT_PARAMS= DUT_DEFAULTS="$ADV" scripts/timing/run_sta.sh <label>/ble-rx-shared-adv 62.5 fca6ac6
DUT_REV=ed8412f DUT_PARAMS= VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-shared 100000 1 fca6ac6
DUT_REV=ed8412f DUT_PARAMS=RX_ADV_AA_ONLY=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-shared-adv 100000 1 fca6ac6
scripts/validation/formal_shared/run_formal_shared.sh <label>
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> line 20 200 fca6ac6
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> adv 20 200 fca6ac6
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> line 20 200 ble-rx-dm
scripts/validation/run_rx_regression.sh <label>-matrix fca6ac6
DUT_DEFAULTS="$ADV" scripts/validation/run_rx_regression.sh <label>-matrix-adv fca6ac6
python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```
(`ble-rx-dm` and `master` are measured with the same timing and activity commands, `DUT_REV=ble-rx-dm`
and `DUT_REV=fca6ac6`.)

## 14. `ble-rx-adv`: the packet memory for Legacy Advertising (run `rx-adv`)

Run `rx-adv`, on `ble-rx-adv`: the RTL of `198d9a6d` (tree `f1edf2c`), the flows of run `rx-shared` (with
`PDU_CONTRACT`, below), the same liberty, corrected `master` (`fca6ac6`) as the reference of timing and
activity, **the vector set of run `all-branches`** (`d53f2d49ed8db456`), and the RAM macros generated by
OpenRAM (FreePDK45, run `openram-rx-adv`). Four configurations measured together, all but `master`
advertising only (`RX_ADV_AA_ONLY=1`): `master`; `ble-rx-shared` (advertising only, the base of this
branch, to isolate the change); `ble-rx-adv` **depth** (`RX_PDU_ADV_DEPTH=1`) and `ble-rx-adv` **one
RAM** (`RX_PDU_ADV_DEPTH=1`, `RX_PDU_ONE_RAM=1`), each parameter set on every level. `master` and
`ble-rx-shared` (advertising only) measure here what they measure in run `rx-shared`. **None of the
three receives data-channel packets** (§ 7).

### 14.1 What changes

The receiver keeps, for each of its 8 sampling phases, the octets the decoder delivers, in a RAM of 512
octets (`serial_in_ram_out`): **8 × 4 096 bits**, the largest block of the receiver. The longest packet
of Legacy Advertising is the 2-octet header, 37 octets of payload and the 3-octet CRC, **42 octets**.
Two parameters of `btle_rx`, default 0 (the original):

- **`RX_PDU_ADV_DEPTH = 1`: 64 words per phase.** The 8 RAMs and their write counters shrink to 6 bits;
  the high 3 bits of the read address are unused.
- **`RX_PDU_ONE_RAM = 1`: one RAM for the 8 phases** (`rx_pdu_ram_shared.v`), the words `{phase, word}`
  of one `sdpram_two_clk`; each phase keeps its 6-bit write counter. **One write port serves the 8
  phases** because the decoder gives an `octet_valid` to one phase per clock at most (the one output
  stage of `rx_decoder_shared`, § 13, proved one-hot): in a clock with a valid octet, it is written at
  `{its phase, its counter}`, where the phase's own RAM wrote it. The phase is part of the read address,
  `{best_phase, word}`, where `btle_rx` read the 8 RAMs and selected the phase after them.

With both, the 8 RAMs of 512 × 8 become **one RAM of 512 × 8**. The memory is not the original's
everywhere, and does not need to be: `serial_in_ram_out` writes on **every clock** (`write_enable` tied
to 1), so the word at a phase's counter always shows the octet being assembled; the one RAM writes only
valid octets. The words of the packet, below the counter, are equal while the counter is below 64; after
a change of `best_phase`, one read still shows the old phase's word. That is the contract of
`rx_pdu_ram_shared.v`, proved in § 14.5, and what the controller consumes: `btle_ll` copies words 0 to
`len` − 1 of `best_phase` after `decode_end` (`len`, the phase's counter), and the firmware reads bits 16
and 15:8 of register 49. Outside the packet, the raw read port (`ext_rx_pdu_octet_mem_data`, bits 7:0 of
register 49) differs (§ 14.4).

### 14.2 The comparison

Differences against corrected `master`, and, in brackets, against `ble-rx-shared` (advertising only).

| | `master` | `ble-rx-shared` (advertising only) | `ble-rx-adv` depth | `ble-rx-adv` one RAM |
|---|---|---|---|---|
| **Content** | upstream BTLE, corrected | B1 + one AA automaton + one decoder (§ 13) | the same + **64-word packet RAMs** | the same + **one packet RAM** for the 8 phases, 64 words each |
| Configuration measured | defaults | `RX_ADV_AA_ONLY=1` | + `RX_PDU_ADV_DEPTH=1` | + `RX_PDU_ADV_DEPTH=1`, `RX_PDU_ONE_RAM=1` |
| **Receives data-channel packets** | yes | no | no | no |
| **RX packet RAMs** | 8 × (512 × 8) | 8 × (512 × 8) | **8 × (64 × 8)** | **1 × (512 × 8)** |
| SRAM bits, `btle_rx` | 32 768 | 32 768 | **4 096** (−87.5 %) | **4 096** (−87.5 %) |
| **RX packet RAM macros, OpenRAM 1RW1R (µm²)** | 189 663.8 | 189 663.8 | **58 986.4 (−68.9 %)** | **23 708.0 (−87.5 %)** |
| Std cells, `btle_rx` | 36 782 | 8 186 (−77.7 %) | 8 101 (−78.0 %) [−85, −1.0 %] | 8 110 (−78.0 %) [−76, −0.9 %] |
| Flip-flops, `btle_rx` | 2 068 | 1 212 | 1 188 [−24] | 1 188 [−24] |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 13 147.3 | 12 957.7 [−189.6, −1.4 %] | 13 020.7 [−126.6, −1.0 %] |
| **Receiver: `btle_rx` cells + its RAM macros (µm²)** | 238 283.0 | 202 811.1 (−14.9 %) | **71 944.1 (−69.8 %)** [−64.5 %] | **36 728.7 (−84.6 %)** [**−81.9 %**] |
| Std cells, `btle_controller` | 52 357 | 24 257 (−53.7 %) | 23 889 (−54.4 %) [−368, −1.5 %] | 24 075 (−54.0 %) [−182, −0.8 %] |
| Flip-flops | 4 722 | 3 866 | 3 842 | 3 842 |
| Cell area (µm²) | 74 684.8 | 39 480.5 | 39 013.4 | 39 237.4 |
| SRAM macros / bits, controller | 15 / 1 136 070 | 15 / 1 136 070 | 15 / 1 107 398 | **8** / 1 107 398 |
| Min period of the controller / worst path | 3.410 ns, the transmitter's Gaussian tail | 3.402 ns, the same | 3.462 ns, the same | 3.346 ns, the same |
| Min period of `btle_rx` alone / worst path | 1.991 ns, a demodulator multiply | 1.808 ns, the shared demodulator's multiply | 1.806 ns, the same | 1.844 ns, the same |
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | +0.9 % | **+0.8 %** [−0.0 %] | **+0.6 %** [−0.2 %] |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | −2.3, +5.4, +0.9, +4.3, +5.7 % | −2.3, +5.2, +0.8, +4.3, +5.6 % | −2.5, +5.0, +0.6, +4.0, +5.3 % |
| Clock pins (load × toggles), `mixed` | 9.03 × 10⁸ fF | −18.0 % | −18.5 % | −18.5 % |
| Data load × toggles, `mixed` | 3.99 × 10⁸ fF | +43.6 % | +44.6 % | +44.0 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 215.2 | 1 226.7 | 1 216.2 |
| RAM-port toggles, `mixed` | 3 165 890 | unchanged | unchanged | 3 131 320 (−1.1 %) |
| **RX packet RAM write accesses** | 8 per clock | 8 per clock | 8 per clock | **one per valid octet: at most 8 per 64 samples** |
| RX packet RAM energy | not characterized (§ 14.4) | the same | the same | the same macro as `master`'s, **one instead of 8**: its clock and leakage energy ÷ 8 |
| Functions removed | — | every Access Address but `0x8E89BED6` | the same; packets of more than 63 octets | the same |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical, every output | identical, every output | identical but the raw packet-RAM read port outside the packet (`PDU_CONTRACT`) |
| Validation (§ 14.5) | the reference | § 13 | formal ≡ the 8 RAMs under the contract (unbounded), lockstep 60/60 `adv` and `line`, the matrix as § 13 (220 + the 50 data-channel cases), lint 8/8 | the same proof; lockstep 60/60 against `ble-rx-shared` and against `master`, `adv` and `line`; the matrix as § 13 |

### 14.3 Area

[`results/area/rx-adv/`](../../results/area/rx-adv/): the 16 tops of `master`, every top of `ble-rx-shared`
(advertising only) and of `ble-rx-adv` in both configurations. The flow reads the RAMs as black boxes
and counts their bits; their area comes from OpenRAM
([`results/area/openram-rx-adv/`](../../results/area/openram-rx-adv/summary.md)).

| Top | `master` | `ble-rx-shared` (advertising only) | `ble-rx-adv` depth | `ble-rx-adv` one RAM |
|---|---:|---:|---:|---:|
| `rx_pdu_ram_shared` (alone: 8 counters, the write select) | — | — | — | 260 (48 FFs), 467.6 µm² |
| **`btle_rx`** | 36 782 | 8 186 | **8 101** | **8 110** |
| `btle_tx` | 5 823 | 6 221 | 5 942 | 6 251 |
| `btle_phy` | 42 844 | 13 984 | 14 083 | 14 199 |
| **`btle_controller`** | **52 357** | **24 257** | **23 889** | **24 075** |

| OpenRAM macro (FreePDK45, 1RW1R: one port per clock) | Words × bits | Width × height (µm) | Area (µm²) | µm² per bit |
|---|---|---|---:|---:|
| `sram_1rw1r_8x512` | 512 × 8 | 146.120 × 162.250 | 23 708.0 | 5.79 |
| `sram_1rw1r_8x64` | 64 × 8 | 100.375 × 73.457 | 7 373.3 | 14.40 |

- **The gain is in the memory, not in the cells.** In the advertising receiver of § 13 the 8 packet
  RAMs are **93.5 %** of `btle_rx`'s area (189 663.8 of 202 811.1 µm²); its logic was already
  reduced to 13 147.3 µm². The cells move little: the 8 counters lose 3 bits each (−24 flip-flops), and
  in the one-RAM configuration the 8-to-1 multiplexer of the reads goes and a write select of the 8
  octets comes (`btle_rx` −85 and −76 cells).
- **One RAM is worth far more than shorter RAMs**: a macro's periphery (decoders, sense amplifiers,
  ports) does not shrink with its words, so a 64-word macro costs 14.40 µm² per bit against 5.79; 8 of
  them are 58 986.4 µm², one RAM of the same 4 096 bits 23 708.0. The receiver, cells and macros,
  falls from 202 811.1 to **71 944.1 µm² (−64.5 %)** with the depth, and to **36 728.7 µm² (−81.9 %)**
  with one RAM: **−84.6 % against `master`**.
- **`btle_tx` moves by −279 and +30 cells with the same RTL**: the flow noise of §§ 3.1, 12.3 and
  13.3; the controller moves by it, so `btle_rx` and the macros are the figures of the change.
- A single-port macro (1RW) is not usable as is: the decoder writes on the baseband clock and the link
  layer reads on the AXI clock, both at any time; it would need an arbiter between the two.

### 14.4 Timing and activity

Timing ([`results/timing/rx-adv/`](../../results/timing/rx-adv/), `STA_SET=full`): the controller's worst
path stays the transmitter's Gaussian tail (3.462 and 3.346 ns against 3.410 ns; the spread is the flow
noise of `btle_tx`), and `btle_rx`'s the shared demodulator's multiply (1.806 and 1.844 ns against
1.808 ns). The macros have no timing model in this flow: the one RAM's address path (`{best_phase, word}`)
ends at a macro input and is not timed against its setup.

Activity ([`results/power/rx-adv/`](../../results/power/rx-adv/)): the harness of § 5, against corrected
`master`. **Depth**: every output and register read compared on every clock in the 5 scenarios — no
mismatch. **One RAM**: compared that way it fails at cycle 21 410 of `rx` and `mixed`, before the first
packet, on the raw read port only (`0x80`, the octet being assembled at the counter, against `0x00`;
[`ble-rx-adv-one-strict`](../../results/power/rx-adv/ble-rx-adv-one-strict/runs.txt)): the difference of
the contract. The run kept is `PDU_CONTRACT=1` (new in `run_activity.sh`): the raw read port and bits 7:0
of register 49 left out, every other output on every clock and every other register read compared,
the 17 packets of `rx` and 9 of `mixed` read through register 40 among them — no mismatch.

- **The switching proxy does not move** (+0.8 and +0.6 % in `mixed`, against +0.9 % for § 13): the 24
  counter flip-flops fewer take 0.6 % off the clock pins of `ble-rx-shared`, and the RAM ports of the
  one RAM toggle 1.1 % less in `mixed`.
- **What the proxy does not see is the RAMs' own energy.** It counts pin capacitance × toggles; a write
  enable tied to 1 does not toggle, but every clock is then a write of 8 RAMs. The one RAM writes once
  per valid octet: each sample gives a bit to one phase, and a phase completes an octet every 8 of its
  bits, so each phase writes at most once per 64 samples, **at most 8 writes per 64 samples** for the 8
  phases (they can come in a burst, one per clock), where the 8 RAMs make 8 per clock: **at least 64
  times fewer write accesses** over any 64 samples (128 in the controller, which gives a sample at most
  every second clock).
- **No energy figure for the RAMs.** The project's SPICE characterization of OpenRAM macros
  (`results/power/sram-char/`, `CHANGES.md` 2026-10-05) covers only one-port macros: the two-port
  (1RW1R) 512 × 8 of every configuration here did not finish in 6 h of ngspice. The analytical Liberty
  files of run `openram-rx-adv` charge every clock edge the same, selected or not, and their leakage is
  about 20 times below the settled SPICE one of comparable one-port macros (0.70 µW for a 64 × 8 against
  15.02 µW for a 256 × 8): they are not used for energy. What holds whatever the model: the one RAM is
  one macro where there were 8 identical ones, with the same two clocks, so the energy its clocks and
  its leakage cost is divided by 8, and its accesses are fewer still.

| `mixed` | RX packet RAM (µm²) | `btle_rx` cells | toggles / cycle, non-clock | data | clock | **data + clock** |
|---|---:|---:|---:|---:|---:|---:|
| `master` | 189 663.8 | 36 782 | 1 041.3 | 3.99 × 10⁸ fF | 9.03 × 10⁸ fF | 1.30 × 10⁹ fF |
| `ble-rx-shared` (advertising only) | 189 663.8 | 8 186 | 1 215.2 | +43.6 % | −18.0 % | +0.9 % |
| `ble-rx-adv` depth | 58 986.4 | 8 101 | 1 226.7 | +44.6 % | −18.5 % | +0.8 % |
| `ble-rx-adv` one RAM | **23 708.0** | 8 110 | 1 216.2 | +44.0 % | −18.5 % | **+0.6 %** |

### 14.5 Evidence

| | `ble-rx-adv` depth | `ble-rx-adv` one RAM |
|---|---|---|
| Formal proof of the packet memory ([`adv-formal`](../../results/validation/adv-formal/formal_adv/result.txt)) | 8 `serial_in_ram_out` of 512 words (read at the full address, the phase selected after the reads) ≡ 8 of 64 words, under the contract, **unbounded** (k-induction, bitwuzla); octets, valids (one phase per clock), resets, read phase and address free on every clock; every RAM abstracted to one watched word at a free address | the same against `rx_pdu_ram_shared`, 8 × 64 words, **unbounded**; and 8 × 512 words (`RX_PDU_ONE_RAM` alone), **unbounded**. **7/7 mutants** make the proof fail (1 counterexample from reset, 6 induction failures), two of them on the contract: one counter value wider, and no condition on the read phase |
| Lockstep of `btle_rx` ([`adv`](../../results/validation/adv/)): every output and per-phase signal exactly on every clock, the packet-RAM read under the contract (the testbench mirrors the counters) | `adv` against `ble-rx-shared`: **60/60**, 25 487 072 clocks, 84 095 phase octets, 755 418 reads compared; `line`: **60/60**, 1 112 316 reads; **3/3 mutants** each | `adv` against `ble-rx-shared` and against corrected `master`: **60/60** each, 755 418 reads compared each; `line`: **60/60**, 1 119 942 reads; `RX_PDU_ONE_RAM` alone, `line`: **60/60**; **7/7 mutants** (6/6 alone) each |
| The product audit's matrix, 270 cases ([`adv-matrix-*`](../../results/validation/)) | 220 PASS, **50 ERROR: the 50 data-channel cases**, case by case those of `ble-rx-shared` (advertising only) | the same; and **270/270** with `RX_PDU_ONE_RAM` alone |
| Lint gate (Verilator 5.020, `--Wall`) | **8/8 configurations**, 12 reviewed exceptions, none new | |
| Gate-level lockstep, run `rx-adv` | 5/5 scenarios, every output identical | 5/5 scenarios under `PDU_CONTRACT`; the strict comparison fails on the raw read port, as the contract says |
| Report | `docs/Validation/RX_ADV_VALIDATION.md` (on `ble-rx-adv`) | |

### 14.6 Conclusions for `ble-rx-adv`

- **The memory was the receiver.** After §§ 12–13 the logic of the advertising receiver is 13 147.3
  µm² and its 8 packet RAMs 189 663.8 µm²: 93.5 %. Sized for the 42 octets of Legacy Advertising and
  merged into one, they become one 512 × 8 RAM of 23 708.0 µm², and the receiver, cells and macros, falls
  by **81.9 %** against `ble-rx-shared` (advertising only) and by **84.6 %** against `master`.
- **One RAM, not only shorter RAMs**: the depth alone gives −64.5 %, because small macros are mostly
  periphery; the one RAM is the configuration of the product. It is exact on the words of the packet,
  proved, and differs only on the raw read port outside the packet, which nothing in the controller or
  the firmware reads.
- **It costs no cells and no switching** (`btle_rx` −76 cells, the proxy −0.2 %), writes the RAM at
  least 64 times less often, in one macro instead of 8 identical ones.
- **What it gives up**: the restriction of § 12 (the advertising address only), packets of more than
  63 octets (no Legacy Advertising packet has more than 42), and the original's content of the raw read
  port outside the packet; an external host on the bare-metal PHY interface must read the packet as
  `btle_ll` does.

### 14.7 Reproducing

From WSL, at the root of `ble-rx-adv` (the vectors: `results/compare/all-branches/vectors.tar.gz`, set
`d53f2d49ed8db456`, extracted in `/tmp/vec`; `ADV` as in § 12.7; `DEPTH` and `ONE` set
`RX_PDU_ADV_DEPTH=1` and `RX_PDU_ONE_RAM=1` as defaults of `btle_rx.v`, `btle_phy.v` and
`btle_controller.v`; `TOPS_SH` the tops of `ble-rx-shared`, without `rx_pdu_ram_shared`):

```bash
scripts/area/run_openram.sh <label> sram_1rw1r_8x64 sram_1rw_8x64 sram_1rw1r_8x512
RTL_REV=fca6ac6 scripts/area/run_area.sh <label>/master $T16
RTL_REV=ble-rx-shared AREA_DEFAULTS="$ADV" scripts/area/run_area.sh <label>/ble-rx-shared-adv $TOPS_SH
RTL_REV=198d9a6d AREA_DEFAULTS="$ADV $DEPTH" scripts/area/run_area.sh <label>/ble-rx-adv-depth
RTL_REV=198d9a6d AREA_DEFAULTS="$ADV $DEPTH $ONE" scripts/area/run_area.sh <label>/ble-rx-adv-one
DUT_REV=ble-rx-shared DUT_PARAMS= DUT_DEFAULTS="$ADV" scripts/timing/run_sta.sh <label>/ble-rx-shared-adv 62.5 fca6ac6
DUT_REV=198d9a6d DUT_PARAMS= DUT_DEFAULTS="$ADV $DEPTH" scripts/timing/run_sta.sh <label>/ble-rx-adv-depth 62.5 fca6ac6
DUT_REV=198d9a6d DUT_PARAMS= DUT_DEFAULTS="$ADV $DEPTH $ONE" scripts/timing/run_sta.sh <label>/ble-rx-adv-one 62.5 fca6ac6
DUT_REV=fca6ac6 DUT_PARAMS= VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/master 100000 1 fca6ac6
DUT_REV=ble-rx-shared DUT_PARAMS=RX_ADV_AA_ONLY=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-shared-adv 100000 1 fca6ac6
DUT_REV=198d9a6d DUT_PARAMS="RX_ADV_AA_ONLY=1 RX_PDU_ADV_DEPTH=1" VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-adv-depth 100000 1 fca6ac6
DUT_REV=198d9a6d DUT_PARAMS="RX_ADV_AA_ONLY=1 RX_PDU_ADV_DEPTH=1 RX_PDU_ONE_RAM=1" PDU_CONTRACT=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-adv-one 100000 1 fca6ac6
```
(the validation commands: `RX_ADV_VALIDATION.md` § 4.)

## 15. `ble-rx-min`: one multiplier and one single-port packet RAM (run `rx-min`)

Run `rx-min`, on `ble-rx-min`: the RTL of `a0e3fe47` (tree `054fd05`), the flows of run `rx-adv`
(with `PDU_CONTRACT` for the gate-level comparison, § 14.4), the same liberty, corrected `master`
(`fca6ac6`) as the reference of timing and activity, **the vector set of run `all-branches`**
(`d53f2d49ed8db456`), and the OpenRAM macros of runs `openram-rx-adv` and `openram-tx` (the
single-port 512 × 8). Four configurations measured together, all but `master` advertising only:
`master`; `ble-rx-adv` (one two-port RAM of 8 × 64 words, the configuration of § 14); `ble-rx-min` with
`RX_PDU_1RW=0` (§ 14's RAM with the demodulator of one multiplier: the effect of that lever alone);
`ble-rx-min` with its defaults (both levers). `master` and `ble-rx-adv` measure here what they measure
in run `rx-adv`. **None of the three receives data-channel packets** (§ 7).

### 15.1 What changes

The two levers left after § 14 that cost no function:

- **One multiplier in the shared demodulator** (`ble-rx-dmult`, § 5): its two products in two
  consecutive clocks; exact when a sample never comes in two consecutive clocks, which
  `clock_domain_conversion_iq` gives the controller.
- **The one packet RAM on a single-port macro** (`RX_PDU_1RW`, `rx_pdu_ram_1rw.v`): OpenRAM's 512 × 8 is
  10 703.9 µm² with one port (1RW) against 23 708.0 µm² with two (1RW1R). One port serves the
  decoder's writes (baseband clock, 16 MHz) and the link layer's reads (the AXI clock, 100 MHz on the
  boards): the macro is clocked by the AXI clock, so the read keeps its one clock; each phase holds its
  octet and the writes cross to the AXI clock (two flip-flops); **the reads take the port first**, a
  write takes the clocks they leave free (forced after 64 clocks of waiting), and a read of the read
  phase's pending word is served from its held octet (the bypass). The port reads only when the output
  must change, otherwise the macro is deselected.

And the defaults of `RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM` and `RX_PDU_1RW` are 1:
the branch, synthesised as it is, is the receiver of Legacy Advertising.

The contract of the packet RAM is § 14's, with **a latency** (the newest word of a phase is read right
4 clocks of the AXI clock after its octet) and **one exception**: a read that needs the port in the
clock of a forced write keeps the previous word that clock, which takes a reader changing its address
on 64 consecutive clocks (the link layer: 48 at most per packet). The first version, in which the
writes took the port first, lost reads that the testbenches of the product audit meet (they read right
after `decode_end`): the matrix found it (18 advertising cases, one PDU byte each), and the design was
changed before the measurements (`RX_MIN_VALIDATION.md` § 1.2).

### 15.2 The comparison

Differences against corrected `master`, and, in brackets, against `ble-rx-adv`.

| | `master` | `ble-rx-adv` | `ble-rx-min`, `RX_PDU_1RW=0` | `ble-rx-min` |
|---|---|---|---|---|
| **Content** | upstream BTLE, corrected | § 14: AA automaton, one decoder, one RAM of 8 × 64 words (1RW1R) | the same + **one multiplier** | the same + **one multiplier** + **the RAM on one single-port macro** |
| Configuration measured | defaults | `RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM` = 1 | the defaults, `RX_PDU_1RW=0` | **the defaults** |
| **Receives data-channel packets** | yes | no | no | no |
| Demodulator multipliers | 16 | 2 | **1** | **1** |
| **RX packet RAM** | 8 × (512 × 8), 1RW1R | 1 × (512 × 8), 1RW1R | 1 × (512 × 8), 1RW1R | **1 × (512 × 8), 1RW** |
| RX packet RAM macros, OpenRAM (µm²) | 189 663.8 | 23 708.0 | 23 708.0 | **10 703.9** |
| Std cells, `btle_rx` | 36 782 | 8 110 | 6 543 [−1 567] | 7 108 [−1 002] |
| Flip-flops, `btle_rx` | 2 068 | 1 188 | 1 191 | 1 323 |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 13 020.7 | 11 234.0 [−1 786.7, −13.7 %] | 12 407.3 [−613.4, −4.7 %] |
| **Receiver: `btle_rx` cells + its RAM macros (µm²)** | 238 283.0 | 36 728.7 (−84.6 %) | 34 942.0 (−85.3 %) [−4.9 %] | **23 111.2 (−90.3 %)** [**−37.1 %**] |
| Std cells, `btle_controller` | 52 357 | 24 075 (−54.0 %) | 22 151 (−57.7 %) | 22 926 (−56.2 %) |
| Cell area, `btle_controller` (µm²) | 74 684.8 | 39 237.4 | 37 106.2 | 38 488.6 |
| SRAM macros / bits, controller | 15 / 1 136 070 | 8 / 1 107 398 | 8 / 1 107 398 | 8 / 1 107 398 |
| Min period of the controller / worst path | 3.410 ns, the transmitter's Gaussian tail | 3.346 ns, the same | 3.442 ns, the same | 3.490 ns, the same |
| Min period of `btle_rx` alone / worst path | 1.991 ns, a demodulator multiply | 1.844 ns, the shared demodulator's multiply | 1.967 ns, the history read into the one multiplier | 2.045 ns, the same |
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | +0.6 % | +6.5 % [+5.8 %] | +8.3 % [+7.6 %] |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | −2.5, +5.0, +0.6, +4.0, +5.3 % | +6.8, +7.8, +6.5, +7.3, +8.6 % | +8.7, +10.2, +8.3, +9.2, +11.1 % |
| Clock pins (load × toggles), `mixed` | 9.03 × 10⁸ fF | −18.5 % | −18.4 % | −15.7 % |
| Data load × toggles, `mixed` | 3.99 × 10⁸ fF | +44.0 % | +62.9 % | +62.6 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 216.2 | 1 324.4 | 1 322.8 |
| RAM-port toggles, `mixed` | 3 165 890 | 3 131 320 | 3 131 320 | 2 922 598 (−7.7 %) |
| RX packet RAM: SPICE-characterized energy | not characterized | not characterized | not characterized | **31.1 µW** at a 16 MHz `clkb`, **62.3 µW** at 100 MHz, + at most 1.2 µW of writes (§ 15.4) |
| Functions removed | — | every Access Address but `0x8E89BED6`; packets of more than 63 octets | the same | the same |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical but the raw packet-RAM read port outside the packet | the same | the same |
| Validation (§ 15.5) | the reference | § 14 | lockstep 60/60 | formal (unbounded), lockstep 60/60 in 5 campaigns, the matrix (220 + the 50 data-channel cases; 270/270 with full function), lint 16/16 |

### 15.3 Area

[`results/area/rx-min/`](../../results/area/rx-min/): the 16 tops of `master`, every top of `ble-rx-adv`
and of `ble-rx-min` in both configurations; the macros from OpenRAM
([`openram-rx-adv`](../../results/area/openram-rx-adv/summary.md), and the single-port 512 × 8 of
[`openram-tx`](../../results/area/openram-tx/summary.md): 85.285 × 125.507 µm).

| Top | `master` | `ble-rx-adv` | `ble-rx-min`, `RX_PDU_1RW=0` | `ble-rx-min` |
|---|---:|---:|---:|---:|
| `gfsk_demodulation_shared` | — | 5 051 (412 FFs), 7 027.7 µm² | **3 439 (415 FFs), 5 226.6 µm²** | 3 439 (415 FFs) |
| `rx_pdu_ram_shared` / `rx_pdu_ram_1rw` (alone) | — | 260 (48 FFs), 467.6 µm² | 260 (48 FFs) | **870 (180 FFs), 1 674.5 µm²** |
| **`btle_rx`** | 36 782 | 8 110 | **6 543** | **7 108** |
| `btle_tx` | 5 823 | 6 251 | 5 724 | 5 979 |
| `btle_phy` | 42 844 | 14 199 | 12 581 | 13 180 |
| **`btle_controller`** | **52 357** | **24 075** | **22 151** | **22 926** |

- **One multiplier: −1 787 µm² of `btle_rx`** (−13.7 %): the demodulator loses a 16 × 16 multiplier
  (−1 612 cells), the largest block of logic left in the receiver.
- **The single-port macro: −13 004 µm² of macro for +1 173 µm² of logic.** The macro goes from
  23 708.0 to 10 703.9 µm²; `rx_pdu_ram_1rw` holds what the crossing and the shared port need: the 8
  held octets (64 flip-flops), the toggles and their synchronizers (32), the pending writes, the wait
  counter, the word shown and its output (about 180 flip-flops against 48), and the bypass.
- **The receiver, cells and macros, falls to 23 111.2 µm²: −37.1 % against `ble-rx-adv`, −90.3 %
  against `master`.** Of that step, 1 786.7 µm² are the multiplier and 11 830.8 µm² the macro.
- **`btle_tx` moves by −527 and −272 cells with the same RTL**: the flow noise of §§ 3.1, 12.3, 13.3
  and 14.3; the controller moves by it.

### 15.4 Timing and activity

Timing ([`results/timing/rx-min/`](../../results/timing/rx-min/), `STA_SET=full`): the controller's worst
path stays the transmitter's Gaussian tail (3.442 and 3.490 ns, the flow noise of `btle_tx`); `btle_rx`'s
becomes **the history read into the one multiplier** (1.967 and 2.045 ns against 1.844 ns with two):
the multiplier now takes its operands through a multiplexer in the clock of the history read, as on
`ble-rx-dmult`; at 16 MHz (62.5 ns) neither matters. The single-port macro and its address path are not
timed (the flow has no timing model for the macros), nor the crossing to the AXI clock, which the
lockstep exercises at 103 MHz.

Activity ([`results/power/rx-min/`](../../results/power/rx-min/)): the harness of § 5 with
`PDU_CONTRACT=1` (§ 14.4), against corrected `master`: every compared output on every clock and every
register read identical in the 5 scenarios, the 17 packets of `rx` and 9 of `mixed` read through
register 40 among them.

- **One multiplier costs switching**, as on `ble-rx-dmult` (§ 5): the data capacitance of the
  controller rises (+44.0 → +62.9 % in `mixed`), the proxy from +0.6 to **+6.5 %** against `master`.
- **The single-port RAM adds its clock-domain logic** (+132 flip-flops on the AXI clock, which in this
  harness is the baseband clock): the clock pins rise from −18.4 to −15.7 %, the proxy to **+8.3 %**;
  the RAM-port toggles fall by 7.7 % (the port reads only when the output must change).
- **The RAM's energy** is now known, the macro being one-port: OpenRAM's SPICE characterization of
  the 512 × 8 1RW ([`sram-char`](../../results/power/sram-char/summary.md), [`sram-leakage`](../../results/power/sram-leakage/summary.md))
  gives a settled leakage of 25.11 µW, 0.372 pJ per clock (deselected, beyond the leakage), and a write
  or a read 1.161 or 1.068 pJ more (ngspice, FreePDK45, TT 1.0 V 25 °C, measured with a 5 ns clock). Clocked at 16 MHz the packet RAM costs **31.1 µW** without
  accesses, at the boards' 100 MHz **62.3 µW**; the writes add at most 1.2 µW (each phase one octet per
  64 samples at 8 MS/s), the reads 1.07 pJ each, only when the reader changes its address. No
  comparison with the two-port RAMs is possible: they were never characterized (§ 14.4).

| `mixed` | RX packet RAM (µm²) | `btle_rx` cells | toggles / cycle, non-clock | data | clock | **data + clock** |
|---|---:|---:|---:|---:|---:|---:|
| `master` | 189 663.8 | 36 782 | 1 041.3 | 3.99 × 10⁸ fF | 9.03 × 10⁸ fF | 1.30 × 10⁹ fF |
| `ble-rx-adv` | 23 708.0 | 8 110 | 1 216.2 | +44.0 % | −18.5 % | +0.6 % |
| `ble-rx-min`, `RX_PDU_1RW=0` | 23 708.0 | 6 543 | 1 324.4 | +62.9 % | −18.4 % | +6.5 % |
| `ble-rx-min` | **10 703.9** | 7 108 | 1 322.8 | +62.6 % | −15.7 % | **+8.3 %** |

### 15.5 Evidence

| | `ble-rx-min` |
|---|---|
| The demodulator ([`min-dmult`](../../results/validation/min-dmult/formal_dmult/result.txt)) | `formal_dmult` of `ble-rx-dmult`: ≡ `ble-rx-dm`'s under its contract, **unbounded** (16 bits with the products abstracted, 4 bits with the multipliers), every mutant rejected |
| The order of the phases, the decoder ([`min-shared-formal`](../../results/validation/min-shared-formal/formal_shared/result.txt)) | `formal_shared` on this demodulator: **unbounded**, 7/7 mutants |
| The single-port packet RAM ([`min-formal`](../../results/validation/min-formal/formal_adv/result.txt)) | `rx_pdu_ram_1rw` ≡ 8 `serial_in_ram_out` of 512 words under its contract, **unbounded** (k-induction, bitwuzla), one clock; the write's completion before its phase's next octet assumed (argued, and counted by the lockstep); the macro never read and written in one clock, a read lost only to a forced write; **14/14 mutants** (10 with a counterexample from reset); § 14's tasks again, 7/7 |
| Lockstep of `btle_rx` ([`min`](../../results/validation/min/)): every output exactly, the packet-RAM read under the contract, the macro's rule, the forced writes and the write count checked; samples never on consecutive clocks; read bursts that force the writes | `adv`, `clkb` = `clk`, against `ble-rx-shared` and against corrected `master`: **60/60** each, 1 241 597 reads compared each, 14/14 mutants; `clkb` at 103 MHz: **60/60**, 7 975 452 reads compared, 2 652 lost to a forced write, 12/12 mutants; `line`: **60/60** (`clkb` = `clk`), **60/60**, 12 271 392 reads compared, 12/12 mutants (103 MHz); `RX_PDU_1RW=0`: **60/60** |
| The product audit's matrix ([`min-matrix-*`](../../results/validation/)) | 220 PASS, **50 ERROR: the 50 data-channel cases**, case by case those of § 13; **270/270** with full function on the single-port RAM; **270/270** with every parameter at 0 |
| Lint gate (Verilator 5.020, `--Wall`) | **16/16 configurations**, 12 reviewed exceptions, none new |
| Gate-level lockstep, run `rx-min` | 5/5 scenarios, `PDU_CONTRACT=1` |
| Report | `docs/Validation/RX_MIN_VALIDATION.md` (on `ble-rx-min`) |

### 15.6 Conclusions for `ble-rx-min`

- **The receiver of Legacy Advertising is 23 111.2 µm², cells and macros: −90.3 % against `master`**,
  −37.1 % against `ble-rx-adv`, with no function given up beyond § 14's.
- **The single-port macro is the larger lever** (−11 831 µm² net), and the harder one: one port
  between two clocks needs a crossing, held octets, a bypass and an order between reads and writes. The
  first order (writes first) lost reads that a real reader meets; the matrix found it, and the reads now
  take the port first, which leaves lost reads only to a reader that changes its address on 64
  consecutive clocks.
- **One multiplier is the smaller one** (−1 787 µm²) and costs switching (+5.8 % of the proxy against
  `ble-rx-adv`); the two together, +7.6 %: the receiver is smaller and switches a little more, and its
  packet RAM, characterized now, draws 31 to 62 µW.
- **With full function** (any Access Address, 512 words per phase) the single-port RAM receives every
  packet of the matrix (270/270): the lever does not depend on advertising, its area for that
  configuration is not measured here.

### 15.7 Reproducing

From WSL, at the root of `ble-rx-min` (the vectors: `results/compare/all-branches/vectors.tar.gz`, set
`d53f2d49ed8db456`, extracted in `/tmp/vec`; `ADV`, `DEPTH`, `ONE` as in § 14.7, `NO1RW` sets
`RX_PDU_1RW=0` in `btle_rx.v`, `btle_phy.v` and `btle_controller.v`; `TOPS_ADV` the tops of `ble-rx-adv`):

```bash
RTL_REV=fca6ac6 scripts/area/run_area.sh <label>/master $T16
RTL_REV=198d9a6d AREA_DEFAULTS="$ADV $DEPTH $ONE" scripts/area/run_area.sh <label>/ble-rx-adv-one $TOPS_ADV
RTL_REV=a0e3fe47 AREA_DEFAULTS="$NO1RW" scripts/area/run_area.sh <label>/ble-rx-min-2port
RTL_REV=a0e3fe47 scripts/area/run_area.sh <label>/ble-rx-min
DUT_REV=198d9a6d DUT_PARAMS= DUT_DEFAULTS="$ADV $DEPTH $ONE" scripts/timing/run_sta.sh <label>/ble-rx-adv-one 62.5 fca6ac6
DUT_REV=a0e3fe47 DUT_PARAMS= DUT_DEFAULTS="$NO1RW" scripts/timing/run_sta.sh <label>/ble-rx-min-2port 62.5 fca6ac6
DUT_REV=a0e3fe47 DUT_PARAMS= scripts/timing/run_sta.sh <label>/ble-rx-min 62.5 fca6ac6
DUT_REV=fca6ac6 DUT_PARAMS= VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/master 100000 1 fca6ac6
DUT_REV=198d9a6d DUT_PARAMS="RX_ADV_AA_ONLY=1 RX_PDU_ADV_DEPTH=1 RX_PDU_ONE_RAM=1" PDU_CONTRACT=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-adv-one 100000 1 fca6ac6
DUT_REV=a0e3fe47 DUT_PARAMS="RX_PDU_1RW=0" PDU_CONTRACT=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-min-2port 100000 1 fca6ac6
DUT_REV=a0e3fe47 DUT_PARAMS= PDU_CONTRACT=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-min 100000 1 fca6ac6
```
(the validation commands: `RX_MIN_VALIDATION.md` § 4. The area, timing and activity of `master`,
`ble-rx-adv` and `RX_PDU_1RW=0` come from the first campaign, at `c2ea1118`, whose RTL of the
demodulator and of `RX_PDU_1RW=0` is that of `a0e3fe47`; `ble-rx-min`'s from the second, at `a0e3fe47`.)

## 16. `ble-rx-best`: the packet RAM sized to Legacy Advertising (run `rx-best`)

Run `rx-best`, on `ble-rx-best`: the RTL of `3d92ea80`, the flows of run `rx-min` (with `PDU_CONTRACT`
for the gate-level comparison), the same liberty, corrected `master` (`fca6ac6`) as the reference of
timing and activity, the vector set of run `all-branches` (`d53f2d49ed8db456`), and the single-port
336 × 8 macro of run `openram-rx-best`. `ble-rx-best` is measured with its defaults; `master`,
`ble-rx-adv` and `ble-rx-min` are those of run `rx-min` (§ 15), the same flows and vectors. **It does
not receive data-channel packets** (§ 7).

### 16.1 What changes

`ble-rx-min`'s macro has 512 words, 64 per phase, of which a Legacy Advertising packet uses 42 at most
(2 octets of header, 37 of payload, 3 of CRC). `RX_PDU_PACKED` (default 1 on the branch,
`rx_pdu_ram_1rw.v` parameter `PHASE_WORDS` = 42) keeps **42 words per phase, packed at
`phase × 42 + word`, in one single-port macro of 336 × 8**:

- the address is a multiply by a constant and an add; **a write beyond a phase's 42 words is dropped**
  (it would land in the next phase's): only a decode of more than 42 octets, noise taken for a packet,
  reaches it;
- **each phase holds the word of its octet with the octet** (`held_word`). On `ble-rx-min` the write took
  its word from the counter when it was served, and a hit resetting the counter while the write waited
  sent it to word 63 of its phase, which no read of the contract sees; packed, word 63 of phase *k* is in
  phase *k* + 1. The unbounded proof found it (`RX_BEST_VALIDATION.md` § 2.1);
- `sdpram_one_clk.v` gets `DEPTH`, the number of words (default 2^`ADDRESS_WIDTH`, as before).

The contract is § 15's with the counter limit at 42 instead of 63. OpenRAM 1.2.48 builds the 336 × 8
layout but cannot characterize it (its timing stimulus probes the address of all ones); the layout-only
flow (`run_openram.sh LAYOUT_ONLY=1`) gives the full flow's sizes at 256 × 8 and 512 × 8, and
**8 116.5 µm²** for 336 × 8 (85.010 × 95.478 µm, [`openram-rx-best`](../../results/area/openram-rx-best/summary.md)).

### 16.2 The comparison

Differences against corrected `master`, and, in brackets, against `ble-rx-min`.

| | `master` | `ble-rx-adv` | `ble-rx-min` | `ble-rx-best` |
|---|---|---|---|---|
| **Content** | upstream BTLE, corrected | § 14: AA automaton, one decoder, one RAM of 8 × 64 words (1RW1R) | § 15: the same + one multiplier + the RAM on one single-port macro | the same + **42 words per phase, packed** |
| Configuration measured | defaults | `RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM` = 1 | the defaults | **the defaults** |
| **Receives data-channel packets** | yes | no | no | no |
| **RX packet RAM** | 8 × (512 × 8), 1RW1R | 1 × (512 × 8), 1RW1R | 1 × (512 × 8), 1RW | **1 × (336 × 8), 1RW** |
| RX packet RAM macros, OpenRAM (µm²) | 189 663.8 | 23 708.0 | 10 703.9 | **8 116.5** [−2 587.4, −24.2 %] |
| Std cells, `btle_rx` | 36 782 | 8 110 | 7 108 | 7 281 [+173] |
| Flip-flops, `btle_rx` | 2 068 | 1 188 | 1 323 | 1 371 [+48] |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 13 020.7 | 12 407.3 | 12 780.0 [+372.7, +3.0 %] |
| **Receiver: `btle_rx` cells + its RAM macros (µm²)** | 238 283.0 | 36 728.7 (−84.6 %) | 23 111.2 (−90.3 %) | **20 896.5 (−91.2 %)** [**−9.6 %**] |
| Std cells, `btle_controller` | 52 357 | 24 075 (−54.0 %) | 22 926 (−56.2 %) | 22 983 (−56.1 %) |
| Cell area, `btle_controller` (µm²) | 74 684.8 | 39 237.4 | 38 488.6 | 38 700.1 |
| SRAM macros / bits, controller | 15 / 1 136 070 | 8 / 1 107 398 | 8 / 1 107 398 | 8 / 1 105 990 |
| Min period of the controller / worst path | 3.410 ns, the transmitter's Gaussian tail | 3.346 ns, the same | 3.490 ns, the same | 3.334 ns, the same |
| Min period of `btle_rx` alone / worst path | 1.991 ns, a demodulator multiply | 1.844 ns, the shared demodulator's multiply | 2.045 ns, the history read into the one multiplier | 1.997 ns, the same |
| **Data + clock switched capacitance, `mixed`** | 1.30 × 10⁹ fF | +0.6 % | +8.3 % | +9.6 % [+1.2 %] |
| … over the 5 scenarios (`rx`, `tx`, `mixed`, `idle`, `idle0`) | — | −2.5, +5.0, +0.6, +4.0, +5.3 % | +8.7, +10.2, +8.3, +9.2, +11.1 % | +10.0, +11.7, +9.6, +10.4, +12.3 % |
| Clock pins (load × toggles), `mixed` | 9.03 × 10⁸ fF | −18.5 % | −15.7 % | −14.7 % |
| Data load × toggles, `mixed` | 3.99 × 10⁸ fF | +44.0 % | +62.6 % | +64.6 % |
| Non-clock toggles / cycle, `mixed` | 1 041.3 | 1 216.2 | 1 322.8 | 1 360.1 |
| RAM-port toggles, `mixed` | 3 165 890 | 3 131 320 | 2 922 598 | 2 924 817 |
| RX packet RAM: SPICE-characterized energy | not characterized | not characterized | 31.1 µW at 16 MHz, 62.3 µW at 100 MHz (§ 15.4) | **not characterized** (OpenRAM cannot, § 16.1) |
| Functions removed | — | every Access Address but `0x8E89BED6`; packets of more than 63 octets | the same | the same, and **packets of more than 42 octets** (none in Legacy Advertising) |
| Gate-level outputs vs corrected `master`, 5 scenarios | — | identical but the raw packet-RAM read port outside the packet | the same | the same |
| Validation (§ 16.5) | the reference | § 14 | § 15 | formal (unbounded), lockstep 60/60 in 5 campaigns, the matrix (220 + the 50 data-channel cases; 270/270 with full function), lint 32/32 |

### 16.3 Area

[`results/area/rx-best/`](../../results/area/rx-best/): every top of `ble-rx-best` with its defaults;
`master`, `ble-rx-adv` and `ble-rx-min` from [`rx-min`](../../results/area/rx-min/).

| Top | `master` | `ble-rx-min` | `ble-rx-best` |
|---|---:|---:|---:|
| `rx_pdu_ram_1rw` (alone, `PHASE_WORDS` = 0) | — | 870 (180 FFs), 1 674.5 µm² | 999 (228 FFs), 2 008.3 µm² |
| **`btle_rx`** | 36 782 | 7 108 | **7 281** (1 371 FFs) |
| `btle_tx` | 5 823 | 5 979 | 5 979 |
| `btle_phy` | 42 844 | 13 180 | 13 380 |
| **`btle_controller`** | **52 357** | **22 926** | **22 983** |

- **The macro: −2 587.4 µm²** (10 703.9 → 8 116.5): a third fewer words, but not a third less area;
  the periphery of an OpenRAM macro (decoders, sense amplifiers, the column of 8 bits) does not shrink
  with the words, and the 336-word macro takes 15.7 % more area per bit than the 512 (3.02 against
  2.61 µm² per bit).
- **The logic: +372.7 µm²** of `btle_rx`: the 8 held words (48 flip-flops, 6 bits each), the
  `phase × 42 + word` address and the range check. `rx_pdu_ram_1rw` synthesised alone has its default
  `PHASE_WORDS` = 0 (512 words, the held word only).
- **The receiver, cells and macros, falls to 20 896.5 µm²: −9.6 % against `ble-rx-min`, −91.2 % against
  `master`.**
- `btle_tx` is the same as `ble-rx-min`'s (5 979 cells), and the controller moves by +57 cells.

### 16.4 Timing and activity

Timing ([`results/timing/rx-best/`](../../results/timing/rx-best/), `STA_SET=full`): the controller's
worst path stays the transmitter's Gaussian tail (3.334 ns), `btle_rx`'s the history read into the one
multiplier (1.997 ns); the flow's noise of § 15.4. The macro and its address, now a multiply and an
add, are not timed (no timing model, and none can be made for this macro); at 16 MHz the address has
62.5 ns, and the port is clocked by the AXI clock, which the lockstep exercises at 103 MHz.

Activity ([`results/power/rx-best/`](../../results/power/rx-best/)): the harness of § 5 with
`PDU_CONTRACT=1`, against corrected `master`: every compared output on every clock and every register
read identical in the 5 scenarios, the 17 packets of `rx` and 9 of `mixed` read through register 40
among them. The proxy rises by 1.2 % against `ble-rx-min` (+9.6 % against `master` in `mixed`): the 48
flip-flops of the held words switch with every octet. **The RAM's energy is not known**: OpenRAM cannot
characterize the 336 × 8 macro (§ 16.1), and the 31.1 / 62.3 µW of § 15.4 are those of the 512 × 8.

| `mixed` | RX packet RAM (µm²) | `btle_rx` cells | toggles / cycle, non-clock | data | clock | **data + clock** |
|---|---:|---:|---:|---:|---:|---:|
| `master` | 189 663.8 | 36 782 | 1 041.3 | 3.99 × 10⁸ fF | 9.03 × 10⁸ fF | 1.30 × 10⁹ fF |
| `ble-rx-min` | 10 703.9 | 7 108 | 1 322.8 | +62.6 % | −15.7 % | +8.3 % |
| `ble-rx-best` | **8 116.5** | 7 281 | 1 360.1 | +64.6 % | −14.7 % | **+9.6 %** |

### 16.5 Evidence

| | `ble-rx-best` |
|---|---|
| The packed packet RAM ([`best-formal`](../../results/validation/best-formal/formal_adv/result.txt)) | `formal_adv` task `best1rw`: `rx_pdu_ram_1rw` with 42 packed words per phase ≡ 8 `serial_in_ram_out` of 512 words under the contract of § 15 with the limit at 42, **unbounded**; `min1rw` (the unpacked memory with the held word) and § 14's tasks again, all PASS; **24/24 mutants** |
| Lockstep of `btle_rx` ([`best`](../../results/validation/best/)), as § 15.5, the reads compared while the counter is 42 or below | `adv`, `clkb` = `clk`, against `ble-rx-shared` and against corrected `master`: **60/60** each, 1 241 598 reads compared each, 17/17 mutants; `clkb` at 103 MHz: **60/60**, 7 975 453 reads compared, 15/15 mutants; `line`: **60/60** (`clkb` = `clk`, 1 893 257 reads, 16/16 mutants), **60/60** (103 MHz, 12 217 655 reads, 14/14 mutants) |
| The product audit's matrix ([`best-matrix-*`](../../results/validation/)) | 220 PASS, **50 ERROR: the 50 data-channel cases**, case by case those of § 13; **270/270** with full function (the packing off: 512 words per phase); **270/270** with every parameter at 0 |
| Lint gate (Verilator 5.020, `--Wall`) | **32/32 configurations** (with `RX_PDU_PACKED`), 12 reviewed exceptions, none new |
| Gate-level lockstep, run `rx-best` | 5/5 scenarios, `PDU_CONTRACT=1` |
| Report | `docs/Validation/RX_BEST_VALIDATION.md` (on `ble-rx-best`) |

### 16.6 Conclusions for `ble-rx-best`

- **The receiver of Legacy Advertising is 20 896.5 µm², cells and macros: −91.2 % against `master`**,
  −9.6 % against `ble-rx-min`, giving up only decodes of more than 42 octets, which no Legacy
  Advertising packet has.
- **The lever is smaller than the words suggest**: 34 % fewer words give 24 % less macro, and 14 % of
  that goes back in logic (the held words, the address). It also leaves the macro without a timing or
  power model.
- **The proof paid for itself**: packing turned a harmless misdirected write of `ble-rx-min` (a hit during
  a waiting write, into a word no read sees) into a corruption of the next phase; the held word fixes
  both.
- **With full function** (any Access Address, 512 words per phase) the branch receives every packet of
  the matrix (270/270): `RX_PDU_PACKED` packs only with `RX_PDU_ADV_DEPTH`.

### 16.7 Reproducing

From WSL, at the root of `ble-rx-best` (the vectors as in § 15.7):

```bash
LAYOUT_ONLY=1 scripts/area/run_openram.sh openram-<label> sram_1rw_8x336 sram_1rw_8x256 sram_1rw_8x512
RTL_REV=3d92ea80 scripts/area/run_area.sh <label>/ble-rx-best
DUT_REV=3d92ea80 DUT_PARAMS= scripts/timing/run_sta.sh <label>/ble-rx-best 62.5 fca6ac6
DUT_REV=3d92ea80 DUT_PARAMS= PDU_CONTRACT=1 VEC_DIR=/tmp/vec scripts/power/run_activity.sh <label>/ble-rx-best 100000 1 fca6ac6
```
(the validation commands: `RX_BEST_VALIDATION.md` § 4; `master`, `ble-rx-adv` and `ble-rx-min` as in § 15.7.)

## 17. `ble-rx-micro`: one stored phase and an 8-bit demodulator (run `micro`)

Run `micro`, on `ble-rx-micro`: the RTL of `745e4bba`, the area flow of run `rx-best`, and the
packet-error-rate harness of `ble-rx-best` (`scripts/validation/rx_per/`, `docs/Validation/RX_PER.md` on
`ble-rx-best` and `ble-rx-micro`). Unlike every branch above, **`ble-rx-micro` is not equivalent to the one
it was cut from**: it decodes less, by design, and its cost is measured in packets, not proved away. It
does not receive data-channel packets (§ 7). No timing and no switching activity were measured.

### 17.1 What changes

Two levers that the models of `RX_PER.md` § 3 rank as the cheapest in sensitivity per µm²:

- **One stored phase** (`rx_one_phase.v`, `RX_ONE_PHASE = 1`): the phase is chosen when the Access Address
  is found, the middle of the phases that find it within one symbol of the first (the model `centre1`),
  instead of keeping 8 decoders and 8 packets and choosing by the CRC at the end. One
  `rx_decoder_shared` with `NUM_PHASE = 1`, fed the chosen phase one bit late, so the choice needs no
  buffer; the packet's 42 octets in registers, read on `clkb`. **The 336 × 8 macro goes.**
- **An 8-bit demodulator** (`RX_IQ_BITS = 8`, `RX_IQ_SHIFT = 0`): the samples saturated to 8 bits before
  `gfsk_demodulation_shared`, at the scale of the matrix (a peak of 127); a 12-bit front end would take
  `RX_IQ_SHIFT = 4`.

`RX_ONE_PHASE = 0` keeps the 8 decoders of `ble-rx-best` unchanged.

### 17.2 The comparison

Differences against corrected `master`, and, in brackets, against `ble-rx-best`.

| | `master` | `ble-rx-best` | `ble-rx-micro` |
|---|---|---|---|
| **Content** | upstream BTLE, corrected | § 16 | § 16 + **one stored phase** + **an 8-bit demodulator** |
| Phases decoded / packets stored | 8 / 8 | 8 / 8 | **1 / 1** |
| Demodulator multipliers / width | 16 / 16 bits | 1 / 16 bits | **1 / 8 bits** |
| **RX packet RAM** | 8 × (512 × 8), 1RW1R | 1 × (336 × 8), 1RW | **none**: 42 octets in registers |
| RX packet RAM macros, OpenRAM (µm²) | 189 663.8 | 8 116.5 | **0** |
| Std cells, `btle_rx` | 36 782 | 7 281 | **3 668** [−3 613] |
| Flip-flops, `btle_rx` | 2 068 | 1 371 | 787 [−584] |
| Cell area, `btle_rx` (µm²) | 48 619.2 | 12 780.0 | **6 993.7** [−5 786.3, −45.3 %] |
| **Receiver: `btle_rx` cells + its RAM macros (µm²)** | 238 283.0 | 20 896.5 (−91.2 %) | **6 993.7 (−97.1 %)** [**−66.5 %**] |
| Std cells, `btle_controller` | 52 357 | 22 983 | 19 671 (−62.4 %) |
| Cell area, `btle_controller` (µm²) | 74 684.8 | 38 700.1 | 33 226.1 |
| SRAM macros, controller | 15 | 8 | 7 |
| Timing, activity | § 4, § 5 | § 16.4 | **not measured** |
| Functions removed | — | every Access Address but `0x8E89BED6`; packets of more than 42 octets | the same, and **about 2 dB of sensitivity** (§ 17.4) |
| Validation (§ 17.5) | the reference | § 16.5 | `rx_per`: RTL ≡ its model packet by packet, 3 configurations; lint 64/64; the matrix |

### 17.3 Area

[`results/area/micro/ble-rx-micro/`](../../results/area/micro/ble-rx-micro/summary.md) (on `ble-rx-micro`):
`btle_rx` 3 668 cells, 787 flip-flops, 6 993.7 µm², and no macro: the 42 octets of the packet are 336
flip-flops in it. Of the 12 780.0 + 8 116.5 µm² of `ble-rx-best`, the macro and its single-port logic
(`rx_pdu_ram_1rw`) go, the decoder keeps one phase of eight, and the demodulator's multiplier and its
history halve in width. `btle_tx` is the same RTL (8 742.1 µm² against 8 698.5 in run `rx-best`: the
flow's noise of §§ 3.1, 12.3, 15.3).

### 17.4 The cost

Packets lost, %, on the same samples (`rx_per`, seed 1, 400 packets per point; RTL):

| ppm | SNR (dB) | `ble-rx-best` | 8 bits, 8 phases (`RX_ONE_PHASE = 0`) | `ble-rx-micro` |
|---:|---:|---:|---:|---:|
| 0 | 10 | 3.0 | 3.8 | 27.8 |
| 0 | 12 | 0.0 | 0.0 | 2.8 |
| 10 | 12 | 0.2 | 0.5 | 10.2 |
| 20 | 12 | 11.8 | 14.0 | 45.2 |
| 20 | 14 | 0.0 | 0.0 | 7.8 |
| 30 | 16 | 1.8 | 2.2 | 11.2 |
| 30 | 20 | 0.0 | 0.0 | 0.0 |

The 8 bits cost little at this scale (2 640 packets lost of 9 600, against 2 604); the one stored phase
costs about 2 dB. With a strong signal (14 dB and more up to 10 ppm, 16 dB up to 20 ppm) neither loses a
packet, or almost none.

### 17.5 Evidence

| | `ble-rx-micro` |
|---|---|
| Both levers against the model `centre1` at 8 bits | **9 600/9 600 packets the same**, 0 wrong PDUs, mutants 4/4 |
| The width alone (`RX_ONE_PHASE = 0`) against `best8` at 8 bits | **9 600/9 600** |
| `RX_ONE_PHASE = 0` at 16 bits against `best8` | **9 600/9 600**, the losses of `ble-rx-best`; mutants 3/3 |
| Lint gate (Verilator 5.020, `--Wall`) | **64/64 configurations** (with `RX_ONE_PHASE`), 12 reviewed exceptions, none new |
| The product audit's matrix | 214 PASS, 56 ERROR: the 50 data-channel cases, and 3 advertising packets at the threshold that one stored phase loses (§ 17.4) |
| Not done | formal proof, lockstep, gate-level simulation, timing, activity |
| Report | `docs/Validation/RX_MICRO_VALIDATION.md` (on `ble-rx-micro`) |

### 17.6 Conclusions for `ble-rx-micro`

- **The receiver of Legacy Advertising is 6 993.7 µm², with no SRAM macro: −97.1 % against `master`,
  −66.5 % against `ble-rx-best`.** The largest single step since B1, and the first one paid in function.
- **The price is about 2 dB**, measured packet by packet and reproduced by the RTL exactly: the choice of
  the phase at the Access Address loses the packets that only another phase would have decoded. The 8-bit
  demodulator costs almost nothing at the scale of the matrix; at another front end's scale it needs
  `RX_IQ_SHIFT`.
- **Whether to take it is a requirement, not a measurement**: for devices heard with a strong signal it
  loses nothing; for the weakest it is `ble-rx-best`.

### 17.7 Reproducing

From WSL, at the root of `ble-rx-micro`:

```bash
QBITS=8 QSHIFT=0 scripts/validation/rx_per/run_rx_per.sh micro 400 centre1
QBITS=8 QSHIFT=0 DUT_PARAMS='RX_ONE_PHASE=0' scripts/validation/rx_per/run_rx_per.sh micro 400 best8
DUT_PARAMS='RX_ONE_PHASE=0 RX_IQ_BITS=16' scripts/validation/rx_per/run_rx_per.sh micro 400 best8
scripts/area/run_area.sh micro/ble-rx-micro
```
