# Validation of the shared GFSK demodulator (optimisation B1)

> Validation correction (2026-10-04): earlier success claims for all 270 checks are withdrawn. The strict rerun is **FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See [the integrity audit](VALIDATION_INTEGRITY.md) for evidence and limitations.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-opt`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-19  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `aa8a014`; harness fix `de0cc54`; formal harness `7d2bcbd`.  

---

## Purpose

This report records the evidence that replacing the 8 per-phase GFSK
demodulators of `btle_rx` with one shared demodulator:

1. **removes no function**: transmission, reception, the 8 sampling-phase
   hypotheses, the CRC-based selection, the packet buffers and the reset
   behaviour are all unchanged; and
2. **reduces the cell count**, measured with the same flow as the baseline.

## 1. The change

| | Upstream | After B1 |
|---|---|---|
| Demodulators | 8 × `gfsk_demodulation` (one inside each `btle_rx_core`) | 1 × `gfsk_demodulation_shared` |
| Multipliers | 16 (8 × 2, 16 × 16 signed) | 2 |
| Decoders (AA search, de-whitening, CRC, PDU buffer) | 8 | 8, unchanged |
| CRC-based phase selection | yes | unchanged |
| Sample storage | `i_store`/`q_store`: 8 × 32 bits in `btle_rx` + 8 × 128 bits of sign-extended copies inside each demodulator | 8 × 32 bits of history + one 3-stage pipeline |

```
upstream:  I/Q ─► distribute to phase p ─► [demod p] ─► decoder p ─┐
                                            × 8                     ├─► CRC selection
after B1:  I/Q ─► [shared demod: history[p], 2 multipliers] ─► bit p ─► decoder p ─┘
```

Each copy of the upstream demodulator computed, for its phase,
`signal = i[n-8]·q[n] − i[n]·q[n-8]` and `phy_bit = signal > 0`, one symbol
apart. The shared unit keeps one history entry per phase and computes the same
product for every incoming sample. It reproduces, per phase and on every clock,
what each copy drove on `phy_bit` and `bit_valid`:

- the same capture edge;
- the same three-stage latency (E1 operands, E2 product, E3 decision);
- the same clearing of every phase's history whenever the decoders restart
  (`rst | decode_end_early | decode_end_all`).

It accepts one sample per clock. The board and the testbenches deliver one
every other clock.

Files: [`verilog/gfsk_demodulation_shared.v`](../../verilog/gfsk_demodulation_shared.v)
(new); `btle_rx.v` and `btle_rx_core.v` (modified: `EXTERNAL_DEMOD`, default 0,
keeps `btle_rx_core` identical to upstream when used alone); the file lists in
`btle_controller.tcl` and the testbench headers.

## 2. Evidence that no function was lost

Three independent kinds of evidence, plus a check of what was not touched.
Each one is reproducible with one command,
and each run records its commit, tools and inputs in a `provenance.txt`.

### 2.1 Formal equivalence

`scripts/validation/formal_demod/run_formal.sh`.

A miter holds, on one side, the upstream sample distribution (verbatim) with
the **8 upstream `gfsk_demodulation` instances** (taken from the tag and
renamed), and on the other side the new phase counter with the shared
demodulator. All inputs are free on every clock, and so is the decoder
restart, so the result holds for any restart sequence the decoders could ever
produce. The property is that the 8 `phy_bit` and 8 `bit_valid` signals are
equal on every clock.

Results in
[`results/validation/shared-demod-w16/formal_demod/`](../../results/validation/shared-demod-w16/formal_demod/result.txt)
(commit `6af6cfe`). The first campaign, without `prove_w16_cut`, is in
`results/validation/shared-demod/formal_demod/`.

| Task | What it proves | Result |
|---|---|---|
| **`prove_w16_cut`** | the property at the **real width (16-bit I/Q), unbounded**: base case from reset + k-induction (depth 16), with explicit inductive invariants that are themselves proven. The decision arithmetic is abstracted (see below). | **PASS**: "successful proof by k-induction", 34 s |
| **`arith_w16`** | the decision arithmetic at the real width: the upstream expression (operands sign-extended into 32-bit registers) and the new one (16-bit operands, 32-bit result) give the same `signal_for_decision` and the same `> 0` decision for all 2⁶⁴ operand values | **PASS** |
| `prove_w4` | the same unbounded proof with the real multipliers, I/Q reduced to 4 bits (cross-check without abstraction) | **PASS** |
| non-vacuity | 4 mutants of the new design must each be rejected | **4 of 4 rejected**: `history_kept_on_decode_end`, `sign_ge` and `valid_one_early` give concrete counterexamples from reset in both proofs (steps 3–5); `swapped_operands` changes the arithmetic, so the guard rejects it before the abstracted proof runs, and `prove_w4` gives a counterexample |

**How the 16-bit proof works.** A proof that keeps the real 16 × 16
multipliers did not close in an hour with bitwuzla or yices. The induction step
asks the solver to match products whose operands are equal only under a
condition, which bit-level solving handles poorly. The proof is therefore split
in two, and each half closes:

1. **`arith_w16`:** the two expressions are the same function, for every
   16-bit operand.
2. **`prove_w16_cut`:** in copies of both demodulators, the value assigned to
   `signal_for_decision` is replaced by a free value. It is constrained only by
   properties that any function of the operands has:
   - zero operands give zero;
   - unchanged operands on consecutive clocks give the same value;
   - the upstream copy's operands, equal to the sign-extended operands of the
     shared unit, give the same value in both designs.

   The last property is exactly what `arith_w16` establishes. The runner
   generates the copies with guards: the replaced expression must occur once,
   be the only non-reset assignment to `signal_for_decision`, and be textually
   the expression `arith_w16` proves. The abstracted sources are kept in the
   results folder for review.

Together, (1) and (2) give **the unbounded equivalence at the real width**.
Everything else in the demodulator (capture, phase counter, per-phase history,
pipeline, valid delays, resets and routing) is in the proof unabstracted.

The inductive invariants state, for every phase, that:
- the upstream copy's newest sample equals the shared history entry;
- its valid delay line equals the shared pipeline for that phase;
- the in-flight samples belong to consecutive phases;
- between updates, each copy's decision signal and bit follow its registers.

They need hierarchical references, so the miter is read with yosys-slang.

### 2.2 Clock-by-clock lockstep against upstream

`scripts/validation/rx_lockstep/run_rx_lockstep.sh`, results in
[`results/validation/shared-demod/rx_lockstep/`](../../results/validation/shared-demod/rx_lockstep/result.txt).

The complete upstream `btle_rx` (8 decoders, CRC selection, PDU buffers) and
the new `btle_rx` run side by side in one simulation on the same stimulus. On
every clock the testbench compares every output (`hit_flag`, `decode_run`,
`decode_end`, `crc_ok`, `best_phase`, `payload_length`, `pdu_octet_mem_data`
with a random read address) and the `phy_bit`/`phy_bit_valid` that each of the
8 decoders consumes.

Stimulus: the three packets of the Python model, replayed at random offsets
between random noise of random amplitude (up to full scale, with the
multiplier corner values −32768 and 32767). The valid pattern is every clock,
every other clock, or random gaps. It also includes truncated packets and
random resets, some of them in the middle of a packet.

**Result: 60 of 60 runs with zero mismatches** (3 packets × 20 seeds ×
200 segments), over:

| Compared | Total |
|---|---:|
| clock cycles | 25 367 270 |
| I/Q samples | 17 590 707 |
| per-phase demodulated bits (`phy_bit_valid` pulses) | 17 563 484 |
| access-address hits | 8 880 |
| decode ends | 7 656 |
| packets decoded with a correct CRC | 7 510 |
| resets (some in mid-packet) | 1 701 |

Mutation check: the same 4 mutants, each run through the lockstep, must be
caught. **4 of 4 caught**. The history-not-cleared mutant is caught only at
clock 666, after the first packet ends, which shows that the stimulus reaches
the decoder-restart path.

### 2.3 Upstream testbenches over a condition matrix

`scripts/validation/run_rx_regression.sh`, results in
[`results/validation/shared-demod/rx_regression/`](../../results/validation/shared-demod/rx_regression/result.txt).

The five upstream testbenches that apply (`gfsk_demodulation_tb`,
`btle_rx_core_tb`, `btle_rx_tb`, `btle_tx_tb`, `btle_controller_tb`, the last
being TX + RX + LL together) run on upstream and on the new RTL, for
3 packets × SNR {20, 12, 8} dB × clock error {0, 20, 50} ppm × sample delay
{0, 5}. For every run, both designs must give the same verdict **and** the same
output files, byte for byte.

**FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**.

The earlier table counted incomplete checks as successful. Corrected per-bench counts are in the [integrity audit](VALIDATION_INTEGRITY.md).

### 2.4 What was not changed

`btle_tx`, `btle_ll`, the decoders (`search_unique_bit_sequence`,
`scramble_core`, `crc24_core`, `serial_in_ram_out`) and the RAM models are
byte-identical to upstream. The lockstep script checks this for the shared
decoder files before it runs.

## 3. Area (measured)

Same flow as the baseline (`scripts/area/run_area.sh`, Yosys 0.68,
Nangate45, SRAMs as macros). Runs `baseline-upstream` (commit `74bb17c`) and
`shared-demod` (commit `aa8a014`).

| Top | Cells before | Cells after | Δ cells | Cell area before (µm²) | after (µm²) | Δ area |
|---|---:|---:|---:|---:|---:|---:|
| `btle_rx` | 36 864 | 10 068 | **−26 796 (−72.7 %)** | 48 824.3 | 15 887.9 | −67.5 % |
| `btle_phy` | 40 339 | 13 536 | −26 803 (−66.4 %) | 54 040.3 | 21 255.5 | −60.7 % |
| `btle_controller` | 50 295 | 23 346 | **−26 949 (−53.6 %)** | 71 706.4 | 38 782.3 | −45.9 % |
| flip-flops in `btle_controller` | 4 578 | 3 926 | −652 | | | |
| SRAM bits in `btle_controller` | 1 136 070 | 1 136 070 | 0 | | | |

The estimate in
[AREA_REDUCTION_PLAN.md](../Design%20Decisions/AREA_REDUCTION_PLAN.md) was
≈ 27 293 cells. The measured saving is 26 949, because the shared unit and its
history cost about 350 cells.

**Flow noise.** Modules whose RTL did not change moved by a few cells:
`btle_tx` 3 409 → 3 411, and `btle_rx_core` when synthesised alone 4 438 →
4 495, because its default configuration still contains its own demodulator.
ABC's result depends on the order in which the files are read, and the new run
reads one more file. These changes are about 0.1 % and do not affect the
conclusion.

## 4. What is not claimed

- **Not proved on FPGA or silicon.** The Vivado project file list was updated
  but not run here, and no board test was done.
- **No timing closure.** The shared multiplier pair now serves all phases at
  up to one sample per clock. Its combinational depth is the same as each
  upstream copy's (one 16 × 16 product and a subtraction per stage), but no
  STA was run.
- **Power** was not measured. Leakage should fall with the cell count, but in
  upstream each copy's multipliers only switched when its own phase's
  operands changed, so the dynamic-power effect is not obvious and needs a
  measurement.

## 5. Reproducing

From WSL, at the repository root, on commit `ec3ccf0` or later:

```bash
scripts/area/run_area.sh <label>
scripts/validation/run_rx_regression.sh <label>
scripts/validation/rx_lockstep/run_rx_lockstep.sh <label> 20 200
scripts/validation/formal_demod/run_formal.sh <label>
```

Tools: OSS CAD Suite 2026-09-07 (Yosys 0.68+195, Icarus 14, SBY, Bitwuzla,
yosys-slang) and Python 3.11 with numpy 2.4.6 for the vector generator.
