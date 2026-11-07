# Validation of the shared demodulator with one multiplier (`ble-rx-dmult`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-dmult`, cut from `ble-rx-dm` (`38755a0`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: corrected `master` (`fca6ac6`) and `ble-rx-dm`  
**Date:** 2026-10-18  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `f00bd9e` (no RTL changed after it); harness `aa83311` … `15fca3b`.
The campaign of § 2 started at `11a602b`; the formal proof, the harness tests and the loopback through
the RTL receiver ran again at `15fca3b`, after the fixes of the formal runner and of its test; the
commits between change no file the other checks use. Area, timing and activity:
`docs/Validation/RX_BRANCH_COMPARISON.md`.

---

## Purpose

This report records the evidence that computing the two products of the shared GFSK
demodulator with one multiplier, in two consecutive clocks, instead of two in one clock:

1. **changes no output**: on every clock, the 8 per-phase `phy_bit` and `bit_valid` that the
   decoders consume are those of `ble-rx-dm`, and so those of upstream's 8 demodulators; the
   controller passes every check of the product audit and the lint closure that `ble-rx-dm`
   passes;
2. **needs exactly one condition, which the controller gives**: a sample is never valid in two
   consecutive clocks.

## 1. The change

`ble-rx-dm` (B1) computes, for every sample of phase p, `signal = old_i·new_q − new_i·old_q`
(`old` the previous sample of the phase, `new` this one) with two 16 × 16 signed multipliers in
the clock after the history read (E2), and decides `phy_bit = signal > 0` in the next (E3).
`ble-rx-dmult` keeps the capture, the per-phase history, the three-stage latency and the reset
behaviour, and shares one multiplier between the two products:

| Clock | `ble-rx-dm` | `ble-rx-dmult` |
|---|---|---|
| capture | `s_i`, `s_q`, `s_phase`, `s_valid` | the same |
| E1 (`s_valid`) | read `hist[s_phase]` into `old_i`, `old_q`; `new_i`, `new_q` ← the sample; write the history | read the history; `old_q`, `new_i` ← the history's Q and the sample's I; **`product_a` ← `hist_i[s_phase]·s_q`** (= `old_i·new_q`), on the multiplier; write the history |
| E2 (`valid1`) | `signal ← old_i·new_q − new_i·old_q` (two multipliers) | **`signal ← product_a − new_i·old_q`**, the second product on the same multiplier |
| E3 (`valid2`) | `phy_bit[phase2] ← signal > 0`, one-hot `bit_valid` | the same |

The multiplier's operands are `valid1 ? (new_i, old_q) : (hist_i[s_phase], s_q)`. With a sample
in E1 and the one before it in E2 in the same clock, the multiplier would be needed twice; that
happens only if `iq_valid` is high in two consecutive clocks, which is the contract of the
module: **at most one sample every two clocks**. The 32-bit first product replaces the operand
registers `old_i` and `new_q`: the same 412 flip-flops in the RTL.

Files: [`verilog/gfsk_demodulation_shared.v`](../../verilog/gfsk_demodulation_shared.v) only.

**The contract at the controller.** `clock_domain_conversion_iq` crosses the samples from the RF
clock (8 MHz) into `bb_clk` (16 MHz) with a 2:1 phase that toggles on every clock and raises
`rx_iq_valid` only when that phase is 0:

```verilog
rx_sample_phase <= ~rx_sample_phase;
rx_iq_valid <= (~rx_sample_phase) && rx_iq_valid_ext;
```

so `rx_iq_valid` is never high in two consecutive clocks, whatever `rx_iq_valid_ext` does
(proved, § 2.1, task `cdc_gap`). `btle_controller` connects it to `btle_phy` (`.rx_iq_valid`), and
`btle_phy` to `btle_rx` (`.iq_valid(rx_iq_valid)`), with no other driver.

## 2. Evidence

Every run records its commit, tools and inputs in a `provenance.txt` or `provenance.json`, keeps
its logs, and refuses to overwrite a label. The logs of the checks that write no folder of their own,
and the campaign's exit codes, are in [`results/validation/dmult-campaign/`](../../results/validation/dmult-campaign/summary.txt).

### 2.1 Formal equivalence with `ble-rx-dm`

`scripts/validation/formal_dmult/run_formal_dmult.sh dmult` (reference: `38755a0`, the head of `ble-rx-dm`), results in
[`results/validation/dmult/formal_dmult/`](../../results/validation/dmult/formal_dmult/result.txt).

A miter holds the shared demodulator of `ble-rx-dm` (taken from that revision, renamed) and the
working tree's, on the same inputs. Every input is free on every clock: I, Q, the sample valid,
the phase of the sample (so the result holds for any phase sequence, not only btle_rx's counter),
`rst` and the decoders' restart. One assumption: the contract, `iq_valid` never high in two
consecutive clocks. The property: the 8 `phy_bit` and 8 `bit_valid` are equal on every clock.

| Task | What it proves | Result |
|---|---|---|
| **`prove_w16_cut`** | the property at the **real width (16-bit I/Q), unbounded**: base case from reset (depth 16) + k-induction, with inductive invariants that are themselves proven; every 16 × 16 product abstracted (below) | **PASS**, in seconds |
| `prove_w4` | the same unbounded proof with the **real multipliers**, I/Q reduced to 4 bits | **PASS** |
| `cdc_gap` | `clock_domain_conversion_iq` (the working tree's) never raises `rx_iq_valid` in two consecutive clocks, for any `rx_iq_valid_ext`, unbounded | **PASS** |
| `no_gap` | the miter without the contract, bounded: it must fail | **FAIL, as required**: a counterexample in which two samples arrive in consecutive clocks |
| non-vacuity | 6 mutants of the dut must each make both proofs fail | **6 of 6 rejected by both** |

**How the 16-bit proof works.** With the real multipliers the induction step did not close: in 1 h
at k = 4 with bitwuzla, nor in 90 min at k = 1 with bitwuzla or yices (task `prove_w16`, kept in `dmult_equiv.sby`, not in the campaign).
The solver has to match products whose operands are equal only through the invariants, as for B1
(`SHARED_DEMOD_VALIDATION.md` § 2.1). `prove_w16_cut` reads copies of both demodulators in which
every product is a free value: in the reference the two products of `old_i*new_q − new_i*old_q`,
in the dut the multiplier's output. The miter constrains them only to be **one function of their
operands**: within a clock and between a clock and the one before, equal operands give an equal
result. The real products are such a function, the same 32-bit product of sign-extended 16-bit
operands in both designs, so the proof for every such function holds for them, and no
multiplier is left in it. The runner checks what the copies replace: in the reference exactly
`old_i*new_q - new_i*old_q`, the only non-reset assignment of `signal_for_decision`; in the dut
`product = mul_x*mul_y`, the only multiplication of the file. The abstracted sources are kept in
the results folder for review. Everything else (capture, history, pipeline, the multiplexer, the
resets, the routing to the phases) is in the proof unabstracted.

The inductive invariants state that the capture stages, the histories, the E1 and E2 registers and
the outputs of the two designs are equal; that a capture and the stage after it are never busy
together (the contract as the dut sees it); and that the multiplier's operands and result one clock
ago are the reference's operands of E2 and the first product the dut holds.

The mutants, each a plausible mistake: the history kept when the decoders restart; a zero decision
counted as a one; the two products subtracted the other way round; `bit_valid` one clock early;
the multiplier given the E2 operands in the clock of a capture; the first product taken from the Q
history. Each makes both proofs fail (`mutants.txt`).

**With B1's proof, the equivalence with upstream.** `SHARED_DEMOD_VALIDATION.md` proves the
shared demodulator of `ble-rx-dm` equivalent to upstream's 8 demodulators, unbounded at 16 bits,
for any input; its demodulator has not changed since. This proof makes `ble-rx-dmult`'s equal to
it under the contract.

### 2.2 Clock-by-clock lockstep of `btle_rx` against corrected `master`

`scripts/validation/rx_lockstep/run_rx_lockstep.sh dmult 20 200 master`, results in
[`results/validation/dmult/rx_lockstep/`](../../results/validation/dmult/rx_lockstep/result.txt).

Corrected `master`'s complete `btle_rx` (8 decoders, each with its own demodulator, the CRC
selection, the packet buffers) and `ble-rx-dmult`'s run side by side on the same stimulus; on every
clock the testbench compares every output (`hit_flag`, `decode_run`, `decode_end`, `crc_ok`,
`best_phase`, `payload_length`, `pdu_octet_mem_data` at a random read address) and the `phy_bit`
and `phy_bit_valid` that each of the 8 decoders consumes. Stimulus as for B1: the three packets of
the Python model, replayed at random offsets between random noise of random amplitude (up to full
scale, with the multiplier corners −32768 and 32767), truncated packets, random resets, some in
mid-packet; with `MIN_GAP=1`, a sample is never valid in the clock after another (the patterns
"every clock", "every other clock" and "random gaps" become every other clock and random gaps of at
least one clock).

**Result: 60 of 60 runs with zero mismatches** (3 packets × 20 seeds × 200 segments), over:

| Compared | Total |
|---|---:|
| clock cycles | 37 054 155 |
| I/Q samples | 17 558 142 |
| per-phase demodulated bits (`phy_bit_valid` pulses) | 17 540 260 |
| access-address hits | 8 878 |
| decode ends | 7 695 |
| packets decoded with a correct CRC | 7 521 |
| resets (some in mid-packet) | 1 632 |

Mutation check: the 6 mutants of § 2.1, each run through the lockstep, must be caught: **6 of 6 caught**.
Contract check: the unmutated design, given samples on consecutive clocks, must be caught too:
**caught, at clock 21, in the per-phase `phy_bit`**: the lockstep sees what the contract excludes.

### 2.3 The campaign of the product audit and the lint closure

The commands with which the lint closure validated `ble-rx-dm`
(`results/validation/lint-evidence-20261006/commands.json`), on `ble-rx-dmult`:

| Check | Command | Result |
|---|---|---|
| The product audit's matrix, 270 cases (210 data comparisons, 60 verified rejections), the five upstream testbenches, against the pinned pre-lint reference `9d6c383` | `scripts/validation/run_rx_regression.sh dmult-functional 9d6c383…` | **270/270**: 210 data comparisons, 60 verified rejections; 0 DIFFERENT, 0 ERROR |
| TX waveforms, Python decoding | `tests/test_tx_packet.py` | **167/167**, and **167/167 decoded by the branch's RTL receiver** (`--rtl-rx`, `tx_packets_rtl_rx.json`) |
| Lint gate: Verilator 5.020 `--lint-only --Wall`, warnings fatal, the reviewed exceptions | `scripts/validation/run_lint.py` | **PASS**: 1/1 configuration, 12 reviewed exceptions |
| Illegal-state recovery | `tests/test_lint_recovery.py` | PASS: 3 illegal encodings recovered without valid outputs |
| Lint negative controls | `tests/test_lint_guards.py` | PASS: 12 baseline and negative-control checks |
| Product defects detected | `tests/test_product_mutations.py` | 4/4 defects caught, 2 clean baselines |
| RF interface contract, with mutants | `tests/test_clock_domain_contract.py --mutants` | 12/12 scenarios, 2/2 mutants detected |
| Gaussian tail, bit repeat, reserved-register readback | `tests/test_gauss_tail.py`, `test_upsample.py`, `test_control_readback.py` | PASS, PASS, PASS |
| Yosys structure of the controller | `yosys … elaborate.ys` | PASS |
| Harness tests | `python -m unittest discover -s tests -p 'test_validation*.py'` | 21 of 23 passed, 2 skipped (they need `REGRESSION_VECTORS`). The first run failed one: the entry-point test ran B1's formal runner, whose guard rejects this branch's demodulator before any engine; the test now runs `formal_dmult` here (`15fca3b`), and passes |

### 2.4 Gate-level lockstep of the whole controller

The activity runs of `RX_BRANCH_COMPARISON.md` § 5 simulate the synthesised netlists of corrected
`master` and of the branch side by side, in 5 scenarios of 100 000 clocks, and compare every output
and every register read on every clock: **every output identical to corrected `master` on every clock, in the 5 scenarios**.

### 2.5 What was not changed

Only `gfsk_demodulation_shared.v` differs from `ble-rx-dm` in `verilog/`. `btle_rx`,
`btle_rx_core`, the decoders (`search_unique_bit_sequence`, `scramble_core`, `crc24_core`,
`serial_in_ram_out`), the transmitter, the Link Layer and the RAM models are those of `ble-rx-dm`,
whose files outside the receiver are corrected `master`'s; the lockstep script checks the shared
decoder files against its reference before it runs.

## 3. What is not claimed

- **Not proved on FPGA or silicon**; no board test.
- **The 16-bit proof abstracts the products** (§ 2.1); with the real multipliers it is proved at 4
  bits and checked by simulation at 16 bits (§§ 2.2–2.4).
- **The connection of the contract above `clock_domain_conversion_iq`** (`btle_controller` →
  `btle_phy` → `btle_rx`) is a direct connection in the RTL, exercised by the matrix and the
  gate-level lockstep, not proved; a `btle_rx` reused with another sample source needs that source
  to keep a clock between samples.
- **Area, timing and activity** are in `RX_BRANCH_COMPARISON.md`, with their limits.

## 4. Reproducing

From WSL, at the root of `ble-rx-dmult`, with the OSS CAD Suite 2026-09-07 (Yosys, Icarus, SBY,
bitwuzla, yosys-slang), Verilator 5.020 for the lint gate, and Python 3.11 with numpy 2.4.6:

```bash
scripts/validation/formal_dmult/run_formal_dmult.sh <label> ble-rx-dm
scripts/validation/rx_lockstep/run_rx_lockstep.sh <label> 20 200 master
bash scripts/validation/run_rx_regression.sh <label>-functional 9d6c383110454c23600766bc70156142d8fb6c1e
python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
# and the other commands of § 2.3
```
