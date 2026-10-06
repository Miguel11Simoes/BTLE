> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](../Validation/PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](../Validation/ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# Gaussian filter: where the table lives, and the folded FIR — TX area of every option

> Validation correction (2026-10-04): earlier success claims for all 270 checks are withdrawn. The strict rerun is **FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See [the integrity audit](../Validation/VALIDATION_INTEGRITY.md) for evidence and limitations.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** the same file on `master`, `risc-v-ble`, `ble-opt`, `ble-tx-table`, `ble-rx-dm`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw`, `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom` and `ble-tx-cordic`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-28; updated 2026-09-29 (on `ble-tx-sin4`, `ble-tx-sin8` and `ble-tx-opt`; pointer to the TX total), 2026-10-03 (the two VCO-memory branches), 2026-10-04 (the filter's weight with the memory of `ble-tx-sin2`; `ble-tx-1--8`; the constant taps paired, built on `ble-tx-pdu`) and 2026-10-05 (`ble-tx-pdu-we`, `ble-tx-rom` and `ble-tx-cordic`, the same filter; what the firmware writes, corrected)  
**Author:** Miguel Simões  
**Status:** executed: run `tx-area` of `scripts/compare/run_tx_compare.sh` (harness `4946579`).
**TX area only**: the receiver is not counted. Pre-layout std-cell area (Nangate45) plus real
SRAM macros (OpenRAM, FreePDK45).

---

## Purpose

Branch `ble-tx-table` replaced the Gaussian FIR of the transmitter by
distributed-arithmetic tables of precomputed tap sums (160 entries of 16 bits,
2 560 bits). The question raised about it is **where those values should be
kept — OTP, ROM, SRAM or registers (REG) — given that it is not known yet
whether they will have to change after the chip is made**, and whether an
alternative with no table, a FIR that exploits the symmetry of the Gaussian
taps, would be better. The goal is the cheapest option, with the smallest
area, and the answer has to rest on real implementations, not on estimates.

Every option that can be built with open tools was implemented, validated
against the upstream FIR, and measured with the same flow, in one run.

## 1. The options

| Option | Branch | Where the values are | Change after fabrication? | Built as |
|---|---|---|---|---|
| Upstream FIR (reference) | `master` | 9 tap registers (144 bits); the filter adds 17 terms | **yes**, any time, through register 1 | upstream |
| **Folded FIR** | `ble-tx-fir2` | the same 9 tap registers; 8 pair terms + the centre | **yes**, same interface | new RTL, exact rewrite |
| **ROM**: tables as constants | `ble-tx-table` | 160 constants that synthesis folds into gates | **no**: a new chip | B2 of `ble-opt` |
| **Constant taps, paired** | `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, `ble-tx-cordic` | the 9 taps as constants; 8 pair terms + the centre | **no**: a new chip | B2 rewritten, exact |
| **REG**: tables in flip-flops | `ble-tx-table-reg` | 2 560 flip-flops | **yes**: rebuilt from the taps | new RTL |
| **SRAM**: tables in SRAM | `ble-tx-table-sram` | 3 single-port SRAM macros, 2 560 bits | **yes**: rebuilt from the taps | new RTL + OpenRAM macros |
| MASK-ROM macro | — | a ROM macro instead of gates | no | **not buildable**: OpenRAM's ROM compiler stops with an internal assertion in FreePDK45 for every size tried |
| **OTP** | — | a one-time-programmable macro | once | **not buildable**: neither FreePDK45 nor OpenRAM provides an OTP macro |

**Folded FIR.** Positions k and 16−k of the 17-sample window use the same tap,
and position 8 is the centre. Each pair of terms (bₖ ? h : −h) + (b₁₆₋ₖ ? h : −h)
is one term: +2h if both bits are 1, −2h if both are 0, and 0 otherwise. The
filter therefore adds 8 pair terms and the centre instead of 17 terms. The
result is identical modulo 2¹⁶ for every tap value and every input, so this is
an exact rewrite, like B1, and it replaces the FIR unconditionally. A side
effect: 2h modulo 2¹⁶ does not depend on bit 15 of h, so synthesis drops the
top bit of the 8 paired taps (178 → 170 flip-flops), correctly.

**Constant taps, paired.** On `ble-tx-pdu` the constant-tap filter of B2 is
computed without tables: (bₖ ? h : −h) = 2·(bₖ ? h : 0) − h, so the sum is
2·Σ(bₖ ? hₖ : 0) − Σhₖ modulo 2¹⁶, and the two positions of each tap are added
first, which takes the tap 0, 1 or 2 times. It is the folding of the folded
FIR applied to the constant taps; the result is the same for every tap set and
every input, and the taps stay a synthesis parameter as on `ble-tx-table`.

**REG and SRAM tables.** To keep the software interface of the FIR (9 taps
written through register 1; `firmware/btle_ll.c` writes no tap itself, but
forwards any register write a host sends it), the
tables are rebuilt in hardware by `gauss_table_builder` from the tap
registers whenever a tap write changes one: one term per clock, 928 clocks
(58 µs at 16 MHz), before the next transmission. Its cost is listed apart
(§ 3), so the memory alone can also be read. If software computed and wrote
the 160 entries itself, the builder and the tap registers would go, and the
table would still cost what § 3 shows.

The SRAM banks are A 32 × 32 bits (both entries of a group-A index), B 64 × 16
and C 32 × 16, each used through one read/write port, as a single-port macro.
They have a registered read, so they are addressed one clock ahead, with the
next state of the shift register, and the output timing is the FIR's. Their
area comes from real macros generated with OpenRAM 1.2.48 in FreePDK45, the
process behind the Nangate45 cells of the flow (`scripts/area/run_openram.sh`).

## 2. Result: TX area (measured)

`scripts/compare/run_tx_compare.sh tx-area`: Yosys 0.68 + ABC, Nangate45; the
area of the SRAM macros is added to the std-cell area. The RAMs every option
shares (TX COS/SIN tables, 32 768 bits, and the TX packet buffer, 4 096 bits)
are left out. Results in
[`results/compare/tx-area/summary.md`](../../results/compare/tx-area/summary.md)
(on the four TX branches). With those RAMs counted as SRAM macros, the
transmitter is about 97 % memory and every option here moves its total by
−1.8 to +11.9 %: `docs/Validation/BRANCH_COMPARISON.md` § 4. With
`ble-tx-sin2` (40 293 µm², the one-port sine table; `ble-tx-1--8` is within
0.2 % of it), the filter weighs more: B2 is estimated to take 7.4 % off it and
the folded FIR 2.5 % (the same § 4.2). `ble-tx-pdu` builds B2, in its paired
form, with that memory and a one-port packet buffer: 20 098.5 µm² in all, of
which the filter is 1.3 %.

### 2.1 The Gaussian filter (`gauss_filter`)

| Option | Branch | Std cells | Flip-flops | Cell area (µm²) | Table macros (µm²) | **Total (µm²)** | vs upstream FIR |
|---|---|---:|---:|---:|---:|---:|---:|
| **Constant taps, paired** | `ble-tx-pdu` | 166 | 22 | 256.7 | — | **256.7** | **−92.4 %** |
| **ROM**: tables as constants | `ble-tx-table` | 253 | 22 | 348.5 | — | **348.5** | **−89.6 %** |
| **Folded FIR** | `ble-tx-fir2` | 1 560 | 170 | 2 311.5 | — | **2 311.5** | **−31.3 %** |
| Upstream FIR | `master` | 2 286 | 178 | 3 366.0 | — | **3 366.0** | — |
| **SRAM** tables | `ble-tx-table-sram` | 1 362 | 267 | 2 479.7 | 18 437.4 | **20 917.1** | **+521 % (×6.2)** |
| **REG** tables | `ble-tx-table-reg` | 10 097 | 2 822 | 23 221.5 | — | **23 221.5** | **+590 % (×6.9)** |

`ble-tx-pdu` is run `tx-pdu` of `scripts/compare/run_compare.sh` (the same flow,
`GAUSS_TABLE=1`). `ble-tx-pdu-we` has the same `gauss_filter.v` (run `tx-pdu-we`:
166 cells, 22 flip-flops, 256.7 µm², as on `ble-tx-pdu`); so do `ble-tx-rom` and
`ble-tx-cordic`, which change only `vco.v`.

### 2.2 The whole transmitter (`btle_tx`)

| Option | Branch | Std cells | Cell area (µm²) | Table macros (µm²) | **Total (µm²)** | vs upstream |
|---|---|---:|---:|---:|---:|---:|
| ROM | `ble-tx-table` | 1 392 | 2 325.6 | — | **2 325.6** | **−56.3 %** |
| Folded FIR | `ble-tx-fir2` | 2 707 | 4 295.9 | — | **4 295.9** | **−19.3 %** |
| Upstream FIR | `master` | 3 409 | 5 322.9 | — | **5 322.9** | — |
| SRAM | `ble-tx-table-sram` | 2 477 | 4 434.5 | 18 437.4 | **22 871.9** | +329.7 % |
| REG | `ble-tx-table-reg` | 11 328 | 25 201.6 | — | **25 201.6** | +373.5 % |

Every number is the same as in the per-branch area runs
(`results/area/tx-table-reg`, `tx-table-sram`, `tx-fir2`, `tx-table`,
`baseline-upstream`), cell for cell. `ble-tx-pdu` is not in this table: its
`btle_tx` also changes the packet buffer and the counters
(`docs/Validation/TX_PDU_VALIDATION.md`).

## 3. Inside the rewritable tables

| Part | REG (`ble-tx-table-reg`) | SRAM (`ble-tx-table-sram`) |
|---|---:|---:|
| Table storage | `gauss_table_reg`: 8 899 cells, 2 560 flip-flops, **20 870.1 µm²** (8.15 µm² per bit, with the write enables and the three read multiplexers) | 3 OpenRAM macros: **18 437.4 µm²** (7.20 µm² per bit) + 139.4 µm² of port logic |
| Builder (`gauss_table_builder`) | 493 cells, 53 flip-flops, 778.0 µm² | the same, 778.0 µm² |
| Tap registers, change detection, three-term sum, output | 1 573.4 µm² | 1 562.3 µm² |
| **Total** | **23 221.5 µm²** | **20 917.1 µm²** |

| OpenRAM macro (FreePDK45, 1RW) | Words × bits | Bits | Size (µm) | Area (µm²) | µm² per bit |
|---|---|---:|---|---:|---:|
| `sram_1rw_32x32` (bank A) | 32 × 32 | 1 024 | 118.685 × 76.220 | 9 046.2 | 8.83 |
| `sram_1rw_16x64` (bank B) | 64 × 16 | 1 024 | 73.035 × 74.975 | 5 475.8 | 5.35 |
| `sram_1rw_16x32` (bank C) | 32 × 16 | 512 | 73.035 × 53.610 | 3 915.4 | 7.65 |

At 2 560 bits in three banks, the SRAM periphery (decoders, sense amplifiers,
write drivers, control, supply rings) dominates: per bit it costs almost as
much as a flip-flop with its multiplexers, and the SRAM table ends only 10 %
below the REG table. The storage alone, without the builder and the tap
registers, is 8 to 9 times the whole folded FIR.

## 4. What the numbers say

1. **Taps fixed at fabrication → ROM (the tables as constants): 348.5 µm².**
   It is by far the smallest option: 9.7 times smaller than the upstream FIR,
   and it cuts the whole transmitter by 56 %. The constants let synthesis fold
   the 160 entries into about 230 gates. The price is that changing the filter
   needs a new chip. The same constant taps without tables, paired as in the
   folded FIR, take 256.7 µm² on `ble-tx-pdu`: 26 % less again.
2. **Taps programmable after fabrication → the folded FIR: 2 311.5 µm².** It is
   the smallest option that can still change: 31 % below the upstream FIR, with
   the same software interface, new taps active on the next clock, no memory
   macro and no rebuild delay.
3. **Rewritable tables (REG, SRAM) are the worst options: 6 to 7 times the
   upstream FIR.** A table is small only because it is constant. To rewrite
   it, the 160 precomputed entries (2 560 bits) must be stored instead of the
   9 taps (144 bits) the FIR computes from, which is 18 times more state.
4. **SRAM against REG**: SRAM is 10 % smaller at this size, which does not
   change the conclusion.
5. **OTP** (§ 5) cannot beat the ROM for a table fixed at fabrication, and it
   cannot be rewritten. Its only sensible use is a **one-time choice per chip**:
   9 taps (144 bits) in OTP feeding the folded FIR, whose tap registers are
   the shadow copy the OTP is read into at boot.

**The price of keeping the filter programmable** is therefore the difference
between the two winners: 2 311.5 − 348.5 = **1 963 µm²** for the filter
(1 970 µm² for the whole transmitter). For scale, that is 7.4 % of the whole
`ble-opt` controller (26 681 µm²).

| If the taps… | Choose | Filter area | Branch |
|---|---|---:|---|
| never change after fabrication | the taps as constants, paired (or as tables) | 256.7 µm² (348.5) | `ble-tx-pdu` (`ble-tx-table`) |
| must change by software | folded FIR | 2 311.5 µm² | `ble-tx-fir2` |
| are chosen once per chip | folded FIR + 144-bit OTP for the taps | 2 311.5 µm² + the OTP macro (not measurable here) | — |
| (anything) | not REG, not SRAM tables | ≥ 20 917 µm² | — |

Since it is not decided yet whether the taps must change, the two candidates
are the ROM and the folded FIR. They are the same kind of change (the filter
block only), so the choice can wait until tape-out. `ble-tx-table` already
selects the ROM with a synthesis parameter (`GAUSS_TABLE`), and the folded FIR
could become the default of that same parameter.

## 5. MASK-ROM and OTP: why there are no branches

- **MASK-ROM macro.** OpenRAM 1.2.48 has a ROM compiler, but in FreePDK45 it
  stops with the same internal assertion (in `pinv`: "Must have a size greater
  than or equal to 1") for every size tried: the full table (160 × 16), bank A
  (32 × 32), bank B (64 × 16) and bank C (32 × 16). Another node, such as
  sky130, would give areas that cannot be compared with the Nangate45 cells.
  It would not change the ranking anyway. A ROM macro still has decoders,
  word-line drivers and sense amplifiers, and the smallest macro measured
  here, 512 bits of SRAM, is already 3 915 µm². The whole filter with the ROM
  in gates is 348.5 µm².
- **OTP.** Neither FreePDK45 nor OpenRAM provides an OTP macro, so there is
  no real number to measure in the node of this flow. An OTP macro needs,
  besides the array, sense amplifiers, decoders and a high-voltage programming
  circuit, and a programming step in production.
  For the table that means more than the ROM in gates, with no way to rewrite.
  For the 9 taps (144 bits) it is a small macro next to the folded FIR,
  measurable only with a foundry's OTP IP.

A branch for either would contain the read logic already measured, plus a
macro whose area cannot be obtained, so none was created.

## 6. Cost beyond area

| Option | Filter area | Extra IP or process | Production | Changing the filter |
|---|---:|---|---|---|
| Constant taps, paired | 256.7 µm² | none | none | new masks |
| ROM in gates | 348.5 µm² | none | none | new masks |
| Folded FIR | 2 311.5 µm² | none | none | software, next clock |
| Upstream FIR | 3 366.0 µm² | none | none | software, next clock |
| SRAM tables | 20 917.1 µm² | SRAM compiler and macros, memory BIST | memory test | software, then 928 clocks |
| REG tables | 23 221.5 µm² | none | none | software, then 928 clocks |
| OTP | not measurable | OTP IP (licence), high-voltage programming circuit | one programming step per chip | once |

## 7. Evidence that each option works

Each new branch was checked against the upstream FIR before its area was
trusted, because a wrong design can be small.

| | `ble-tx-fir2` (folded FIR) | `ble-tx-table-reg` | `ble-tx-table-sram` |
|---|---|---|---|
| Formal | pair identity at 16 bits (all taps); whole filter equivalent to upstream for **any taps and any input**, unbounded, at 4 bits (74 s, z3); 3/3 mutants rejected (the 4-bit proof does not pass them, and the random lockstep finds each) | defaults ≡ upstream: `gauss_filter`, `gfsk_modulation`, `btle_tx` | the same |
| Random lockstep, module level, 16 bits | 4 seeds × 2 000 000 clocks: 7 999 607 clocks compared, 1 001 125 random tap writes, 5 332 990 samples, 393 resets, no mismatch | 4 seeds × 200 random tap sets × 5 000 clocks, back-to-back samples included; 2/2 mutants | the same; 4/4 mutants, including the one-clock-ahead SRAM addressing |
| Controller through the registers | — | 15/15 runs, 90 random tap sets reprogrammed in flight, 930 629 clocks, every output and register; 4/4 mutants | 15/15 runs, 927 488 clocks; 6/6 mutants |
| Upstream testbenches, 270 runs | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) |

The ROM option is validated in `docs/Validation/TX_TABLE_VALIDATION.md` on
`ble-tx-table` (unbounded formal proof against the FIR with the BLE taps), and
its paired form in `docs/Validation/TX_PDU_VALIDATION.md` on `ble-tx-pdu`
(the same proof, with mutants of the new form, 3/3).

At 16 bits, the solvers do not close the whole folded-FIR equivalence: they
would have to match two different 16-bit adder trees over 9 symbolic taps. At
16 bits bitwuzla had not closed the induction after 13 minutes and z3 after
40 (both stopped), and z3 had not closed 8 bits after 40 minutes either; at 4
bits z3 closes it in about a minute. The proof is therefore split: the pair
identity is proved at 16 bits, the whole filter (pairing, index mapping, sum,
registers) at 4 bits, and the 16-bit design is exercised by the random
lockstep and the 270 testbench runs. The identity implemented holds over the
integers, hence modulo 2ᵂ for every width W. Unlike the shared demodulator on
`ble-opt`, whose arithmetic could be abstracted to reach an unbounded proof at
the real width, there is no full-width proof of the whole folded filter: the
two designs compute their sums differently, so there is no common arithmetic
to abstract.

## 8. What this does not claim

- **Area only**, as asked: no timing, no power, no layout of the logic.
- **The SRAM macros are OpenRAM layouts in FreePDK45**, an academic PDK;
  a commercial compiler would be denser. It would not change the ranking:
  even at a third of the measured area, the SRAM table would be about
  8 600 µm², 3.7 times the folded FIR.
- **The REG table is mapped without clock gating** (Nangate45 has no
  enable flip-flop, so each bit has a multiplexer). Its 2 560 flip-flops alone
  are already 11 576 µm², five times the folded FIR.
- **MASK-ROM and OTP macros are not measured** (§ 5).
- **The REG and SRAM tables need 928 clocks after a tap write** before the
  filter is valid again; the FIRs apply new taps on the next clock.

## 9. Reproducing

From WSL, at the root of a TX branch (`ble-tx-table`, `ble-tx-table-reg`,
`ble-tx-table-sram` or `ble-tx-fir2`):

```bash
scripts/compare/run_tx_compare.sh <label>        # the five options, about 15 s
scripts/area/run_openram.sh <label>              # the SRAM macros (on ble-tx-table-sram), about 6 min
```

Validation, on each branch: `scripts/validation/formal_fir2/run_formal_fir2.sh`
(`ble-tx-fir2`), `scripts/validation/table_random/run_table_random.sh`,
`scripts/validation/ctl_lockstep/run_ctl_lockstep.sh` and
`scripts/validation/equiv_defaults/run_equiv_defaults.sh <label> upstream-baseline gauss_filter gfsk_modulation btle_tx`
(`ble-tx-table-reg`, `ble-tx-table-sram`), and
`scripts/validation/run_rx_regression.sh` (with
`DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1"` on the table branches).
