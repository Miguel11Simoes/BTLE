> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# Comparison of the transmitter branches: upstream, the transmitter variants and `ble-opt`

> Validation correction (2026-10-04): earlier success claims for all 270 checks are withdrawn. The strict rerun is **FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See [the integrity audit](VALIDATION_INTEGRITY.md) for evidence and limitations.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** these branches carry this same file, with its companion [RX_BRANCH_COMPARISON.md](RX_BRANCH_COMPARISON.md) (`master`, `risc-v-ble`, `ble-tx-table`, `ble-tx-table-reg`, `ble-tx-table-sram`, `ble-tx-fir2`, `ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw`, `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom`, `ble-tx-cordic`, `ble-tx-min`, `ble-rx-dm`, `ble-rx-dmult`, `ble-opt`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-28; updated 2026-09-29 (six transmitter branches, SRAM macro areas), 2026-10-03 (the VCO-memory sweep), 2026-10-04 (`ble-tx-sin8-1rw`, `ble-tx-sin2` and `ble-tx-1--8`, the one-port VCO memories, runs `tx-1rw` and `tx-1--8`; `ble-tx-pdu`, the one-port packet buffer, run `tx-pdu`), 2026-10-05 (`ble-tx-pdu-we`, the packet buffer written only when its pair is new, run `tx-pdu-we`; the energy of the transmitter's SRAMs, § 6.6; corrections listed in `CHANGES.md`; `ble-tx-rom` and `ble-tx-cordic`, the VCO without memory, and run `tx-vco`, every transmitter on the audited RTL, § 4.4) 2026-10-07 (`ble-tx-rom` and `ble-tx-cordic` in the table of § 2; the lint closure, §§ 4.4, 7 and 10) and 2026-10-18 (`BRANCH_COMPARISON.md` split in two: the branches that change only the receiver, `ble-rx-dm` and `ble-rx-dmult`, are compared in [RX_BRANCH_COMPARISON.md](RX_BRANCH_COMPARISON.md); this file keeps the transmitter branches and `ble-opt`, whose B1 is the change of `ble-rx-dm`)  
**Author:** Miguel Simões  
**Status:** executed: run `all-branches`, harness `scripts/compare/` at `f540e99` (summary
regenerated at `696b036`, § 11); with the same harness and the same vectors, run `tx-variants`
(`fe14935`) for four transmitter branches (its two failed checks are explained in § 6.1), run
`tx-sin8` (`577bb31`) for `ble-tx-sin8`, run `tx-opt` (`a4ccea7`) for `ble-tx-opt`, run
`tx-1rw` (`69e5204`) for `ble-tx-sin8-1rw` and `ble-tx-sin2`, run `tx-1--8` (`78fdadc`) for
`ble-tx-1--8`, run `tx-pdu` (`b773316`) for `ble-tx-pdu` and run `tx-pdu-we` (`eec6c8f`) for
`ble-tx-pdu-we`; transmitter SRAM macros from runs `openram-tx`, `openram-sin8`,
`openram-1rw-sweep` and `openram-pdu` (OpenRAM 1.2.48, FreePDK45), their energies from runs
`sram-char` (`f810ae4`) and `sram-leakage` (`3d94645`), their accesses from run `sram-energy`
and the packet buffer at rest from run `sram-idle` (`d39ee32`); run `tx-vco` (`8083f77`, on
`ble-tx-rom`) for the VCO and the transmitter of every branch on the audited RTL (§ 4.4).
Pre-layout area and static timing; gate-level switching activity, which is a proxy and
**not power**; and the energy of the transmitter's SRAM accesses (§ 6.6).

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
B2 and `ble-rx-dm` only B1. `ble-rx-dm`, and the other branches that change
only the receiver, are compared in [RX_BRANCH_COMPARISON.md](RX_BRANCH_COMPARISON.md);
B1 appears here only as a part of `ble-opt`, with the measures of `ble-rx-dm`
where the sums of `ble-opt` need them (§§ 3.2, 3.3 and 6.4). Thirteen more
branches change only the transmitter. Three of
them build the Gaussian filter another way: `ble-tx-table-reg` and
`ble-tx-table-sram` keep B2's tables but rewritable (in flip-flops, in SRAM),
and `ble-tx-fir2` folds the FIR by the symmetry of its taps; their choice is
argued in `docs/Design Decisions/GAUSS_FILTER_OPTIONS.md`. Five shrink the
VCO's memory: `ble-tx-sin4` stores only the first quarter of the cosine and
sine tables and rebuilds the rest by symmetry, and `ble-tx-sin8` then keeps
those two quarter tables, which are always read at the same address, in one
memory of {cos, sin} words. `ble-tx-sin8-1rw` gives that memory one port
instead of two; `ble-tx-sin2` keeps only the quarter sine table, also with one
port, read twice per sample; and `ble-tx-1--8` keeps only the first eighth of
both tables, 256 {cos, sin} words with one port, read once per sample. Their
memories were chosen in `docs/Design Decisions/VCO_MEMORY_SWEEP.md`. One
more, `ble-tx-opt`, puts
together B2 and the memory of `ble-tx-sin8`, and nothing else: its receiver and
its debug memory are upstream's. `ble-tx-pdu` puts B2 together with the
memory of `ble-tx-sin2`, gives the packet buffer one port too, and rewrites five
blocks of the transmitter's logic exactly; `ble-tx-pdu-we` writes that buffer only
when its pair is new, for power; and the last two, `ble-tx-rom` and `ble-tx-cordic`,
give the VCO no memory: its tables are fixed, in a ROM or computed by a CORDIC.

This document measures every branch with the same ruler and answers four
questions: what each change buys on its own, whether the changes add up, what
each one costs in function, and how large the transmitter really is once its
memories are counted. The area flow counts RAM in bits only, so it cannot
weigh logic against memory; § 4 adds the area of real SRAM macros, and § 6.6
the energy of their accesses, which the activity flow does not see.

This file is identical on every branch listed above. The raw results it cites are in
`results/compare/{all-branches,tx-variants,tx-sin8,tx-opt,tx-1rw,tx-1--8,tx-pdu,tx-pdu-we}/`, in the
per-configuration folders `results/{area,timing,power}/{all-branches,tx-variants,tx-sin8,tx-opt,tx-1rw,tx-1--8,tx-pdu,tx-pdu-we}/`,
in `results/area/{openram-tx,openram-sin8,openram-1rw-sweep,openram-pdu}/`, in
`results/power/{sram-char,sram-char-trimmed,sram-char-xyce,sram-leakage,sram-energy,sram-idle}/` and in
`results/{area,timing}/tx-vco/`, which exist on `ble-opt`, `ble-tx-table`, `ble-rx-dm`, `ble-tx-opt`,
`ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom` and `ble-tx-cordic`; the relative links below resolve there.

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
| `ble-tx-sin8-1rw` | the memory of `ble-tx-sin8` with one port: 512 × 16, {cos, sin} per word | `vco.v` and the testbench fix U9; tree `132cca8` | defaults (not a parameter) |
| `ble-tx-sin2` | the quarter sine table alone, 512 × 8 with one port, read twice per sample; cos 0 in a register | `vco.v` and the testbench fix U9; tree `833ee9d` | defaults (not a parameter) |
| `ble-tx-1--8` | an eighth of the {cos, sin} tables (0°–45°), 256 × 16 with one port, read once per sample; 45° in a register | `vco.v` and the testbench fix U9; tree `7ff12d1` | defaults (not a parameter) |
| `ble-tx-opt` | the best of the first transmitter branches together: B2 and the {cos, sin} memory of `ble-tx-sin8`; receiver and debug memory of upstream | the files of `ble-tx-table`, and the `vco.v` of `ble-tx-sin8`; tree `c76351d` | `GAUSS_TABLE=1` |
| `ble-tx-pdu` | B2, the quarter sine table of `ble-tx-sin2` and the packet buffer with one port (256 × 8 and a register for byte 256), exact rewrites of the transmitter's counters; receiver and debug memory of upstream | from `ble-tx-opt`: `btle_tx.v`, `vco.v`, `gauss_filter.v`, `bit_repeat_upsample.v`, `crc24.v` and `scramble.v`; tree `0030050` as measured (later commits change only comments of `btle_tx.v`) | `GAUSS_TABLE=1` |
| `ble-tx-pdu-we` | `ble-tx-pdu`, with the packet buffer written only when its pair is new: the AXI clock after a write of register 8 | from `ble-tx-pdu`: `btle_tx.v`, `btle_phy.v`, `btle_controller.v` and `btle_ll.v` (a new output); tree `f61412f` | `GAUSS_TABLE=1 PDU_WRITE_STROBE=1` |
| `ble-tx-rom` | `ble-tx-pdu`, after the product audit, with the COS and SIN tables fixed: a ROM in logic of the first eighth of the wave (257 pairs), no VCO memory; the table writes are ignored | from `ble-tx-pdu` (`4e6ffc2`): `vco.v`; tree `21d60be` | `GAUSS_TABLE=1` |
| `ble-tx-cordic` | the same, with the tables computed: an exact CORDIC of the first eighth of the wave (15 iterations in one clock), no VCO memory; the table writes are ignored | from `ble-tx-pdu` (`4e6ffc2`): `vco.v`; tree `e5029a3` | `GAUSS_TABLE=1` |
| `ble-opt` | B1 + B2 + A1 + A2, plus the model-update firmware | 11 RTL files (1 new), the Vivado file list, 2 testbenches; tree `b78aa37` | `ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1` |

How they relate:

```
master  (= upstream-baseline, 8540186)
 ├─ ble-tx-sin4                  from fae132e: quarter-wave VCO tables (5df56e9)
 │   └─ ble-tx-sin8              from 8567f8d: one {cos, sin} memory (94a7bc7), its test
 │       ├─ ble-tx-sin8-1rw      from 00ad076: the memory with one port (36c1103), U9
 │       ├─ ble-tx-sin2          from 00ad076: the quarter sine table alone, one port (6d86155), U9
 │       └─ ble-tx-1--8          from 9b4ddcf: an eighth of the tables, one port (4346dd0), U9
 └─ risc-v-ble                   70cab42, 3e3086e: documentation only
     └─ 74bb17c, 69c8b51         area flow; upstream baseline measured
         ├─ ble-tx-table         + B2 alone (dfcc15c), U9 (4c8d66a), its validation
         │   ├─ ble-tx-table-reg     from f6c9f78: tables in flip-flops (e5d7f51)
         │   ├─ ble-tx-table-sram    from f6c9f78: tables in SRAM (65eefff)
         │   └─ ble-tx-opt           from e6bf731: + the vco.v of ble-tx-sin8 (516a509)
         │       └─ ble-tx-pdu       from 894e9b2: one-port packet buffer, the vco.v of ble-tx-sin2, exact rewrites (9810e88)
         │           ├─ ble-tx-pdu-we from d7c65e3: the packet buffer written only when its pair is new (73c7af6)
         │           ├─ ble-tx-rom    from 4e6ffc2: the VCO tables fixed, a ROM of an eighth of the wave (144d51b)
         │           └─ ble-tx-cordic from 4e6ffc2: the VCO tables computed by an exact CORDIC (3d9ad94)
         ├─ ble-tx-fir2          + folded FIR (05d5d95), U9 (7f45d46), its proofs
         └─ aa8a014 … 88f2250    B1 and its proofs
             ├─ ble-rx-dm        = 88f2250: B1 alone, nothing of A1, A2, B2 (RX_BRANCH_COMPARISON.md)
             └─ 39f5851 … d37ac4b    A1, A2, B2, model update, activity, timing  (ble-opt)
```

Every branch then has commits that add this document; the measurement
branches (`ble-opt`, `ble-tx-table`, `ble-rx-dm`, `ble-tx-opt`, and `ble-tx-pdu`,
`ble-tx-pdu-we`, `ble-tx-rom` and `ble-tx-cordic`, cut from `ble-tx-opt`) also carry the
comparison harness (the same files on the eight) and its results.

`ble-tx-sin8-1rw` and `ble-tx-sin2` were cut from `ble-tx-sin8` (`00ad076`) for
single-port memories of the VCO tables. Their memories were measured first,
before any RTL, in `docs/Design Decisions/VCO_MEMORY_SWEEP.md`; a third
branch cut with them, `ble-tx-sin128` (128 × 32), was deleted when that sweep
measured its memory (16 637.9 µm², not the ~7 000 µm² that motivated it).
`ble-tx-1--8`, cut later from `ble-tx-sin8` (`9b4ddcf`), builds the 256 × 16
memory that the sweep found to be the best of 4 096 bits. Each carries its own
report at its root (`TX_SIN8_1RW_COMPARISON.md`, `TX_SIN2_COMPARISON.md`,
`TX_1--8_COMPARISON.md`) and its validation runs in `results/validation/`.

`ble-tx-pdu` was cut from `ble-tx-opt` (`894e9b2`) after an analysis of what
was left of the transmitter with B2 and the memory of `ble-tx-sin2`: the packet
buffer, 64 % of it, two ports and 512 words for one byte read every 128 clocks
and at most 257 bytes. It gives the buffer one port on the AXI clock, 256 words
and a register for byte 256, and was validated with the strict runner of the
integrity audit (`docs/Validation/TX_PDU_VALIDATION.md`, on the branch).

`ble-tx-pdu-we` was cut from `ble-tx-pdu` (`d7c65e3`): the same transmitter, with
the packet buffer written only in the AXI clock after a write of register 8,
instead of on every AXI clock. It changes no output and almost no area; it is
there for power, and with it the energy of the transmitter's SRAM accesses is
measured (§ 6.6; `docs/Validation/TX_PDU_WE_VALIDATION.md`, on the branch).

`ble-tx-rom` and `ble-tx-cordic` were cut from `ble-tx-pdu` after the product audit
(`4e6ffc2`): the same transmitter, with a VCO that has no memory. Its COS and SIN
tables are fixed to the project's (`python/btlelib.py`), built from the first eighth of
the wave: a ROM in logic on `ble-tx-rom`, an exact CORDIC on `ble-tx-cordic`. The
outputs are those of the upstream VCO with those tables, on every clock, and the
table writes are ignored. `ble-tx-pdu` had set this change aside because the tables
stop being programmable. Both are measured on the audited RTL with every other
branch (§ 4.4) and validated with the product audit's campaign
(`docs/Validation/TX_ROM_VALIDATION.md` and `TX_CORDIC_VALIDATION.md`, on each).

The two isolated branches measure **exactly the code that `ble-opt`
combines**. `ble-rx-dm` is the `ble-opt` history itself, stopped at `88f2250`.
In `ble-tx-table`, `gauss_filter.v`, `gfsk_modulation.v` and `btle_tx.v` are
byte-identical to `ble-opt`, and `btle_phy.v` and `btle_controller.v` carry only
the B2 lines of `39f5851`. The transmitter branches are alternatives to B2
(`reg`, `sram`, `fir2`), independent of it (`sin4`, `sin8`, `sin8-1rw`, `sin2`
and `1--8`, which touch only `vco.v`, the last three also the testbench fix U9) or
both together (`ble-tx-opt`: every file of `ble-tx-table`, and the `vco.v` of
`ble-tx-sin8`, byte for byte; `ble-tx-pdu`: B2 rewritten exactly, the `vco.v` of
`ble-tx-sin2` without its change detector, and its own `btle_tx.v` and three
blocks; `ble-tx-pdu-we`: `ble-tx-pdu` with a write strobe for the packet
buffer; `ble-tx-rom` and `ble-tx-cordic`: `ble-tx-pdu` with another `vco.v`). None of
them is part of `ble-opt`.

A branch is measured in **its configuration: every optional reduction its
`btle_controller` declares, switched on** (`scripts/branch_config.sh`). The
parameters default to the original design on every branch, so the Vivado flow
of the boards sees upstream unless it asks otherwise; B1, the folded FIR, the
quarter-wave tables, the {cos, sin} memory, the one-port memories, the
rewrites of `ble-tx-pdu` and the VCOs without memory are the exceptions,
because they are structural.

## 2. The comparison

Differences are against `master`. `risc-v-ble` has the same `verilog/` tree
as `master`, so its figures are the same by construction: the flows are
deterministic for identical inputs, `master` reproduces the committed
`baseline-upstream` area run exactly, and it came out identical in all eight runs
(§§ 3, 6.1).

† `ble-tx-rom` and `ble-tx-cordic` exist only after the product audit, so their
columns are of the audited RTL, from run `tx-vco` (§§ 4.4, 5.1), at the revisions it
measured (`144d51b`, `3d9ad94`: before the lint closure, `LINT_CLOSURE.md`), and their
differences are against corrected `master` (`5abbbf7`) in the same run: 52 497 cells,
4 722 flip-flops, 74 746 µm² of cells, 1 136 070 SRAM bits, a transmitter of
171 284 µm² and a minimum period of 3.458 ns. In that run `ble-tx-pdu` measures
48 192 cells, 4 443 flip-flops, 68 833 µm² and a transmitter of 20 237 µm² (−88.2 %),
1.904 ns: the two columns are to be read against those figures, not against the
`ble-tx-pdu` column below, which is of the RTL before the audit. The controller's cells
and flip-flops come from the netlists of the timing run, which uses the area flow of
§ 3 (the same counts as the area run on `master`); the SRAM bits are those of
`ble-tx-pdu` without its sine table (4 096 bits: the VCO has no macro). Their switching
activity was not measured (§ 10), and they were validated at module and controller
level against corrected `master`, not in the gate-level lockstep of § 6.1 (§ 7).

| | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` | `ble-tx-rom` † | `ble-tx-cordic` † | `ble-opt` |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Content** | upstream BTLE (+ thesis docs on `risc-v-ble`) | **B2** | B2's tables in flip-flops | B2's tables in SRAM | folded FIR | quarter-wave VCO tables | one {cos, sin} memory for the quarter-wave tables | the {cos, sin} memory with **one port** | the quarter **sine** table alone, **one port** | an **eighth** of the {cos, sin} tables, **one port** | **B2 + the {cos, sin} memory** | **B2**, the quarter **sine** table and the **packet buffer** with **one port**, exact counters | as `ble-tx-pdu`, the packet buffer written only when its pair is **new** (a write strobe) | **B2**, the packet buffer of `ble-tx-pdu`, **no VCO memory**: the tables fixed in a **ROM** (an eighth of the wave, 257 pairs) | as `ble-tx-rom`, the tables computed by an **exact CORDIC** (15 iterations in one clock) | **B1 + B2 + A1 + A2** |
| Configuration measured | defaults | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | defaults | defaults | defaults | defaults | defaults | defaults | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | `GAUSS_TABLE=1`, `PDU_WRITE_STROBE=1` | `GAUSS_TABLE=1` | `GAUSS_TABLE=1` | `ENABLE_IQ_CAPTURE=0`, `LL_MINIMAL=1`, `GAUSS_TABLE=1` |
| GFSK demodulators in `btle_rx` | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | 8 | **1, shared** |
| Gaussian filter | FIR, runtime taps | **fixed-tap table** | **table in 2 560 flip-flops**, runtime taps | **table in SRAM**, runtime taps | **folded FIR**, runtime taps | FIR, runtime taps | FIR, runtime taps | FIR, runtime taps | FIR, runtime taps | FIR, runtime taps | **fixed-tap table** | **fixed taps**, paired | **fixed taps**, paired | **fixed taps**, paired | **fixed taps**, paired | **fixed-tap table** |
| VCO COS / SIN tables | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | 2 × 2 048 × 8 | **2 × 512 × 8** | **1 × 512 × 16** ({cos, sin}) | **1 × 512 × 16** ({cos, sin}), one port | **1 × 512 × 8** (sine), one port; cos 0 in a register | **1 × 256 × 16** ({cos, sin}, 0°–45°), one port; 45° in a register | **1 × 512 × 16** ({cos, sin}) | **1 × 512 × 8** (sine), one port; cos 0 in a register | **1 × 512 × 8** (sine), one port; cos 0 in a register | **none**: fixed, a ROM in logic of 257 {cos, sin} pairs (0°–45°) | **none**: fixed, computed by a CORDIC | 2 × 2 048 × 8 |
| IQ-capture debug RAM (1 Mbit) | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | yes | **removed** |
| Link Layer | full | full | full | full | full | full | full | full | full | full | full | full | full | full | full | **minimal** |
| **Std cells, `btle_controller`** | 50 295 | 48 227 (−4.1 %) | 58 091 (+15.5 %) | 49 324 (−1.9 %) | 49 620 (−1.3 %) | 50 397 (+0.2 %) | 50 716 (+0.8 %) | 50 708 (+0.8 %) | 50 621 (+0.6 %) | 50 904 (+1.2 %) | 48 559 (−3.5 %) | 48 164 (−4.2 %) | 48 056 (−4.5 %) | 48 250 (−8.1 %) † | 49 763 (−5.2 %) † | **16 102 (−68.0 %)** |
| Flip-flops | 4 578 | 4 422 (−3.4 %) | 7 222 (+57.8 %) | 4 667 (+1.9 %) | 4 570 (−0.2 %) | 4 581 (+0.1 %) | 4 656 (+1.7 %) | 4 642 (+1.4 %) | 4 639 (+1.3 %) | 4 654 (+1.7 %) | 4 500 (−1.7 %) | 4 430 (−3.2 %) | 4 432 (−3.2 %) | 4 411 (−6.6 %) † | 4 411 (−6.6 %) † | 2 673 (−41.6 %) |
| Cell area (µm²) | 71 706 | 68 667 (−4.2 %) | 91 556 (+27.7 %) | 70 896 (−1.1 %) | 70 652 (−1.5 %) | 71 863 (+0.2 %) | 72 484 (+1.1 %) | 72 414 (+1.0 %) | 72 278 (+0.8 %) | 72 617 (+1.3 %) | 69 412 (−3.2 %) | 68 767 (−4.1 %) | 68 767 (−4.1 %) | 68 739 (−8.0 %) † | 70 270 (−6.0 %) † | 26 681 (−62.8 %) |
| **SRAM bits** | 1 136 070 | 1 136 070 | 1 136 070 | 1 138 630 (+0.2 %) | 1 136 070 | 1 111 494 (−2.2 %) | 1 111 494 (−2.2 %) | 1 111 494 (−2.2 %) | 1 107 398 (−2.5 %) | 1 107 398 (−2.5 %) | 1 111 494 (−2.2 %) | 1 105 350 (−2.7 %) | 1 105 350 (−2.7 %) | 1 101 254 (−3.1 %) † | 1 101 254 (−3.1 %) † | **87 046 (−92.3 %)** |
| **Transmitter with its SRAM macros (µm², § 4)** | 167 731 | 164 734 (−1.8 %) | 187 610 (+11.9 %) | 185 280 (+10.5 %) | 166 704 (−0.6 %) | **76 552 (−54.4 %)** | **67 437 (−59.8 %)** | **46 773 (−72.1 %)** | **40 293 (−76.0 %)** | **40 359 (−75.9 %)** | **64 441 (−61.6 %)** | **20 098 (−88.0 %)** | **20 098 (−88.0 %)** | **9 489 (−94.5 %)** † | **11 121 (−93.5 %)** † | 164 734 (−1.8 %) |
| Min period at 16 MHz (62.5 ns) | 1.991 ns | 1.905 ns | 1.995 ns | 2.011 ns | 1.877 ns | 2.007 ns | 1.910 ns | 1.974 ns | 1.938 ns | 1.949 ns | 1.917 ns | 1.919 ns | 2.050 ns | 2.002 ns † | 5.501 ns † | 1.944 ns |
| Slack / Fmax | +60.509 ns / 502 MHz | +60.595 ns / 525 MHz | +60.505 ns / 501 MHz | +60.489 ns / 497 MHz | +60.623 ns / 533 MHz | +60.493 ns / 498 MHz | +60.590 ns / 524 MHz | +60.526 ns / 507 MHz | +60.562 ns / 516 MHz | +60.551 ns / 513 MHz | +60.583 ns / 522 MHz | +60.581 ns / 521 MHz | +60.450 ns / 488 MHz | +60.498 ns / 500 MHz † | +56.999 ns / 182 MHz † | +60.556 ns / 514 MHz |
| Worst path | demodulator multiply, one of 8 copies | Link Layer 64-bit timestamp | demodulator multiply, one of 8 copies | the same | the same | the same | Link Layer 64-bit timestamp | demodulator multiply, one of 8 copies | demodulator multiply, one of 8 copies | demodulator multiply, one of 8 copies | demodulator multiply, one of 8 copies | demodulator multiply, one of 8 copies | Link Layer 64-bit timestamp | demodulator multiply, one of 8 copies | **the CORDIC**, in the transmitter | Link Layer 64-bit timestamp |
| **Data + clock switched capacitance, `mixed`** | 1.25 × 10⁹ fF | −3.2 % | +40.8 % | +0.6 % | −0.5 % | +0.1 % | +1.3 % | +1.3 % | +1.8 % | +1.5 % | −1.8 % | −2.2 % | −2.1 % | not measured | not measured | **−30.3 %** |
| … over the 5 scenarios | — | −2.3 to −5.0 % | +39.9 to +53.0 % (4 scenarios, § 6.1) | +0.6 to +1.8 % (4 scenarios) | −0.1 to −1.1 % | 0 to +0.4 % | +1.2 to +1.8 % | +1.0 to +1.9 % | +0.9 to +3.4 % | +1.2 to +2.3 % | −1.1 to −3.1 % | −2.2 to −3.0 % | −2.1 to −2.9 % | — | — | −25.5 to −34.7 % |
| Clock pins (load × toggles) | 8.76 × 10⁸ fF | −3.4 % | +57.3 % | +1.9 % | −0.2 % | +0.1 % | +1.7 % | +1.4 % | +1.3 % | +1.6 % | −1.7 % | −3.2 % | −3.2 % | not measured | not measured | −41.4 % |
| Non-clock toggles / cycle, `mixed` | 984.3 | 956.4 (−2.8 %) | 988.0 (+0.4 %) | 958.7 (−2.6 %) | 971.0 (−1.4 %) | 987.0 (+0.3 %) | 989.4 (+0.5 %) | 994.3 (+1.0 %) | 1012.1 (+2.8 %) | 996.0 (+1.2 %) | 962.7 (−2.2 %) | 985.4 (+0.1 %) | 983.6 (−0.1 %) | not measured | not measured | 939.7 (−4.5 %) |
| Nets with activity > 10 %, `mixed` | 839 | 827 | 836 | 824 | 841 | 851 | 845 | 882 | 951 | 887 | 837 | 954 | 951 | not measured | not measured | 3 908 (×4.7) |
| RAM-port toggles, `mixed` | 3 044 741 | unchanged | unchanged | +10.8 % | unchanged | −0.4 % | −0.4 % | −0.4 % | +7.0 % | −0.5 % | −0.4 % | +7.2 % | +7.1 % | not measured | not measured | −40.0 % |
| Functions removed | — | runtime Gaussian taps | none; 928 clocks after a tap write before the next transmission | the same | none | COS/SIN tables without quarter-wave symmetry | as `ble-tx-sin4`; table writes limited to w + 1 in any w clocks (§ 8) | as `ble-tx-sin4`; a table write waits for a clock without a read (§ 8) | as `ble-tx-sin4`, and the COS table apart from cos 0; sine writes wait while transmitting; one sample every two clocks at most (§ 8) | as `ble-tx-sin4`; cos[k] and sin[512 − k] stored as one; a table write waits for a clock without a read (§ 8) | runtime Gaussian taps; COS/SIN tables as `ble-tx-sin8` (§ 8) | runtime Gaussian taps; COS/SIN tables as `ble-tx-sin2`; a packet byte rewritten while it is being read (§ 8) | runtime Gaussian taps; COS/SIN tables as `ble-tx-sin2`; a packet byte rewritten while it is being read (§ 8) | runtime Gaussian taps; **the COS/SIN tables**, fixed (writes ignored); a packet byte rewritten while it is being read (§ 8) | as `ble-tx-rom` (§ 8) | runtime taps, IQ capture, UART HCI, 1 PPS, latency counter |
| Gate-level outputs vs upstream, 5 scenarios | — | identical, every output | identical in 4; `tx` transmits before the rebuild (§ 6.1) | the same | identical, every output | identical, every output | identical, every output | identical, every output | identical, every output | identical, every output | identical, every output | identical, every output | identical, every output | not run; module and controller lockstep against corrected `master` (§ 7) | the same | identical, except the 3 removed outputs |

## 3. Area

Same flow as every earlier run: Yosys 0.68, `synth -flatten`, `dfflibmap`,
`abc -liberty`, Nangate45, SRAMs blackboxed and counted in bits. All 16 tops
were synthesised for each branch; results in
[`results/area/all-branches/`](../../results/area/all-branches/),
[`results/area/tx-variants/`](../../results/area/tx-variants/),
[`results/area/tx-sin8/`](../../results/area/tx-sin8/),
[`results/area/tx-opt/`](../../results/area/tx-opt/),
[`results/area/tx-1rw/`](../../results/area/tx-1rw/),
[`results/area/tx-1--8/`](../../results/area/tx-1--8/),
[`results/area/tx-pdu/`](../../results/area/tx-pdu/) and
[`results/area/tx-pdu-we/`](../../results/area/tx-pdu-we/). Every
configuration reproduces its earlier area run top for top: `master` =
`baseline-upstream` (in all eight runs), `ble-tx-table` = `tx-table`,
`ble-opt` = `sticker`; the Gaussian filter and the
transmitter of `ble-tx-table-reg`, `ble-tx-table-sram` and `ble-tx-fir2` =
run `tx-area` of `GAUSS_FILTER_OPTIONS.md`, and the transmitter of
`ble-tx-sin4` = its own `TX_SIN4_COMPARISON.md`. On `ble-tx-opt`, the
Gaussian filter synthesises exactly as on `ble-tx-table` and the VCO exactly
as on `ble-tx-sin8` (the same files).

### 3.1 Per block (std cells, each top synthesised alone)

| Top | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `gauss_filter` | 2 286 | **253** (−88.9 %) | 10 097 (+341.7 %) | 1 362 (−40.4 %) | **1 560** (−31.8 %) | 2 286 | 2 286 | 2 286 | 2 286 | 2 286 | **253** (−88.9 %) | **166** (−92.7 %) | **166** (−92.7 %) | **253** (−88.9 %) |
| `vco` | 86 | 86 | 86 | 86 | 86 | 179 (+108.1 %) | 438 (+409.3 %) | 426 (+395.3 %) | 408 (+374.4 %) | 645 (+650.0 %) | 438 (+409.3 %) | 349 (+305.8 %) | 349 (+305.8 %) | 86 |
| `btle_tx` | 3 409 | **1 392** (−59.2 %) | 11 328 (+232.3 %) | 2 477 (−27.3 %) | **2 707** (−20.6 %) | 3 465 (+1.6 %) | 3 718 (+9.1 %) | 3 729 (+9.4 %) | 3 687 (+8.2 %) | 3 939 (+15.5 %) | **1 696** (−50.2 %) | **1 305** (−61.7 %) | **1 299** (−61.9 %) | **1 392** (−59.2 %) |
| `btle_rx` | 36 864 | 36 884 | 36 954 | 36 954 | 36 980 | 36 884 | 36 928 | 36 952 | 36 928 | 36 951 | 36 931 | 36 940 | 36 910 | **10 068** (−72.7 %) |
| `btle_phy` | 40 339 | 38 083 (−5.6 %) | 48 192 (+19.5 %) | 39 294 (−2.6 %) | 39 655 (−1.7 %) | 40 384 (+0.1 %) | 40 573 (+0.6 %) | 40 550 (+0.5 %) | 40 593 (+0.6 %) | 40 964 (+1.5 %) | 38 600 (−4.3 %) | 38 143 (−5.4 %) | 38 136 (−5.5 %) | 11 394 (−71.8 %) |
| `auxiliary_daemon` | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | 299 | **233** (−22.1 %) |
| `btle_ll` | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 453 | 9 478 | **4 336** (−54.1 %) |
| **`btle_controller`** | **50 295** | **48 227** (−4.1 %) | **58 091** (+15.5 %) | **49 324** (−1.9 %) | **49 620** (−1.3 %) | **50 397** (+0.2 %) | **50 716** (+0.8 %) | **50 708** (+0.8 %) | **50 621** (+0.6 %) | **50 904** (+1.2 %) | **48 559** (−3.5 %) | **48 164** (−4.2 %) | **48 056** (−4.5 %) | **16 102** (−68.0 %) |

The cell counts leave out the RAMs. `ble-tx-table-sram` moves 2 560 bits of
its table into SRAM banks (controller: 1 138 630 SRAM bits);
`ble-tx-sin4`, `ble-tx-sin8`, `ble-tx-sin8-1rw` and `ble-tx-opt` remove 24 576
bits (1 111 494), which all but `ble-tx-sin4` keep in one memory instead of
two; `ble-tx-sin2` and `ble-tx-1--8` remove 28 672 (1 107 398), keeping the
quarter sine table alone or an eighth of both tables; `ble-tx-pdu` keeps the
memory of `ble-tx-sin2` and halves the packet buffer (1 105 350: 2 048 bits
fewer, byte 256 in a register), and `ble-tx-pdu-we` has the same memories; § 4
converts the transmitter's RAMs into area.

Each change moves only its own block. The small moves elsewhere (`btle_rx`
36 864 → 36 884 … 36 980 on the transmitter branches) are the flow noise
already recorded on `ble-opt`: ABC's result depends on everything Yosys reads.

### 3.2 The savings add up

| Saving on `btle_controller` | Std cells | Flip-flops |
|---|---:|---:|
| B2 alone (`ble-tx-table`) | 2 068 | 156 |
| B1 alone (`ble-rx-dm`, [RX_BRANCH_COMPARISON.md](RX_BRANCH_COMPARISON.md) § 3) | 26 949 | 652 |
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
transmitter). The one-port branches spend less on it: `ble-tx-sin8-1rw` holds a
waiting write in the table registers instead of a queue and adds a 16-bit
register for a write to the entry being read (VCO: 426 cells, 79 flip-flops,
against 438 and 93 on `ble-tx-sin8`), and `ble-tx-sin2` writes one table and
holds the two entries of a sample (VCO: 408 cells, 76 flip-flops). On the
transmitter they are 75.2 and 144.7 µm² below `ble-tx-sin8`. `ble-tx-1--8`
schedules its port as `ble-tx-sin8-1rw` and adds the eighth-wave mapping: a
second reflection of the address, the cosine/sine swap past 45°, the 45°
register and the routing of each write to its half (VCO: 645 cells, 91
flip-flops); its transmitter is 200.3 µm² above `ble-tx-sin8`.

`ble-tx-opt` checks that the two transmitter changes add up, built into one
design. On `btle_tx`:

| | Std cells | Flip-flops | Cell area (µm²) |
|---|---:|---:|---:|
| B2 (`ble-tx-table` − `master`) | −2 017 | −156 | −2 997.3 |
| {cos, sin} memory (`ble-tx-sin8` − `master`) | +309 | +78 | +702.5 |
| **Sum of the parts, from `master`** | **1 701** | **326** | **3 028.1** |
| **Measured, `ble-tx-opt`** | **1 696** | **326** | **3 028.9** |
| Residual | −5 | 0 | +0.8 |

On the whole controller the flip-flops add up exactly (4 578 − 156 + 78 =
4 500) and the cells to within 89 (0.2 %), less than the noise of the
unchanged receiver (36 864 to 36 980 cells from one netlist to another).

`ble-tx-pdu` cannot be checked the same way: its packet buffer and its
rewrites exist on no other branch. Its parts are measured block by block in
`TX_PDU_VALIDATION.md` § 3. Its transmitter logic, 2 415.5 µm² (1 305 cells,
256 flip-flops), has the fewest cells of all branches, and 89.9 µm² more area
than `ble-tx-table`, whose VCO keeps upstream's tables in memory and has no port
logic; with the memories counted it is by far the smallest (§ 4.2).
`ble-tx-pdu-we` adds the write strobe to it: two flip-flops on the controller
(4 430 → 4 432: `write_pending` in the buffer, and `baremetal_phy_intf_mode`
one clock ago in `btle_controller`) and the Link Layer's comparator (+25 cells
in `btle_ll`). Its `btle_tx` synthesises to 1 299 cells and 2 415.0 µm², 6
cells and 0.5 µm² fewer than that of `ble-tx-pdu`, which is below the flow's
noise (§ 3.1).

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

| RAM | RTL | Every other branch | `ble-tx-sin4` | `ble-tx-sin8`, `ble-tx-opt` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-pdu`, `ble-tx-pdu-we` | Written | Read |
|---|---|---|---|---|---|---|---|---|---|---|
| COS table | `vco.v`, `sdpram_one_clk` | 2 048 × 8 | 512 × 8 | one 512 × 16, {cos, sin} per word, with a write mask of one bit per table | the same 512 × 16, with **one port** | none: cos x = sin(90° − x), cos 0 in an 8-bit register | one 256 × 16, {cos, sin} of 0°–45°, with a write mask, **one port**; past 45° the swapped word at 90° − x; 45° in an 8-bit register | as `ble-tx-sin2` | from the table registers, on every clock (`write_enable` tied to 1); from `ble-tx-sin8` on, when a register changes, through one shared port; on the one-port branches, in a clock without a read | at the VCO phase, on every clock; on the one-port branches, in every clock without a write (`ble-tx-sin2`: entry b of the next phase in the clock of a sample, entry a otherwise) |
| SIN table | `vco.v`, `sdpram_one_clk` | 2 048 × 8 | 512 × 8 | (the same word) | (the same word) | one 512 × 8, **one port** | (the same word) | one 512 × 8, **one port** (as `ble-tx-sin2`) | the same | the same |
| PDU buffer | `btle_tx.v`, `sdpram_two_clk` | 512 × 8 | 512 × 8 | 512 × 8 | 512 × 8 | 512 × 8 | 512 × 8 | **256 × 8, one port**, on `clkb`, `sdpram_one_clk`; byte 256 in an 8-bit register | by the processor side, on `clkb`, every clock (on `ble-tx-pdu`, every clock but the one that reads; on `ble-tx-pdu-we`, once per new pair) | by the packet path, on `clk` (on `ble-tx-pdu`, on `clkb`, one byte when the packet path asks, 12 clocks before it takes it) |

`ble-tx-table-sram` adds the three Gaussian-table banks, 2 560 bits,
18 437.4 µm² (`GAUSS_FILTER_OPTIONS.md` § 3). The receiver is not converted.
In the RTL of `ble-tx-sin8`, and of `ble-tx-opt`, which has the same `vco.v`,
the 512 × 16 memory is written as its two halves, two `sdpram_one_clk` that
share the write and read addresses (the mask bits are their write enables); it
is one macro. `ble-tx-sin8-1rw` and `ble-tx-1--8` keep that model (256 words
on `ble-tx-1--8`), and `ble-tx-sin2` one `sdpram_one_clk`, but they never write
and read it in the same clock: a
one-port macro takes the write address in a clock with a write, in which it
keeps its output, and the read address in the others. The model's read port
also reads in a clock with a write; the VCO keeps it on an entry that no write
has changed, or does not show it (both reports explain why), and their tests
check, on every clock, that the VCO outputs are the same with a one-port macro
model. The packet buffer of `ble-tx-pdu` is one `sdpram_one_clk` with one
address for both of its ports, so the address multiplexer of a one-port macro
is in its logic; its test runs it on a one-port macro model as well.

### 4.1 The macros

OpenRAM 1.2.48 in FreePDK45, the process behind the Nangate45 cells, default
layout, in two port sets (`scripts/area/run_openram.sh`, runs
[`openram-tx`](../../results/area/openram-tx/summary.md) and
[`openram-sin8`](../../results/area/openram-sin8/summary.md); run
[`openram-1rw-sweep`](../../results/area/openram-1rw-sweep/summary.md) gives the
two 1RW macros above the same areas, and the 256 × 16 one of `ble-tx-1--8`; run
[`openram-pdu`](../../results/area/openram-pdu/summary.md) the 256 × 8 packet
buffer of `ble-tx-pdu`):

| Macro | Ports | Words × bits | Size (µm) | Area (µm²) | µm² per bit |
|---|---|---|---|---:|---:|
| `sram_1rw1r_8x2048` | 1 read/write + 1 read | 2 048 × 8 | 232.930 × 297.730 | 69 350.2 | 4.23 |
| `sram_1rw1r_8x512` | 1 read/write + 1 read | 512 × 8 | 146.120 × 162.250 | 23 708.0 | 5.79 |
| `sram_1rw1r_16x512_m8` | 1 read/write with an 8-bit write mask + 1 read | 512 × 16 | 230.000 × 163.930 | 37 703.9 | 4.60 |
| `sram_1rw_8x2048` | 1 read/write | 2 048 × 8 | 136.623 × 232.907 | 31 820.4 | 1.94 |
| `sram_1rw_8x512` | 1 read/write | 512 × 8 | 85.285 × 125.507 | 10 703.9 | 2.61 |
| `sram_1rw_16x512_m8` | 1 read/write with an 8-bit write mask | 512 × 16 | 135.157 × 126.627 | 17 114.7 | 2.09 |
| `sram_1rw_16x256_m8` | 1 read/write with an 8-bit write mask | 256 × 16 | 86.385 × 120.680 | 10 424.9 | 2.55 |
| `sram_1rw_8x256` | 1 read/write | 256 × 8 | 85.290 × 81.828 | 6 979.1 | 3.41 |

- **1RW1R is the macro the RTL needs**, and the one used below, except for the
  VCO memory of `ble-tx-sin8-1rw`, `ble-tx-sin2` and `ble-tx-1--8`: every other
  RAM of the transmitter is a simple dual-port model whose write port and read
  port work in the same cycle, and the PDU buffer has a clock on each side.
- **The three one-port branches need 1RW for the VCO memory**, because their
  RTL never writes it in a clock in which it reads. Their PDU buffer stays
  1RW1R.
- **`ble-tx-pdu` and `ble-tx-pdu-we` need 1RW for both**: their VCO memory as
  `ble-tx-sin2`, and their packet buffer, which they never write in the clock
  that reads it (256 × 8: 6 979.1 µm², against 16 750.2 with a second port, run
  `openram-pdu`).
- **1RW for every RAM is a lower bound.** One port for the other memories
  would need their RTL to schedule the port the same way, which only
  `ble-tx-pdu` does, for the packet buffer.
- **A quarter of the bits is a third of the area.** The periphery (decoders,
  sense amplifiers, write drivers, control, supply rings) does not shrink with
  the array: 512 × 8 costs 34 % of 2 048 × 8, in both port sets.
- **One 16-bit macro costs 20 % less than two 8-bit ones** (37 703.9 against
  47 415.9 µm²; 20.1 % with one port). The two tables share the address
  decoders, word-line drivers, control and rings, but each bit keeps its
  column, sense amplifier and write driver.

### 4.2 Total area of the transmitter

`btle_tx` std-cell area (§ 3.1) plus its macros. **Total** counts the macros
the RTL needs: 1RW1R for every RAM, except the VCO memory of the three one-port
branches, which is 1RW (17 114.7, 10 703.9 and 10 424.9 µm²), and both memories
of `ble-tx-pdu` and `ble-tx-pdu-we` (10 703.9 and 6 979.1 µm²). **Total, all 1RW**
is the lower bound with a one-port macro for every RAM. The estimated rows are
not built: they add the measured change of `ble-tx-sin8`, `ble-tx-sin2` or
`ble-tx-1--8` (its logic and its memory) to `ble-tx-fir2` or `ble-tx-table`.
The same estimate made for `ble-tx-table` with the memory of `ble-tx-sin8` gave
64 440.0 µm²; built, as `ble-tx-opt`, it measures 64 440.8.

| Branch | `btle_tx` cells (µm²) | Gaussian-table macros | COS + SIN macros | PDU buffer | **Total (µm²)** | vs `master` | Total, all 1RW (µm²) | vs `master` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `master` / `risc-v-ble` | 5 322.9 | — | 138 700.5 | 23 708.0 | **167 731.4** | — | 79 667.6 | — |
| `ble-tx-table` | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 734.1** | −1.8 % | 76 670.3 | −3.8 % |
| `ble-tx-table-reg` | 25 201.6 | — | 138 700.5 | 23 708.0 | **187 610.1** | +11.9 % | 99 546.3 | +25.0 % |
| `ble-tx-table-sram` | 4 434.5 | 18 437.4 | 138 700.5 | 23 708.0 | **185 280.4** | +10.5 % | 97 216.6 | +22.0 % |
| `ble-tx-fir2` | 4 295.9 | — | 138 700.5 | 23 708.0 | **166 704.4** | −0.6 % | 78 640.6 | −1.3 % |
| **`ble-tx-sin4`** | 5 427.7 | — | **47 415.9** | 23 708.0 | **76 551.6** | **−54.4 %** | 37 539.4 | **−52.9 %** |
| **`ble-tx-sin8`** | 6 025.4 | — | **37 703.9** | 23 708.0 | **67 437.3** | **−59.8 %** | 33 844.0 | **−57.5 %** |
| **`ble-tx-sin8-1rw`** | 5 950.2 | — | **17 114.7** (1RW) | 23 708.0 | **46 772.8** | **−72.1 %** | 33 768.8 | **−57.6 %** |
| **`ble-tx-sin2`** | 5 880.7 | — | **10 703.9** (1RW) | 23 708.0 | **40 292.6** | **−76.0 %** | 27 288.5 | **−65.7 %** |
| **`ble-tx-1--8`** | 6 225.7 | — | **10 424.9** (1RW) | 23 708.0 | **40 358.6** | **−75.9 %** | 27 354.5 | **−65.7 %** |
| **`ble-tx-opt`** | **3 028.9** | — | **37 703.9** | 23 708.0 | **64 440.8** | **−61.6 %** | 30 847.5 | **−61.3 %** |
| **`ble-tx-pdu`** | **2 415.5** | — | **10 703.9** (1RW) | **6 979.1** (1RW, 256 × 8) | **20 098.5** | **−88.0 %** | 20 098.5 | **−74.8 %** |
| **`ble-tx-pdu-we`** | **2 415.0** | — | **10 703.9** (1RW) | **6 979.1** (1RW, 256 × 8) | **20 098.0** | **−88.0 %** | 20 098.0 | **−74.8 %** |
| `ble-opt` | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 734.1** | −1.8 % | 76 670.3 | −3.8 % |
| *estimate: `ble-tx-sin8` + `ble-tx-fir2`* | *4 998.4* | — | *37 703.9* | *23 708.0* | *66 410.3* | *−60.4 %* | *32 817.0* | *−58.8 %* |
| *estimate: `ble-tx-sin2` + `ble-tx-table` (B2)* | *2 883.4* | — | *10 703.9* | *23 708.0* | *37 295.3* | *−77.8 %* | *24 291.2* | *−69.5 %* |
| *estimate: `ble-tx-sin2` + `ble-tx-fir2`* | *4 853.7* | — | *10 703.9* | *23 708.0* | *39 265.6* | *−76.6 %* | *26 261.5* | *−67.0 %* |
| *estimate: `ble-tx-1--8` + `ble-tx-table` (B2)* | *3 228.4* | — | *10 424.9* | *23 708.0* | *37 361.3* | *−77.7 %* | *24 357.2* | *−69.4 %* |

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
4. **One port cuts the table memory by more than half again.** The
   transmitter takes one sample every two clocks, so one port has time for the
   reads and the writes (`VCO_MEMORY_SWEEP.md` § 1). `ble-tx-sin8-1rw` keeps
   the 512 × 16 {cos, sin} memory with one port: 37 703.9 → 17 114.7 µm², with
   75.2 µm² less logic than `ble-tx-sin8`, and the transmitter goes to
   46 773 µm², −72.1 % against `master` and −30.6 % against `ble-tx-sin8`.
   `ble-tx-sin2` keeps only the quarter sine table, 512 × 8 with one port
   (10 703.9 µm²), read twice per sample, with 144.7 µm² less logic than
   `ble-tx-sin8`: 40 293 µm², −76.0 % against `master`, the smallest
   transmitter built before `ble-tx-pdu` (point 7). `ble-tx-1--8` keeps the same 4 096 bits in the 256 × 16
   memory the sweep found best (10 424.9 µm²) and reads it once per sample, but
   its eighth-wave logic costs 345.0 µm² more than that of `ble-tx-sin2`, so
   the 279.0 µm² it saves on the memory come back with 66 more: 40 359 µm²,
   −75.9 %. The two are the same size within 0.2 %; `ble-tx-1--8` keeps one
   read per sample, so its tables can be written while transmitting and its
   VCO takes a sample on any clock. Their price is again function, not area:
   table writes wait for clocks without a read, and on `ble-tx-sin2` and
   `ble-tx-1--8` the cosine and sine tables are tied (cos[k] = sin[512 − k], § 8).
   With these memories the PDU buffer, untouched until `ble-tx-pdu`, becomes
   the largest part of the transmitter: 51 % of it on `ble-tx-sin8-1rw`, 59 % on
   `ble-tx-sin2` and `ble-tx-1--8`.
5. **The Gaussian-filter options hardly move the real total.** B2 saves
   1.8 % of the transmitter (3.8 % with 1RW), the folded FIR 0.6 %, and the
   rewritable tables add 10 to 12 % (22 to 25 % with 1RW).
   `GAUSS_FILTER_OPTIONS.md` ranks them right within the filter; this puts the
   filter in scale.
6. **The two kinds of change add.** The VCO branches touch only `vco.v`, the
   Gaussian branches only the filter. `ble-tx-opt` builds B2 with the memory
   of `ble-tx-sin8`: 64 440.8 µm², −61.6 % against `master` (−61.3 % with
   1RW), 0.8 µm² from the estimate made from the two branches apart. Its
   logic, 3 028.9 µm², is less than the upstream Gaussian filter alone
   (3 366.0), and the memories are 95 % of it. With the folded FIR instead of
   B2, which keeps the taps programmable, the estimate is 66 410 µm²
   (−60.4 %). With the memory of `ble-tx-sin2`, B2 is estimated at
   37 295 µm² (−77.8 %) and the folded FIR at 39 266 µm² (−76.6 %); with that
   of `ble-tx-1--8`, B2 at 37 361 µm² (−77.7 %). The one of B2 with the memory
   of `ble-tx-sin2` is built inside `ble-tx-pdu` (point 7); the others are not.
7. **The packet buffer halves the smallest transmitter again (`ble-tx-pdu`).**
   The transmitter reads one byte every 128 clocks and only bytes 0 to 256,
   so the buffer needs neither two ports nor 512 words. With one port on the
   AXI clock, 256 words and a register for byte 256, it is 6 979.1 µm² instead
   of 23 708.0, for 179.6 µm² of logic (the request, its synchronizer, the
   register of the byte read, byte 256 and the address multiplexer). With B2
   in its paired form, the memory of `ble-tx-sin2` and exact rewrites of the
   counters, the transmitter measures 20 098.5 µm²: −88.0 % against `master`,
   −50.1 % against `ble-tx-sin2`. Its logic, 2 415.5 µm², is 12 % of it; the
   two memories are the rest, and the sine table is now the larger one. Its
   price is one more contract: the packet is written before `tx_start`, as the
   upstream testbenches do (§ 8). `ble-tx-pdu-we` writes that buffer only when
   its pair is new: the same macros, two flip-flops more, and 20 098.0 µm²; its
   point is the energy of the buffer (§ 6.6).
8. **Without a VCO memory the transmitter halves again** (§ 4.4, on the audited
   RTL): `ble-tx-rom` fixes the tables in a ROM of 593.2 µm² and measures
   9 488.5 µm², −94.5 % against `master` and −53.1 % against `ble-tx-pdu`.

### 4.4 Every transmitter on the audited RTL, and the VCO without memory

The figures of §§ 3–4.3 are of the RTL before the product audit, whose
corrections changed the transmitter of every branch (`PRODUCT_VALIDATION.md`).
Run [`tx-vco`](../../results/area/tx-vco/summary.md) measures the VCO and the
whole transmitter (`btle_tx`) of every branch again, each at its head after
the audit (2026-10-05, the revisions in its `provenance.txt`), with the flow of
§ 3 (`scripts/area/run_area.sh`) and the
configuration of § 1; `master`'s `verilog/` is corrected `master`'s
(`5abbbf7`), which is also `risc-v-ble`'s. The macros are those of § 4.2: their
areas depend on their geometry only, which the audit did not change. The lint
closure of 2026-10-06 (`LINT_CLOSURE.md`) changed the RTL of every branch after
this run (explicit widths, illegal states that recover to idle, the CORDIC's
unused last angle removed) and was validated, not measured again: §§ 4.4 and 5.1
describe the revisions before it.

| Branch | `vco` cells (µm²) | `btle_tx` cells (µm²) | before the audit (§ 4.2) | Gaussian-table macros | COS + SIN macros | PDU buffer | **Total (µm²)** | vs `master` | Total, all 1RW (µm²) | vs `master` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `master` / `risc-v-ble` | 150.0 | 8 875.6 | 5 322.9 | — | 138 700.5 | 23 708.0 | **171 284.1** | — | 83 220.3 | — |
| `ble-tx-table` | 150.0 | 2 360.8 | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 769.3** | −3.8 % | 76 705.5 | −7.8 % |
| `ble-tx-table-reg` | 150.0 | 28 672.7 | 25 201.6 | — | 138 700.5 | 23 708.0 | **191 081.2** | +11.6 % | 103 017.4 | +23.8 % |
| `ble-tx-table-sram` | 150.0 | 7 883.2 | 4 434.5 | 18 437.4 | 138 700.5 | 23 708.0 | **188 729.1** | +10.2 % | 100 665.3 | +21.0 % |
| `ble-tx-fir2` | 150.0 | 7 698.6 | 4 295.9 | — | 138 700.5 | 23 708.0 | **170 107.1** | −0.7 % | 82 043.3 | −1.4 % |
| `ble-tx-sin4` | 274.2 | 9 029.1 | 5 427.7 | — | **47 415.9** | 23 708.0 | **80 153.0** | −53.2 % | 41 140.8 | −50.6 % |
| `ble-tx-sin8` | 870.6 | 9 571.2 | 6 025.4 | — | **37 703.9** | 23 708.0 | **70 983.1** | −58.6 % | 37 389.8 | −55.1 % |
| `ble-tx-sin8-1rw` | 796.9 | 9 605.3 | 5 950.2 | — | **17 114.7** (1RW) | 23 708.0 | **50 427.9** | −70.6 % | 37 423.9 | −55.0 % |
| `ble-tx-sin2` | 740.0 | 9 208.4 | 5 880.7 | — | **10 703.9** (1RW) | 23 708.0 | **43 620.3** | −74.5 % | 30 616.2 | −63.2 % |
| `ble-tx-1--8` | 1 059.7 | 9 790.1 | 6 225.7 | — | **10 424.9** (1RW) | 23 708.0 | **43 923.0** | −74.4 % | 30 918.9 | −62.8 % |
| `ble-tx-opt` | 870.6 | 3 078.2 | 3 028.9 | — | **37 703.9** | 23 708.0 | **64 490.1** | −62.3 % | 30 896.8 | −62.9 % |
| `ble-tx-pdu` | 635.7 | 2 553.9 | 2 415.5 | — | **10 703.9** (1RW) | **6 979.1** (1RW, 256 × 8) | **20 236.9** | −88.2 % | 20 236.9 | −75.7 % |
| `ble-tx-pdu-we` | 635.7 | 2 564.8 | 2 415.0 | — | **10 703.9** (1RW) | **6 979.1** (1RW, 256 × 8) | **20 247.8** | −88.2 % | 20 247.8 | −75.7 % |
| **`ble-tx-rom`** | 593.2 | 2 509.4 | — | — | — | **6 979.1** (1RW, 256 × 8) | **9 488.5** | **−94.5 %** | 9 488.5 | −88.6 % |
| `ble-tx-cordic` | 2 317.9 | 4 142.2 | — | — | — | **6 979.1** (1RW, 256 × 8) | **11 121.3** | −93.5 % | 11 121.3 | −86.6 % |
| `ble-opt` | 150.0 | 2 362.3 | 2 325.6 | — | 138 700.5 | 23 708.0 | **164 770.8** | −3.8 % | 76 707.0 | −7.8 % |

1. **`ble-tx-rom` is the smallest transmitter: 9 488.5 µm²**, −94.5 % against
   `master` and −53.1 % against `ble-tx-pdu`. Its one macro is the packet
   buffer (6 979.1 µm², 74 % of it). The 10 703.9 µm² of the quarter sine
   table are gone, and the ROM that replaces them, 257 pairs of an eighth of the
   wave, is 593.2 µm²: −42.5 µm² against the logic of the sine-table VCO it
   replaces (635.7 µm², whose memory needed read sequencing and registers).
2. **`ble-tx-cordic` computes the same tables exactly**, with 15 iterations of a
   CORDIC in one clock: its VCO is 2 317.9 µm², 3.9 times the ROM, and its
   transmitter 11 121.3 µm², 1 632.8 µm² above `ble-tx-rom` and still
   −45.0 % against `ble-tx-pdu`. For these tables a ROM is the better fixed
   table: smaller, and off the critical path (§ 5.1).
3. **The audit's corrections add 3 230–3 655 µm² of logic** to the transmitters
   whose Gaussian taps are programmable (`master` 5 322.9 → 8 875.6 µm²) and
   35–150 µm² to those with fixed taps (`ble-tx-pdu` 2 415.5 → 2 553.9). Among
   them is the tail of the Gaussian filter (`btle_gauss_tail`), which weighs the
   taps: the runtime ones on the first, constants with B2 (`FIXED_TAPS`). The
   order of § 4.2 holds but for two pairs that differ by little: `ble-tx-table`
   and `ble-opt` (1.5 µm²), and `ble-tx-pdu-we`, whose strobe now measures
   10.9 µm² more than `ble-tx-pdu` (0.5 µm² less before the audit).
4. **The flow moves identical RTL**: the transmitters of `ble-tx-table` and
   `ble-opt` are the same RTL and measure 2 360.8 and 2 362.3 µm²; that of
   `master` measures 317.8 µm² (3.6 %) less in the netlist of `ble-rx-dm`,
   which has the same transmitter (the runtime FIR's multipliers map
   differently when the other modules read differ; `RX_BRANCH_COMPARISON.md`).
   The conclusions here rest on a macro of 10 703.9 µm² and on 1 632.8 µm² of
   logic, far above that.

## 5. Static timing

`scripts/timing/run_sta.sh` with `STA_SET=controller`: the netlist of the area
flow, flip-flops and RAM macros cut to a register-to-register network, fanout
legalised (maximum 16) and gates sized, ABC `stime`, and the worst liberty
clock-to-Q and setup added. Results in
[`results/timing/all-branches/`](../../results/timing/all-branches/),
[`results/timing/tx-variants/`](../../results/timing/tx-variants/),
[`results/timing/tx-sin8/`](../../results/timing/tx-sin8/),
[`results/timing/tx-opt/`](../../results/timing/tx-opt/),
[`results/timing/tx-1rw/`](../../results/timing/tx-1rw/),
[`results/timing/tx-1--8/`](../../results/timing/tx-1--8/),
[`results/timing/tx-pdu/`](../../results/timing/tx-pdu/) and
[`results/timing/tx-pdu-we/`](../../results/timing/tx-pdu-we/).
Target: the 16 MHz baseband clock, 62.5 ns. The table is of the RTL before the
product audit; `ble-tx-rom` and `ble-tx-cordic`, which exist only after it, are
timed in § 5.1.

| | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` | `ble-opt` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.546 ns | 6.479 ns | 7.115 ns | 6.408 ns | 7.081 ns | 6.251 ns | 6.120 ns | 6.195 ns | 6.243 ns | 6.689 ns | 7.088 ns | 7.146 ns | 4.044 ns |
| Logic path (buffered, sized) | 1.631 ns | 1.546 ns | 1.636 ns | 1.652 ns | 1.517 ns | 1.647 ns | 1.550 ns | 1.614 ns | 1.578 ns | 1.590 ns | 1.558 ns | 1.560 ns | 1.690 ns | 1.597 ns |
| Register overhead | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns | 0.347 ns |
| **Min period** | **1.991 ns** | **1.905 ns** (−4.3 %) | **1.995 ns** (+0.2 %) | **2.011 ns** (+1.0 %) | **1.877 ns** (−5.7 %) | **2.007 ns** (+0.8 %) | **1.910 ns** (−4.1 %) | **1.974 ns** (−0.9 %) | **1.938 ns** (−2.7 %) | **1.949 ns** (−2.1 %) | **1.917 ns** (−3.7 %) | **1.919 ns** (−3.6 %) | **2.050 ns** (+3.0 %) | **1.944 ns** (−2.4 %) |
| Slack at 62.5 ns | +60.509 ns | +60.595 ns | +60.505 ns | +60.489 ns | +60.623 ns | +60.493 ns | +60.590 ns | +60.526 ns | +60.562 ns | +60.551 ns | +60.583 ns | +60.581 ns | +60.450 ns | +60.556 ns |
| Fmax | 502.3 MHz | 524.9 MHz | 501.2 MHz | 497.2 MHz | 532.8 MHz | 498.3 MHz | 523.6 MHz | 506.6 MHz | 516.0 MHz | 513.1 MHz | 521.6 MHz | 521.1 MHz | 487.9 MHz | 514.3 MHz |
| Flip-flops / gates timed | 4 578 / 45 716 | 4 422 / 43 804 | 7 222 / 50 868 | 4 667 / 44 656 | 4 570 / 45 049 | 4 581 / 45 815 | 4 656 / 46 059 | 4 642 / 46 065 | 4 639 / 45 981 | 4 654 / 46 249 | 4 500 / 44 058 | 4 430 / 43 733 | 4 432 / 43 623 | 2 673 / 13 428 |
| Worst path | demodulator multiply, copy 2 | Link Layer `timestamp` | demodulator multiply, copy 2 | demodulator multiply, copy 6 | demodulator multiply, copy 3 | demodulator multiply, copy 6 | Link Layer `timestamp` | demodulator multiply, copy 6 | demodulator multiply, copy 0 | demodulator multiply, copy 3 | demodulator multiply, copy 0 | demodulator multiply, copy 3 | Link Layer `timestamp` | Link Layer `timestamp` |

The worst paths in full:

- demodulator multiply: `btle_phy_i.btle_rx_i.genblk1[k].btle_rx_core_i.gfsk_demodulation_i.i1[5]`
  (`master`) or `…i0[6]` / `…i0[4]` / `…i0[3]` / `…q0[7]` (the transmitter branches) →
  `…signal_for_decision[31]`, in one of the 8 upstream demodulator copies;
- Link Layer `timestamp` (`ble-tx-table`, `ble-tx-sin8`, `ble-tx-pdu-we`, `ble-opt`):
  `btle_ll_i…write_data[16]` → `[76]`, the 64-bit `timestamp` counter.

What can be said, and what cannot:

1. **Every branch closes 16 MHz with a factor of about 30 in hand**
   (1.88–2.05 ns of a 62.5 ns period). None of the changes makes timing a
   constraint.
2. **No change lengthens the critical path.** None of the transmitter branches puts the
   worst path in the transmitter: it stays the multiply of one of the 8
   upstream demodulators or, on `ble-tx-sin8` and `ble-tx-pdu-we`, the Link
   Layer's `timestamp` counter, as on `ble-tx-table`. The read ahead of
   `ble-tx-sin2` puts the
   phase adder and a negation in front of the memory address, and the
   one-port memories have their data 0.29 to 0.32 ns after the falling clock
   edge (`VCO_MEMORY_SWEEP.md` § 3): far inside the clock.
3. **Differences below about 0.15 ns are flow noise, not design effects.** The
   worst path of nine transmitter branches is the same upstream RTL, the
   demodulator multiply, and it times anywhere from 1.877 ns (`ble-tx-fir2`)
   to 2.011 ns (`ble-tx-table-sram`), against 1.991 ns on `master`. Likewise
   the `timestamp` counter of `btle_ll` is the same RTL on `master` and
   `ble-tx-table`, yet it times at 1.546 ns in the `ble-tx-table` netlist,
   where it is the worst path, and at 1.690 ns in the `ble-tx-pdu-we` one
   (2.050 ns with the register overhead; its `btle_ll` adds only the strobe's
   comparator, away from the counter). Buffering and sizing are heuristics over the whole
   netlist, so ranking the branches within 0.15 ns means nothing.
4. The unbuffered column only shows that Yosys builds no buffer trees
   (explained in `STATIC_TIMING.md` on `ble-opt`); it is kept for completeness.

### 5.1 On the audited RTL: the VCO without memory

Run [`tx-vco`](../../results/timing/tx-vco/) times `ble-tx-pdu`, `ble-tx-rom`
and `ble-tx-cordic` against corrected `master` (`5abbbf7`) with the flow above
(`STA_SET=full`; the controllers):

| | corrected `master` (`5abbbf7`) | `ble-tx-pdu` | `ble-tx-rom` | `ble-tx-cordic` |
|---|---:|---:|---:|---:|
| Logic path (buffered, sized) | 3.098 ns | 1.544 ns | 1.642 ns | 5.142 ns |
| Register overhead | 0.359 ns | 0.359 ns | 0.359 ns | 0.359 ns |
| **Min period** | **3.458 ns** | **1.904 ns** | **2.002 ns** | **5.501 ns** |
| Slack at 62.5 ns | +59.042 ns | +60.596 ns | +60.498 ns | +56.999 ns |
| Fmax | 289.2 MHz | 525.3 MHz | 499.6 MHz | 181.8 MHz |
| Worst path | the Gaussian tail of the audited runtime FIR (`tail_i.remaining` → `tail_i.correction`) | the Link Layer's clock crossing (`clk_cross_bus_bb_to_s_axi_i.write_data[16]` → `[76]`) | demodulator multiply, copy 2 | **the CORDIC** (`vco_i.integral_voltage_signal[3]` → `btle_tx_i.i_internal[6]`) |

- **The ROM is not on the critical path**: the worst path of `ble-tx-rom` is a
  demodulator multiply, as on most branches, and its period is within the
  flow's noise of `ble-tx-pdu`'s (the same `btle_rx` RTL times at
  1.512–1.616 ns across the three runs).
- **The CORDIC is the first change that puts the worst path in the
  transmitter**: its 15 add-and-shift stages, from the phase register to the
  output register in one clock, take 5.142 ns of logic, a minimum period of
  5.501 ns (181.8 MHz), still 11 times the 16 MHz clock.
- The worst path of corrected `master` is the Gaussian tail that the audit
  added (`btle_gauss_tail` in `gfsk_modulation.v`, 3.098 ns of logic), which weighs
  the runtime taps; with B2 its taps are constants (`FIXED_TAPS`), and it is not
  the worst path.

## 6. Switching activity

### 6.1 Method

`scripts/power/run_activity.sh`, the harness of `SWITCHING_ACTIVITY.md` on
`ble-opt`, once per branch. Results in
[`results/power/all-branches/`](../../results/power/all-branches/),
[`results/power/tx-variants/`](../../results/power/tx-variants/),
[`results/power/tx-sin8/`](../../results/power/tx-sin8/),
[`results/power/tx-opt/`](../../results/power/tx-opt/),
[`results/power/tx-1rw/`](../../results/power/tx-1rw/),
[`results/power/tx-1--8/`](../../results/power/tx-1--8/),
[`results/power/tx-pdu/`](../../results/power/tx-pdu/) and
[`results/power/tx-pdu-we/`](../../results/power/tx-pdu-we/).

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
  one set. Runs `tx-variants`, `tx-sin8`, `tx-opt`, `tx-1rw`, `tx-1--8`,
  `tx-pdu` and `tx-pdu-we` reused that set (the same `vectors.sha256`), and so
  did run `sram-energy` (§ 6.6).
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
[`tx-variants/summary.md`](../../results/compare/tx-variants/summary.md),
[`tx-sin8/summary.md`](../../results/compare/tx-sin8/summary.md),
[`tx-opt/summary.md`](../../results/compare/tx-opt/summary.md),
[`tx-1rw/summary.md`](../../results/compare/tx-1rw/summary.md),
[`tx-1--8/summary.md`](../../results/compare/tx-1--8/summary.md),
[`tx-pdu/summary.md`](../../results/compare/tx-pdu/summary.md) and
[`tx-pdu-we/summary.md`](../../results/compare/tx-pdu-we/summary.md)). The
scenarios that do not use the packet vectors (`tx`, `idle`, `idle0`) also
reproduce the earlier `ble-opt` run `sticker-vs-upstream` exactly, every count
of every block, upstream and reduced alike; `rx` and `mixed` cannot, because
that run's vectors were not kept.

### 6.2 Data + clock switched capacitance, every scenario

| Scenario | `master` / `risc-v-ble` | `ble-tx-table` (B2) | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` | `ble-opt` (B1 B2 A1 A2) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `rx` | 1.23 × 10⁹ fF | −2.4 % | +40.8 % | +1.4 % | −0.1 % | 0 | +1.2 % | +1.0 % | +0.9 % | +1.2 % | −1.2 % | −2.3 % | −2.2 % | **−33.2 %** |
| `tx` | 1.00 × 10⁹ fF | −5.0 % | — | — | −1.1 % | +0.4 % | +1.8 % | +1.9 % | +3.4 % | +2.3 % | −3.1 % | −2.6 % | −2.6 % | **−34.7 %** |
| `mixed` | 1.25 × 10⁹ fF | −3.2 % | +40.8 % | +0.6 % | −0.5 % | +0.1 % | +1.3 % | +1.3 % | +1.8 % | +1.5 % | −1.8 % | −2.2 % | −2.1 % | **−30.3 %** |
| `idle` | 1.26 × 10⁹ fF | −2.3 % | +39.9 % | +1.4 % | −0.1 % | 0 | +1.2 % | +1.0 % | +0.9 % | +1.2 % | −1.1 % | −2.2 % | −2.2 % | **−25.5 %** |
| `idle0` | 0.95 × 10⁹ fF | −3.1 % | +53.0 % | +1.8 % | −0.1 % | 0 | +1.5 % | +1.3 % | +1.2 % | +1.5 % | −1.5 % | −3.0 % | −2.9 % | **−34.4 %** |

### 6.3 The measures of `SWITCHING_ACTIVITY.md`, scenario `mixed`, every branch

| Measure | `master` / `risc-v-ble` | `ble-tx-table` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` | `ble-opt` |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Toggles / cycle, non-clock nets | 984.3 | 956.4 (−2.8 %) | 988.0 (+0.4 %) | 958.7 (−2.6 %) | 971.0 (−1.4 %) | 987.0 (+0.3 %) | 989.4 (+0.5 %) | 994.3 (+1.0 %) | 1012.1 (+2.8 %) | 996.0 (+1.2 %) | 962.7 (−2.2 %) | 985.4 (+0.1 %) | 983.6 (−0.1 %) | 939.7 (−4.5 %) |
| Nets with activity > 10 % | 839 | 827 | 836 | 824 | 841 | 851 | 845 | 882 | 951 | 887 | 837 | 954 | 951 | 3 908 (×4.7) |
| `btle_rx` toggles / cycle | 791.1 | 790.6 | 788.2 | 788.9 | 791.4 | 788.8 | 791.0 | 791.5 | 792.1 | 790.9 | 791.5 | 791.5 | 791.1 | 808.8 (+2.2 %) |
| `btle_ll` toggles / cycle | 41.5 | 40.6 | 41.6 | 41.9 | 42.7 | 41.1 | 42.2 | 41.7 | 41.5 | 41.5 | 41.5 | 41.9 | 41.1 | 11.0 (**−73.4 %**) |
| Gaussian filter toggles / cycle | 39.1 | 12.6 (**−67.8 %**) | 45.6 (+16.4 %) | 15.4 (**−60.8 %**) | 24.2 (**−38.1 %**) | 39.1 | 39.1 | 39.1 | 39.1 | 39.1 | 12.3 (**−68.6 %**) | 10.7 (**−72.6 %**) | 11.2 (−71.5 %) | 12.3 (**−68.6 %**) |
| Rest of `btle_tx` (VCO, packet path) toggles / cycle | 37.4 | 37.4 | 37.4 | 37.4 | 37.4 | 42.8 (+14.4 %) | 42.0 (+12.1 %) | 46.8 (+24.9 %) | 64.3 (+71.9 %) | 49.2 (+31.5 %) | 42.3 (+12.9 %) | 66.1 (+76.5 %) | 65.0 (+73.7 %) | 37.7 |
| Clock network (CK-pin load × toggles) | 8.76 × 10⁸ | −3.4 % | **+57.3 %** | +1.9 % | −0.2 % | +0.1 % | +1.7 % | +1.4 % | +1.3 % | +1.6 % | −1.7 % | −3.2 % | −3.2 % | **−41.4 %** |
| Memory: toggles on RAM ports | 3 044 741 | unchanged | unchanged | +10.8 % | unchanged | −0.4 % | −0.4 % | −0.4 % | +7.0 % | −0.5 % | −0.4 % | +7.2 % | +7.1 % | **−40.0 %** |
| Data load × toggles | 3.73 × 10⁸ | −2.8 % | +1.8 % | −2.5 % | −1.2 % | +0.2 % | +0.4 % | +1.0 % | +2.9 % | +1.2 % | −2.1 % | +0.1 % | +0.3 % | −4.3 % |
| **Data + clock proxy** | 1.25 × 10⁹ | **−3.2 %** | **+40.8 %** | **+0.6 %** | **−0.5 %** | **+0.1 %** | **+1.3 %** | **+1.3 %** | **+1.8 %** | **+1.5 %** | **−1.8 %** | **−2.2 %** | **−2.1 %** | **−30.3 %** |

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
(−16.6 %, `RX_BRANCH_COMPARISON.md`); every other block stays within 1 %. The transmitter branches
behave the same way: only their own block moves the proxy by more than 0.1
point, the Gaussian filter on `ble-tx-table-reg` (+40 to +53 points),
`ble-tx-table-sram` (+0.6 to +1.8) and `ble-tx-fir2` (−0.1 to −1.1), and the
rest of `btle_tx`, which holds the VCO, on `ble-tx-sin4` (at most +0.4),
`ble-tx-sin8` (+1.2 to +1.9), `ble-tx-sin8-1rw` (+1.0 to +1.9), `ble-tx-sin2`
(+0.9 to +3.4) and `ble-tx-1--8` (+1.2 to +2.3). On `ble-tx-opt` both move,
and they add up:

| Scenario | B2 (`ble-tx-table`) | {cos, sin} memory (`ble-tx-sin8`) | Sum | `ble-tx-opt` | Residual |
|---|---:|---:|---:|---:|---:|
| `rx` | −2.4 | +1.2 | −1.3 | −1.2 | +0.1 |
| `tx` | −5.0 | +1.8 | −3.2 | −3.1 | +0.1 |
| `mixed` | −3.2 | +1.3 | −1.9 | −1.8 | +0.1 |
| `idle` | −2.3 | +1.2 | −1.2 | −1.1 | 0.0 |
| `idle0` | −3.1 | +1.5 | −1.6 | −1.5 | +0.1 |

On `ble-tx-pdu` both move as well: the Gaussian filter −2.4 to −5.2 points, as
with B2, and the rest of `btle_tx` +0.1 to +2.5 points, close to `ble-tx-sin2`.
Its packet buffer and its rewritten counters exist on no other branch, so the
sum cannot be checked for it. `ble-tx-pdu-we` moves as `ble-tx-pdu`, within
0.1 point in every scenario (−2.1 to −2.9 %).

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
  4.9 µW against 17.7 µW for 2 048 × 8, a model figure, not a measurement;
  § 6.6 measures the leakage of the one-port macros.
- **One {cos, sin} memory (`ble-tx-sin8`).** Its write port adds 75
  flip-flops clocked on every cycle (the previous register pairs and the
  queues), so the clock-pin load rises 1.7 % in every scenario and the proxy
  1.2 to 1.8 %. The rest of the transmitter switches as on `ble-tx-sin4`
  (68.0 → 77.1 toggles per cycle in `tx`), and so do the RAM ports. In
  OpenRAM's model the one 512 × 16 dual-port macro leaks 9.0 µW, against
  2 × 4.9 µW for the two 512 × 8 of `ble-tx-sin4`.
- **One port for the {cos, sin} memory (`ble-tx-sin8-1rw`).** The queues of
  the write port give way to a 16-bit held entry, 14 flip-flops fewer than
  `ble-tx-sin8`, so the clock-pin load rises 1.4 % instead of 1.7 %. While
  transmitting the rest of the transmitter switches somewhat more (68.0 →
  86.7 toggles per cycle in `tx`, against 77.1), and the proxy rises 1.0 to
  1.9 %, as on `ble-tx-sin8`. OpenRAM's analytical model puts the leakage of
  the one-port macro at 8.6 µW (`VCO_MEMORY_SWEEP.md` § 2.2); the energy of its
  accesses is not measured (§ 6.6 says why that model cannot give it).
- **The sine table alone (`ble-tx-sin2`).** Two reads per sample make the
  memory's read address alternate between entries b and a on every clock while
  transmitting: the RAM-port toggles rise 15.7 % in `tx` (7.0 % in `mixed`) and
  the rest of the transmitter switches 80 % more (68.0 → 122.2 toggles per
  cycle), so the proxy rises 3.4 % in `tx`. Without traffic only the VCO's
  flip-flops count, and the proxy rises 0.9 to 1.2 % (clock pins +1.3 %). The
  proxy does not see the memory, which is read on every clock while
  transmitting: OpenRAM's analytical model puts the leakage of the 512 × 8
  one-port macro at 4.5 µW, and § 6.6 measures its energy on `ble-tx-pdu` and
  `ble-tx-pdu-we`, which have the same memory (1.07 pJ per read).
- **An eighth of the tables (`ble-tx-1--8`).** One read per sample, as on
  `ble-tx-sin8-1rw`: the read address moves once per sample, and the RAM-port
  toggles fall 1.2 % in `tx`, where those of `ble-tx-sin2` rise 15.7 %. Its 91
  VCO flip-flops put the clock-pin load 1.6 % up, and while transmitting the
  rest of the transmitter switches 68.0 → 91.8 toggles per cycle (the second
  reflection and the swap past 45°): the proxy rises 1.2 to 2.3 %, between
  `ble-tx-sin8-1rw` and `ble-tx-sin2`. OpenRAM's analytical model puts the
  leakage of the 256 × 16 macro at 4.5 µW; the energy of its accesses is not
  measured (§ 6.6).
- **The best transmitter together (`ble-tx-opt`).** The Gaussian table saves
  more activity than the write port of the {cos, sin} memory costs: the proxy
  falls 1.1 to 3.1 %, most while transmitting (−15.1 % of all non-clock
  toggles in `tx`), and the clock-pin load falls 1.7 % (−156 flip-flops of the
  filter, +78 of the write port).
- **The packet buffer with one port too (`ble-tx-pdu`).** It has 148
  flip-flops fewer than upstream (−156 in the filter, −44 in the three
  rewritten blocks, +48 in the VCO, +4 in the rest of `btle_tx`), so the
  clock-pin load falls 3.2 % in every scenario and the proxy 2.2 to 3.0 %.
  While transmitting, the filter switches as with B2 (79.1 → 21.7 toggles
  per cycle) and the rest of the transmitter 85 % more (68.0 → 125.7), as on
  `ble-tx-sin2` (122.2), whose two reads per sample it keeps; the RAM-port
  toggles rise 16.0 % in `tx` (7.2 % in `mixed`). The proxy does not see the
  memories: its packet buffer is still written on every AXI clock, and § 6.6
  measures what that costs.
- **The packet buffer written when its pair is new (`ble-tx-pdu-we`).** Two
  flip-flops more than `ble-tx-pdu` put the clock-pin load at −3.17 % instead
  of −3.21 %, and the proxy moves as on `ble-tx-pdu` (−2.1 to −2.9 %); the
  RAM-port toggles fall by 1 315 in `tx`, since the buffer's port now moves
  only for a new pair. Its point is the energy of the SRAMs, which the proxy
  does not see (§ 6.6).
- **B1, shared demodulator** (in `ble-opt`): what it does to activity on its
  own, on `ble-rx-dm`, is in [RX_BRANCH_COMPARISON.md](RX_BRANCH_COMPARISON.md)
  (−5.9 to −12.9 % of the proxy, from the clock pins of its 652 flip-flops
  fewer).
- **A1 + A2, debug infrastructure.** They give the largest activity saving
  (−17 to −23 points), although they are only 15 % of the cells saved. The
  full Link Layer holds 44 % of the upstream flip-flops (2 036 of 4 578), all
  clocked on every cycle, and makes 32 % of the upstream proxy; the minimal one
  switches 73 % less. The IQ-capture RAM, written on every 16 MHz cycle, is
  gone (RAM-port toggles −25 to −48 %, depending on the scenario).

The ranking by activity (A1 + A2, then B1, then B2) is not the ranking by area
(B1, then A1 + A2, then B2): cells that are clocked on every cycle cost switching
whatever the traffic, and the debug infrastructure is exactly that.

### 6.6 The energy of the transmitter's SRAMs

The proxy of §§ 6.2–6.5 leaves the SRAMs out, and OpenRAM's analytical `.lib`
cannot price them: its clock power is one estimate of the whole array, every
gate at 100 MHz, the same for a read, a write and an idle clock
(`VCO_MEMORY_SWEEP.md` § 2.2). Four runs made on `ble-tx-pdu-we` measure them.
Unlike the rest of § 6, the accesses are counted on the audited RTL of
`ble-tx-pdu` and `ble-tx-pdu-we`, against corrected master `5abbbf7`
(`PRODUCT_VALIDATION.md`, `RF_INTERFACE_REVIEW.md`).

- **The macros** (run [`sram-char`](../../results/power/sram-char/summary.md),
  `scripts/power/run_sram_char.sh`): OpenRAM's own characterizer, with
  ngspice, on the whole netlist of each macro (FreePDK45, TT, 1.0 V, 25 °C, a
  5 ns cycle). An access is priced against a deselected clock of the same
  port; a deselected clock costs energy too (0.323 and 0.372 pJ), since the
  macro gates its array with the chip select but not its clock buffers and
  input flip-flops. OpenRAM's default netlist, trimmed to the outer bitcells,
  gives access energies 17 to 35 % lower (run `sram-char-trimmed`), and Xyce,
  the other simulator in OpenRAM's environment, does not give usable figures
  (run `sram-char-xyce`).
- **The leakage** (run [`sram-leakage`](../../results/power/sram-leakage/summary.md),
  `scripts/power/run_sram_leakage.sh`): OpenRAM's figure is the supply power
  5–10 ns after a power-up from 0 V, when the bitlines and the sense
  amplifiers' inputs, which nothing drives in a deselected macro, still sit
  between the rails (115.1 µW on the 256 × 8 macro). Run for 5 µs with every
  cell at 0, the same measure settles at 15.0 µW (25.1 on the 512 × 8 macro), its
  last three windows, 3–5 µs, within 0.1 %.
- **The accesses** (run [`sram-energy`](../../results/power/sram-energy/summary.md),
  `scripts/power/run_sram_energy.sh`): the five workloads of § 6.1, with the
  same setup and vectors, 100 000 clocks of the 16 MHz `bb_clk`, which is the
  AXI clock here too, the setup subtracted; at RTL, the corrected `master` and
  each branch side by side, every output compared on every clock, every RAM
  model replaced by one that counts its accesses.

| Macro | Memory | Write (pJ) | Read (pJ) | Deselected clock (pJ) | Leakage (µW) | OpenRAM's figure (µW) |
|---|---|---:|---:|---:|---:|---:|
| `sram_1rw1r_8x2048` | COS and SIN tables of `master` | — | — | — | — | — |
| `sram_1rw1r_8x512` | packet buffer of `master` | — | — | — | — | 126.7 |
| `sram_1rw_8x512` | quarter sine table of `ble-tx-pdu` and `ble-tx-pdu-we` | 1.161 | 1.068 | 0.372 | 25.1 | 130.3 |
| `sram_1rw_8x256` | packet buffer of `ble-tx-pdu` and `ble-tx-pdu-we` | 0.889 | 0.821 | 0.323 | 15.0 | 115.1 |

| Configuration | `rx` | `tx` | `mixed` | `idle` | `idle0` | of which clocks | Leakage |
|---|---:|---:|---:|---:|---:|---:|---:|
| `master` | — | — | — | — | — | — | — |
| `ble-tx-pdu` | 42.43 | 42.42 | 42.42 | 42.43 | 42.43 | 11.12 | 40.1 |
| `ble-tx-pdu-we` | 28.20 | 28.37 | 28.28 | 28.20 | 28.20 | 11.12 | 40.1 |

— : a memory of that configuration is not characterized. Every scenario,
every memory and its counts: [`sram-energy/summary.md`](../../results/power/sram-energy/summary.md).

- **`master` is not priced, but its accesses are counted**: upstream writes
  and reads each of its three memories on every clock, in every scenario. Its
  2 048 × 8 two-port tables are too large for the ngspice of OpenRAM's
  environment (revision 26), whose leakage run of that netlist alone ran for
  hours, and the measurement run of its 512 × 8 two-port buffer did not end in
  6 h.
- **`ble-tx-pdu` accesses both memories on every clock**: 42.4 µW of
  dynamic power in every scenario, 14.2 µW to write the packet buffer on every
  AXI clock, 17.1 µW to read the quarter sine table on every clock and
  11.1 µW for the clocks of the two macros.
- **The strobe removes the buffer's writes** (`ble-tx-pdu-we`): none in
  `idle`, `idle0` and `rx`, 612 in `tx` (34 per packet written) against 99 405.
  The transmitter's SRAMs drop to 28.20–28.37 µW, **−34 %**. The
  saving, 14.2 µW at this 16 MHz AXI clock, grows with it: `ble-tx-pdu`
  writes its buffer on every AXI clock (88.9 µW at 100 MHz), `ble-tx-pdu-we`
  once per packet byte.
- **What is left is the clocks and the sine table's reads** (11.1 and
  17.1 µW), also when the phase does not move: a read only when it moves
  would remove most of the reads without traffic. It is not built.
- **The leakage is of the same order**: 15.0 and 25.1 µW for the two one-port
  macros with every cell at 0, 40.1 µW in all on both branches, about the
  dynamic power of `ble-tx-pdu`. FreePDK45's devices come from a predictive
  model and leak far more than those of a low-power process; the dynamic power
  is the part the RTL decides.
- **At rest, the buffer's static power depends on its content** (run
  [`sram-idle`](../../results/power/sram-idle/summary.md), `scripts/power/run_sram_idle.sh`):
  deselected, with the words the RTL leaves in it, the 256 × 8 buffer of
  `ble-tx-pdu-we` takes 15.0–15.7 µW when the words never written hold 0 and
  25.3–35.6 µW when they hold random data, as after a power-up: 10.3 to
  19.8 µW more, as much as the strobe saves, from the crossover current of
  the sense amplifiers whose floating column holds mixed data. `ble-tx-pdu`
  writes its buffer on every AXI clock and is not concerned. Writing the whole
  buffer once after reset would keep the saving; it is not built.
- **`ble-tx-rom` and `ble-tx-cordic` have no VCO memory**: their one SRAM is the
  packet buffer of `ble-tx-pdu`, with the same `btle_tx.v` and so the same
  accesses: 19.40 µW of dynamic power and 15.0 µW of leakage. The 23.03 µW of the
  sine table's reads and clocks, and its 25.1 µW of leakage, are gone. The logic
  that replaces the table switches too; § 6.6 does not price logic, and the
  activity flow of §§ 6.1–6.5 has not been run again on the audited RTL, whose
  coverage the product audit lists as open (`RF_INTERFACE_REVIEW.md`).

## 7. Evidence per branch

Every branch that changes the RTL has its own proof that nothing needed was
lost, plus the gate-level lockstep of these runs (§ 6.1), in which every output
of the synthesised netlist is compared with upstream on every clock.

| | `ble-tx-table` (B2) | `ble-opt` (B1 B2 A1 A2) |
|---|---|---|
| Formal proof of the change | table ≡ upstream FIR, **unbounded** (k-induction), 3/3 mutants rejected | both proofs (B1, B2) |
| Defaults ≡ original (formal, per module) | 5 modules against `upstream-baseline` (96 609 `$equiv` cells for the controller) | 7 modules against `88f2250` |
| Lockstep against upstream | controller through the registers, `GAUSS_TABLE=1`: 15/15, 923 385 clocks, **every output and register**, 4/4 mutants | controller through the registers: 15/15, 923 385 clocks (removed outputs skipped), 3/3 mutants |
| Upstream testbenches, 270 runs | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) |
| Gate-level lockstep, run `all-branches` | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches |
| Report | `docs/Validation/TX_TABLE_VALIDATION.md` | `SHARED_DEMOD_VALIDATION.md`, `STICKER_REDUCTIONS_VALIDATION.md` |

| | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` | `ble-tx-sin8` | `ble-tx-sin8-1rw` | `ble-tx-sin2` | `ble-tx-1--8` | `ble-tx-opt` | `ble-tx-pdu` | `ble-tx-pdu-we` |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Formal | defaults ≡ upstream: `gauss_filter`, `gfsk_modulation`, `btle_tx` | the same | pair identity at 16 bits; whole filter ≡ upstream for any taps and any input, unbounded, at 4 bits; 3/3 mutants | — | — | — | — | — | B2 ≡ upstream FIR, **unbounded** (the `gauss_filter.v` of `ble-tx-table`); VCO: — (as `ble-tx-sin8`) | B2 in its paired form ≡ upstream FIR, **unbounded**, 3/3 mutants; defaults ≡ upstream: `gauss_filter` (`TX_PDU_VALIDATION.md`) | as `ble-tx-pdu` (the same `gauss_filter.v`): B2 in its paired form ≡ upstream FIR, **unbounded**, 3/3 mutants; defaults ≡ upstream: `gauss_filter` (`TX_PDU_WE_VALIDATION.md`) |
| Random lockstep, module level | 4 seeds × 200 random tap sets × 5 000 clocks; 2/2 mutants | the same; 4/4 mutants | 4 seeds × 2 000 000 clocks, 1 001 125 random tap writes | `vco` against the `master` VCO, both full tables loaded: all 2 048 phase addresses, phase jumps, gaps, a reset; 3 072 clocks, no mismatch (`tests/test_vco_sin4.py`) | `vco` against the `ble-tx-sin4` VCO: 4 seeds × 1 000 000 clocks of random writes to both tables (same and different addresses in one clock, streams, resets), reads aimed at the entries just written, 2 919 121 comparisons, no mismatch; 7/7 mutants. And the sweep of `test_vco_sin4.py` against `master` (`tests/test_vco_sin8.py`) | `vco` against the `ble-tx-sin4` VCO: 4 seeds × 1 000 000 clocks of random writes to both tables against samples on random clocks, every other clock or none; 2 370 274 comparisons, no mismatch; the same VCO on a one-port macro model identical on every clock; 11/11 mutants. And the sweep against `master` (`tests/test_vco_sin8_1rw.py`) | `vco` against the `ble-tx-sin4` VCO, each sine write mirrored into its cosine table: 4 seeds × 1 000 000 clocks, 1 324 264 samples on random clocks, every other clock or none; 2 629 325 comparisons, no mismatch; the one-port macro model identical on every clock; 11/11 mutants. And a sweep against `master` with the full tables (`tests/test_vco_sin2.py`) | `vco` against the `ble-tx-sin4` VCO, kept equal to what this branch stores (each write mirrored, cos[k] = sin[512 − k]): 4 seeds × 1 000 000 clocks of random writes to both tables against samples on random clocks, every other clock or none; 2 263 689 comparisons, no mismatch; the one-port macro model identical on every clock; 14/14 mutants. And the sweep against `master` (`tests/test_vco_1--8.py`) | the VCO: `tests/test_vco_sin8.py` on this branch, the result of `ble-tx-sin8` (the same `vco.v`) | `btle_tx` against upstream's `btle_tx`, every output on every clock: 3 seeds × 6 AXI clocks (`clk`, 8 to 100 MHz) × 2 memory models (the RAM model, one-port macros), 36/36 runs, 2 776 037 clocks per model, 116 packets (255 and 0 bytes included), 82 resets; 11/11 mutants (`tests/test_tx_pdu.py`). The VCO as on `ble-tx-sin2`: 2 629 325 comparisons, 11/11 mutants (`tests/test_vco_sin2.py`) | `btle_tx` against upstream's `btle_tx`, every output on every clock, with the write strobe off and on: 3 seeds × 6 AXI clocks × 2 memory models × 2 strobe settings, 72/72 runs, 2 344 632 clocks per configuration, 116 packets, 82 resets, the bytes of the next packet written while one is sent (1 656 new pairs in a clock that reads); with the strobe, 59 563 memory writes for 59 563 new pairs, 1 169 498 without; 13/13 mutants (`tests/test_tx_pdu.py`). The VCO as on `ble-tx-pdu`: 2 629 325 comparisons, 11/11 mutants (`tests/test_vco_sin2.py`) |
| Controller through the registers | 15/15 runs, 90 random tap sets reprogrammed in flight, 930 629 clocks, every output and register; 4/4 mutants | 15/15 runs, 927 488 clocks; 6/6 mutants | — | — | — | — | — | — | 15/15 runs, 923 385 clocks, `GAUSS_TABLE=1`, every output and register; 4/4 mutants | 15/15 runs, 923 385 clocks, `GAUSS_TABLE=1`, every output and register; 5/5 mutants, one in the packet buffer | 15/15 runs, 922 759 clocks, `GAUSS_TABLE=1 PDU_WRITE_STROBE=1`, every output and register, 40 baremetal windows before `tx_start`; 8/8 mutants, three of them in the write strobe |
| Upstream testbenches, 270 runs | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit) | 118 PASS; **FAIL overall** (integrity audit); every verdict equal to `master`'s, 0 DIFFERENT, also on one-port macro models | 118 PASS; **FAIL overall** (integrity audit); every verdict equal to `master`'s, 0 DIFFERENT, also on one-port macro models (the controller testbench runs in baremetal mode, where the strobe is held at 1) |
| Gate-level lockstep, runs `tx-variants`, `tx-sin8`, `tx-opt`, `tx-1rw`, `tx-1--8`, `tx-pdu` and `tx-pdu-we` | 4/5 scenarios, 0 mismatches; `tx` transmits before the 928-clock rebuild (§ 6.1) | the same | 5/5 scenarios, 0 mismatches | 5/5 scenarios, 0 mismatches, with the full 2 048-entry tables written through the registers (25 packets sent) | 5/5 scenarios, 0 mismatches, with the full tables written through the registers (25 packets sent) | 5/5 scenarios, 0 mismatches (run `tx-1rw`), tables written through the registers | 5/5 scenarios, 0 mismatches (run `tx-1rw`), tables written through the registers | 5/5 scenarios, 0 mismatches (run `tx-1--8`), tables written through the registers | 5/5 scenarios, 0 mismatches (run `tx-opt`), tables written through the registers | 5/5 scenarios, 0 mismatches (run `tx-pdu`), tables and packets written through the registers | 5/5 scenarios, 0 mismatches (run `tx-pdu-we`), tables and packets written through the registers |
| Report | `GAUSS_FILTER_OPTIONS.md` § 7 | `GAUSS_FILTER_OPTIONS.md` § 7 | `GAUSS_FILTER_OPTIONS.md` § 7 | `TX_SIN4_COMPARISON.md` (on `ble-tx-sin4`) | `TX_SIN8_COMPARISON.md` (on `ble-tx-sin8`) | `TX_SIN8_1RW_COMPARISON.md` (on `ble-tx-sin8-1rw`) | `TX_SIN2_COMPARISON.md` (on `ble-tx-sin2`) | `TX_1--8_COMPARISON.md` (on `ble-tx-1--8`) | `docs/Validation/TX_OPT_VALIDATION.md` (on `ble-tx-opt`) | `docs/Validation/TX_PDU_VALIDATION.md` (on `ble-tx-pdu`) | `docs/Validation/TX_PDU_WE_VALIDATION.md` (on `ble-tx-pdu-we`) |

The rows "Upstream testbenches, 270 runs" above are the strict runner of the
integrity audit on the RTL before the product audit. The product audit then
corrected the RTL of every branch and replaced that runner with its own 270-case
matrix (210 data comparisons and 60 verified rejections), which every branch passes,
270/270, and 270/270 again on a one-port model where the branch has one-port memories
(`PRODUCT_VALIDATION.md`, `RF_INTERFACE_REVIEW.md`); after the lint closure of
2026-10-06 all 18 branches pass it again, and pass the lint gate (`LINT_CLOSURE.md`).

`ble-tx-rom` and `ble-tx-cordic` were validated on the audited RTL, with the
product audit's campaign against corrected `master` (`5abbbf7`), not with the
strict runner of the integrity audit like the branches above:

| | `ble-tx-rom` | `ble-tx-cordic` |
|---|---|---|
| VCO, module level | `vco` against the `master` VCO, its tables written with the project's values as the upstream testbench writes them, every output on every clock: a sweep of every phase (+1, −1 and a stride of 7) and 4 × 1 000 002 random clocks (samples on random clocks, resets, table writes), 3 991 804 comparisons, no mismatch; 7/7 mutants (`tests/test_vco_fixed.py`) | the same; 11/11 mutants, five of them in the CORDIC |
| Transmitter, module level | `btle_tx` against corrected `master`'s, every output on every clock: 2 seeds × 6 AXI clocks × 2 memory models, 24/24 runs, 2 241 980 clocks, 102 packets; 11/11 mutants (`tests/test_tx_pdu.py`) | the same |
| The product audit's matrix, 270 cases | 270/270 (210 data comparisons, 60 verified rejections), and 270/270 on the one-port model of the packet buffer | the same |
| TX waveforms | 167/167, every PDU decoded by the RTL receiver; 16/16 on the one-port model | the same |
| RF contract, controller, defects | 12/12, 2/2 mutants; controller lockstep 6/6 runs (36 TX, 36 RX), 5/5 mutations; 4/4 product defects | the same |
| Structure, at the revision validated (`144d51b`, `3d9ad94`) | Yosys passes; strict lint fails, as it then did on every branch: 156 diagnostics (+3 against `ble-tx-pdu`: the table writes it ignores) | 159 (+6: the table writes, and bits the CORDIC computes but does not use) |
| Lint closure, 2026-10-06 | lint passes (2 configurations), with the reviewed exceptions; the 270-case matrix 270/270 on the RTL and on the one-port model; 7/7 ROM mutants (`LINT_CLOSURE.md`) | lint passes (2 configurations); the same matrices; 11/11 CORDIC mutants |
| Report | `docs/Validation/TX_ROM_VALIDATION.md` (on `ble-tx-rom`) | `docs/Validation/TX_CORDIC_VALIDATION.md` (on `ble-tx-cordic`) |

## 8. What each branch gives up

| Branch | Functions removed |
|---|---|
| `master`, `risc-v-ble` | none (the reference) |
| `ble-tx-fir2` | **none**: an exact rewrite; the taps stay programmable through register 1 and apply on the next clock |
| `ble-tx-table-reg`, `ble-tx-table-sram` | none, but after a tap write the tables need 928 clocks (58 µs) to be rebuilt before the next transmission |
| `ble-tx-sin4` | the independent programming of the whole COS/SIN tables: only addresses 0–511 of each are stored and the rest follows by quarter-wave symmetry, so a table without that symmetry can no longer be loaded (the project's tables have it, § 6.1) |
| `ble-tx-sin8` | the same as `ble-tx-sin4`, and the two tables share one write port: their writes must not back up by more than one, at most w + 1 table writes in any w consecutive clocks (two writes to the same address in one clock count as one), where upstream accepts two per clock. Within that, the outputs differ only if the VCO reads an entry in the clock after its write had to wait, which means rewriting both tables while transmitting. Through the registers one table entry is written per register write, at most one every three AXI clocks (the repository's firmware writes none itself) |
| `ble-tx-sin8-1rw` | the same as `ble-tx-sin4`, and the tables share one port with the VCO's reads: a table write waits for a clock without a read (one clock in two while transmitting, every clock when idle; two writes to the same address in one clock count as one), and a table's pair must not change again before it is written (at most four clocks, when both tables change at once while transmitting). Within that, the outputs are upstream's on every clock. Through the registers one table entry is written per register write (the repository's firmware writes none itself) |
| `ble-tx-sin2` | the same as `ble-tx-sin4`, and the cosine table: only cos[0] is stored, every other entry is cos[k] = sin[512 − k], so a cosine table not of that form can no longer be loaded (the project's tables are). Sine writes wait for a clock without a read, none while transmitting, and the sine pair must not change again before it is written. The VCO takes at most one sample every two clocks and none in the clock after a reset, which is what the transmitter gives |
| `ble-tx-1--8` | the same as `ble-tx-sin4`, and the cosine and sine tables are tied: cos[k] and sin[512 − k] are one stored value (k = 1..511), so a pair of tables not of that form can no longer be loaded (the project's tables are). Both tables are still written, each write setting its mirror entry too. Table writes as on `ble-tx-sin8-1rw`: a clock without a read (one in two while transmitting, every clock when idle), a pair held until it is written; and two writes to one stored entry, in the same clock or one waiting while the other is written, must carry the same value |
| `ble-tx-table` | the runtime change of the Gaussian taps (register 1): the taps become a synthesis parameter |
| `ble-tx-opt` | what `ble-tx-table` and `ble-tx-sin8` give up, and nothing else: the runtime Gaussian taps; COS/SIN tables without quarter-wave symmetry; table writes faster than w + 1 in any w clocks. The receiver, the Link Layer and the IQ-capture debug memory are upstream's |
| `ble-tx-pdu` | what `ble-tx-table` and `ble-tx-sin2` give up: the runtime Gaussian taps; COS/SIN tables with quarter-wave symmetry and cos[k] = sin[512 − k]; sine writes that wait while transmitting; one sample every two clocks. And the packet: it must be written before `tx_start`, as the upstream testbenches do (the repository's firmware does not transmit); a byte rewritten while it is being read (in the 12 clocks between its request and its use) may differ from upstream's; while a packet is sent, a pair must stay two AXI clocks (register 8 keeps one at least three); and the AXI clock must run at 8 MHz or faster. The receiver, the Link Layer and the IQ-capture debug memory are upstream's |
| `ble-tx-pdu-we` | what `ble-tx-pdu` gives up, and nothing more. In baremetal mode the buffer is written on every clock, as on `ble-tx-pdu`: the saving of § 6.6 is in Link Layer mode, the path the boards use |
| `ble-tx-rom`, `ble-tx-cordic` | what `ble-tx-pdu` gives up for the Gaussian taps and the packet, and the COS/SIN tables altogether: they are fixed to the project's (`python/btlelib.py`), and the table writes are ignored. The conditions of `ble-tx-pdu`'s sine memory go with it: the VCO takes a sample on any clock. The receiver, the Link Layer and the IQ-capture debug memory are upstream's |
| `ble-opt` | the runtime Gaussian taps; the IQ capture (`btle_ll -q`); the UART HCI; the 1 PPS input; the latency statistic of `btle_ll.c`; removed registers read 0 |

## 9. Conclusions

1. **In `ble-opt`, B1 is the change that matters for logic** (79 % of all the
   cells it saves; `RX_BRANCH_COMPARISON.md`). B2, the transmitter's share, is
   a small exact gain (−4.1 %) that costs the runtime-programmable taps.
2. **For the transmitter, memory matters more than any logic change.** With
   its SRAM macros counted, the COS/SIN tables and the packet buffer are 97 %
   of the transmitter. `ble-tx-sin4` halves it (−54.4 %, 91 180 µm²) for
   104.8 µm² of logic, 30 times what B2 saves there; B2 and the folded FIR save
   1.8 % and 0.6 %. `ble-tx-sin4` only looked larger (+2.0 % of cell area)
   because the flow does not count the memory it removes. `ble-tx-sin8`, with
   one memory for both quarter tables, takes it to 67 437 µm² (−59.8 %), and
   `ble-tx-opt`, which adds B2, to 64 441 µm² (−61.6 %). One port, which is
   enough because the transmitter takes one sample every two clocks, halves
   that memory again: `ble-tx-sin8-1rw` measures 46 773 µm² (−72.1 %), and
   `ble-tx-sin2`, which keeps only the quarter sine table and reads it twice
   per sample, 40 293 µm² (−76.0 %), the smallest built before `ble-tx-pdu`, with the
   receiver and the debug memory unchanged. `ble-tx-1--8`, an eighth of both
   tables in the 256 × 16 memory the sweep found best, read once per sample,
   measures 40 359 µm² (−75.9 %): its eighth-wave logic takes back what the
   smaller memory saves, so it ties with `ble-tx-sin2` and keeps what
   `ble-tx-sin2` gives up, table writes while transmitting and a sample on any
   clock. The packet buffer is then most of what is left. Their cost is
   function, not area: the tables must have quarter-wave symmetry, which the
   project's tables have (identical outputs, § 6.1); the table writes are
   limited, to one entry per clock between the two tables on `ble-tx-sin8`, to
   the clocks the VCO does not read on the one-port branches; on `ble-tx-sin2`
   and `ble-tx-1--8` the cosine and sine tables are tied; and on `ble-tx-opt`
   the Gaussian taps are fixed (§ 8). `ble-tx-pdu` then gives the packet
   buffer, most of what was left, one port and 256 words, with B2, the memory
   of `ble-tx-sin2` and exact rewrites of the counters: 20 098 µm² (−88.0 %),
   half of `ble-tx-sin2`, for one more contract, the packet written before
   `tx_start`. `ble-tx-pdu-we` keeps that transmitter and writes its buffer
   only when the pair is new (§ 6.6). On the audited RTL (§ 4.4) `ble-tx-rom`
   then fixes the VCO's tables in a ROM and removes the last VCO memory:
   9 488.5 µm², −94.5 % against `master` and half of `ble-tx-pdu`, for the
   programmability of the tables.
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
   subset can be combined with a predictable result, and `ble-tx-opt` shows
   it built: B2 with the memory of `ble-tx-sin8` measures 64 440.8 µm²
   against 64 440.0 estimated, the flip-flops add up exactly and the activity
   to within 0.1 point. With the folded FIR, which keeps the taps
   programmable, the same combination is estimated at −60.4 %; with the
   memory of `ble-tx-sin2`, B2 at −77.8 % and the folded FIR at −76.6 %; with
   that of `ble-tx-1--8`, B2 at −77.7 %. `ble-tx-pdu` builds the first of
   these, B2 with the memory of `ble-tx-sin2`, together with its own packet
   buffer and rewrites.
6. **Activity ranks the changes differently from area.** The debug
   infrastructure (A1 + A2) gives most of the 25–35 % proxy reduction, because
   it is logic clocked on every cycle; B1 lowers the clock load but raises data
   switching when the receiver has no traffic; B2 matters only while
   transmitting.
7. **Timing does not separate the branches.** All close 16 MHz. Before the
   audit those measured did it with a factor of about 30,
   none with the worst path in the transmitter, within the flow's noise of
   each other (§ 5). On the audited RTL (§ 5.1) corrected `master`'s worst path
   is the Gaussian tail the audit added, with the runtime taps (3.458 ns, a
   factor of 18), `ble-tx-rom` keeps a factor of 31, and the CORDIC of
   `ble-tx-cordic`, 15 stages in one clock, is the controller's worst path:
   5.501 ns, a factor of 11.
8. **The SRAMs' energy follows their accesses and their clocks.** Measured
   with SPICE (§ 6.6), the transmitter's SRAMs of `ble-tx-pdu` take 42.4 µW of
   dynamic power in every scenario, 14.2 of them to write the packet buffer on
   every AXI clock. Writing it only when its pair is new (`ble-tx-pdu-we`)
   takes them to 28.20–28.37 µW (−34 %), and saves more at a faster AXI
   clock; what is left is the clocks of the two macros and the sine table,
   read on every clock. Their leakage, 40.1 µW once settled with every cell at 0, is
   of the same order; at rest, with random data in the words never written, the
   deselected buffer takes 10.3 to 19.8 µW more, as much as the strobe saves.
   `ble-tx-rom` and `ble-tx-cordic` have no VCO memory: their SRAM is the packet
   buffer alone, 19.40 µW of dynamic power and 15.0 µW of leakage.
9. **A fixed VCO table is cheapest as a ROM.** Fixing the tables removes the
   last VCO memory (10 703.9 µm²). The ROM of an eighth of the wave costs
   593.2 µm², less than the logic of the sine-table VCO it replaces; an exact
   CORDIC computes the same tables with 2 317.9 µm² and puts the worst path in
   the transmitter. The price of both is the programmability of the tables
   (§ 8).

## 10. What this does not claim

- **No FPGA, no silicon, no power of the logic.** Area and timing are
  pre-layout (ideal wires, ideal clock, setup only, RAM macros not timed).
  Switching activity is a pin-capacitance proxy with no wires, no clock tree,
  no internal energy and no leakage, from zero-delay simulation, which does not
  count glitches.
- **The SRAM energy of § 6.6 is a model too**: OpenRAM's SPICE
  characterization of FreePDK45 netlists (no layout parasitics), at one corner
  (TT, 1.0 V, 25 °C), one input slew and one output load, at a 5 ns cycle, and
  the leakage of a deselected macro once settled, with every cell at 0 (and,
  for the buffer at rest, with the words the RTL leaves in it), for the
  transmitter's memories only and three configurations, applied to access
  counts of one stimulus set at RTL. A commercial memory would give other
  absolute figures; the counts do not depend on the model.
- **The SRAM macros of § 4 are OpenRAM layouts in FreePDK45**, an academic
  PDK, generated without DRC/LVS and never placed with the logic. A commercial
  compiler would be denser, and its small macros relatively more so. Only the
  transmitter's RAMs are converted to area. The receiver's are the same on
  every branch, and the RAMs that `ble-opt` removes (the IQ-capture RAM, the
  Link Layer crossings) are counted in bits only.
- **One stimulus set** for activity (example 0 of the Python model, seed 1,
  100 000 cycles per scenario).
- **§§ 4.4 and 5.1, and the columns marked † in § 2, are the only figures of
  the audited RTL in §§ 2–5**, and they are of the revisions before the lint
  closure of 2026-10-06 (`LINT_CLOSURE.md`), which changed the RTL again and was
  not measured: the rest of §§ 2–5 describes the RTL before the product audit, and the activity of
  §§ 6.1–6.5 has not been measured again (its coverage is open in
  `RF_INTERFACE_REVIEW.md`).
- **The resolution of the method.** The same block, with the same RTL and the
  same stimulus, can differ by up to about 3 % between two netlists
  (`btle_ll` toggles −2.0 % on `ble-tx-table`, whose Link Layer is the upstream
  RTL mapped to 29 fewer cells, and +3.0 % on `ble-tx-fir2`), and timing by up
  to about 0.15 ns (§ 5); the area of the same RTL by 3.6 % on the transmitter
  with the runtime FIR (§ 4.4).
- **A1 and A2 are not isolated in a branch of their own**; their share is
  measured on their own blocks, and §§ 3.2 and 6.4 show it is consistent with
  the totals.
- **Two combinations of the transmitter changes are built**: `ble-tx-opt`
  (B2 with the {cos, sin} memory) and `ble-tx-pdu` (B2 with the memory of
  `ble-tx-sin2`, with its own packet buffer and rewrites). The ones with the
  folded FIR, and B2 with the memory of `ble-tx-1--8`, are estimated from the
  parts in § 4.
- **The {cos, sin} memory of `ble-tx-sin8` and `ble-tx-opt` is checked by
  simulation**, at module level against `ble-tx-sin4` and at gate level
  against upstream, not by a formal proof: the write port's contract (§ 8) is
  exercised, not proved. So are the one-port memories of `ble-tx-sin8-1rw`,
  `ble-tx-sin2`, `ble-tx-1--8`, `ble-tx-pdu` and `ble-tx-pdu-we` (their packet
  buffer too), and the packet buffer of `ble-tx-rom` and `ble-tx-cordic`; their
  one-port behaviour is checked
  against a behavioural model of a one-port macro (one address, the output
  kept in a clock with a write), not against a vendor's macro model.
- **The ROM and the CORDIC are checked by simulation**, against the `master`
  VCO with the project's tables: on all 2 048 phases, which is exhaustive for
  them (their output depends on the phase alone), and on random traffic; not
  by a formal proof.

## 11. Reproducing

From WSL, at the root of `ble-opt`, `ble-tx-table`, `ble-rx-dm`,
`ble-tx-opt`, `ble-tx-pdu`, `ble-tx-pdu-we`, `ble-tx-rom` or `ble-tx-cordic`. The harness is
the same set of files on the eight branches, and
it reads every branch through `git archive`, so the branch checked out does
not matter:

```bash
scripts/compare/run_compare.sh <label>                          # about 1 h, master, ble-tx-table, ble-rx-dm, ble-opt
scripts/compare/run_compare.sh <label> master ble-tx-table-reg ble-tx-table-sram ble-tx-fir2 ble-tx-sin4
scripts/compare/run_compare.sh <label> master ble-tx-sin8
scripts/compare/run_compare.sh <label> master ble-tx-opt
scripts/compare/run_compare.sh <label> master ble-tx-sin8-1rw ble-tx-sin2
scripts/compare/run_compare.sh <label> master ble-tx-1--8
scripts/compare/run_compare.sh <label> master ble-tx-pdu
scripts/compare/run_compare.sh <label> master ble-tx-pdu-we
# the activity of these runs exactly: reuse their vectors
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> [name ...]
# the SRAM macros of § 4, about 20 + 10 min (OpenRAM in its own environment, see the script)
scripts/area/run_openram.sh <label> sram_1rw_8x2048 sram_1rw1r_8x2048 sram_1rw_8x512 sram_1rw1r_8x512
scripts/area/run_openram.sh <label> sram_1rw1r_16x512_m8 sram_1rw_16x512_m8
scripts/area/run_openram.sh <label> sram_1rw_16x256_m8           # the memory of ble-tx-1--8 (run openram-1rw-sweep)
scripts/area/run_openram.sh <label> sram_1rw_8x256               # the packet buffer of ble-tx-pdu (run openram-pdu)
# the SRAM energy of § 6.6: the macros with SPICE (about 1 h and 4 h), their settled leakage with every
# cell at 0, then the accesses against the current reference (minutes), then the buffer at rest (25 min)
PERIOD_NS=5 scripts/power/run_sram_char.sh <char-label> sram_1rw_8x256 sram_1rw_8x512
scripts/power/run_sram_leakage.sh <leak-label> sram_1rw_8x256 sram_1rw_8x512
python3 scripts/power/summarize_sram_char.py results/power/<char-label> sram_1rw_8x256 sram_1rw_8x512 \
  --leakage results/power/<leak-label>/leakage.json > results/power/<char-label>/summary.md
SRAM_CHAR=results/power/<char-label> VEC_DIR=/tmp/vec REF_REV=5abbbf7a093b48a64f18c2c1f84057c54d0af0e5 \
  scripts/power/run_sram_energy.sh <label> master ble-tx-pdu ble-tx-pdu-we
scripts/power/run_sram_idle.sh <idle-label> <label> ble-tx-pdu-we idle tx
# § 4.4 and § 5.1, run tx-vco (in a clone): every branch at its head, in the configuration
# scripts/branch_config.sh gives it (PDU_WRITE_STROBE=1 on ble-tx-pdu-we)
for b in master ble-rx-dm ble-opt ble-tx-table ble-tx-table-reg ble-tx-table-sram ble-tx-fir2 ble-tx-opt \
         ble-tx-sin4 ble-tx-sin8 ble-tx-sin8-1rw ble-tx-sin2 ble-tx-1--8 ble-tx-pdu ble-tx-pdu-we ble-tx-rom ble-tx-cordic; do
  t=$(mktemp -d); git archive origin/$b verilog | tar -x -C $t; p=$(scripts/branch_config.sh $t/verilog); rm -rf $t
  RTL_REV=origin/$b AREA_PARAMS="$p" scripts/area/run_area.sh <label>/$b vco btle_tx
done
for b in ble-tx-pdu ble-tx-rom ble-tx-cordic; do
  DUT_REV=origin/$b scripts/timing/run_sta.sh <label>/$b 62.5 5abbbf7a093b48a64f18c2c1f84057c54d0af0e5
done
```

The first name is the reference of the summary, so it must be `master`. The
script refuses to overwrite a label. It records, per configuration, the
revision, commit, `verilog/` tree and parameters in `provenance.txt`
([`all-branches`](../../results/compare/all-branches/provenance.txt),
[`tx-variants`](../../results/compare/tx-variants/provenance.txt),
[`tx-sin8`](../../results/compare/tx-sin8/provenance.txt),
[`tx-opt`](../../results/compare/tx-opt/provenance.txt),
[`tx-1rw`](../../results/compare/tx-1rw/provenance.txt),
[`tx-1--8`](../../results/compare/tx-1--8/provenance.txt),
[`tx-pdu`](../../results/compare/tx-pdu/provenance.txt),
[`tx-pdu-we`](../../results/compare/tx-pdu-we/provenance.txt)), writes
`summary.md` and `data.json`, and fails if a consistency check fails. Area and
timing take about a minute; activity about 15 minutes per configuration. Run
`tx-vco` lists its configurations in
[`results/area/tx-vco/provenance.txt`](../../results/area/tx-vco/provenance.txt).

Run `all-branches`' own summariser (`f540e99`) compared the capacitance sums of the
upstream side bit for bit and flagged them, although every count was
identical: the sums differ by about 10⁻¹⁵ relative, because `saif_activity.py`
adds them in Python-set order, which changes from one process to the next.
`696b036` compares counts exactly and sums to 10⁻⁹; the summary was
regenerated from the same measurements with it, and every check passes. No
measurement was repeated or changed.
