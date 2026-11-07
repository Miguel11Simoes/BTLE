# Validation of one decoder for the 8 phases (`ble-rx-shared`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-shared`, cut from `ble-rx-dm` (`38755a0`), with the Access Address detector and the harness of `ble-rx-aa` (`06bee7b`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: corrected `master` (`fca6ac6`) and `ble-rx-dm`  
**Date:** 2026-10-18  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `ed8412f` (no RTL changed after it); harness `9f3385f` (from `ble-rx-aa`),
`ed8412f`, `c99d5f7`, `4e701b1`. Area, timing and activity: `docs/Comparison/RX_BRANCH_COMPARISON.md` § 13.

---

## Purpose

This report records the evidence that replacing the 8 `btle_rx_core` of `btle_rx` (one Access Address
search, one scrambler, one CRC24 and one state machine per sampling phase) by one
`search_unique_bit_sequence_shared` (`ble-rx-aa`) and one `rx_decoder_shared`:

1. **changes no output**: per phase and on every clock, `btle_rx` receives from its decoders what it
   received from the 8 cores, in both configurations of the detector;
2. **needs no condition outside `btle_rx`**: the property it relies on, the order of the phases, is a
   property of `btle_rx` itself, proved.

## 1. The change

| | `ble-rx-dm` | `ble-rx-shared` |
|---|---|---|
| Demodulator | `gfsk_demodulation_shared` | the same |
| Access Address search | 8 × `search_unique_bit_sequence` (inside the cores) | 1 × `search_unique_bit_sequence_shared` (`ble-rx-aa`; `RX_ADV_AA_ONLY=1`: the automaton) |
| Scrambler, CRC24, state machine | 8 × (inside the cores) | **1 × `rx_decoder_shared`**: one copy of the logic, the state of 8 phases |
| Packet RAMs, payload-length and CRC stores, CRC selection | 8, unchanged | the same |

`rx_decoder_shared.v` registers the bit of a phase (clock `t`), computes in `t+1` the three clocks
`E_t+1 … E_t+3` of the original from the phase's stored state (the state machine of `btle_rx_core`
transcribed as a function, applied three times, the scrambler and the CRC as functions), writes the state
back into a ring of 8 × 54 bits that rotates by one entry per bit, and shows the pulses in `t+3` through
two shared registers. Each phase keeps its own octet register, written at `E_t+1` and `E_t+3` as in the
original, because `serial_in_ram_out` writes it into the phase's packet RAM on every clock. The payload
length and `crc_ok` are shared: `btle_rx` uses them only with `payload_length_valid` and `decode_end`.

Files: `verilog/rx_decoder_shared.v` (new), `verilog/search_unique_bit_sequence_shared.v` (from
`ble-rx-aa`), `verilog/btle_rx.v` (no `btle_rx_core`), `btle_phy.v` and `btle_controller.v`
(`RX_ADV_AA_ONLY`, as on `ble-rx-aa`), the file lists. `btle_rx_core.v` is unchanged and still serves
`btle_rx_core_tb`.

## 2. Evidence

Every run records its commit, tools and inputs, keeps its logs, and refuses to overwrite a label. The
campaign's exit codes and logs: [`results/validation/shared-campaign/`](../../results/validation/shared-campaign/summary.txt).

### 2.1 The order of the phases (formal)

`scripts/validation/formal_shared/run_formal_shared.sh shared-formal`, task `order`
([`results/validation/shared-formal/formal_shared/`](../../results/validation/shared-formal/formal_shared/result.txt)):
`btle_rx`'s phase counter feeding the working tree's `gfsk_demodulation_shared`, every input free
(I, Q, the sample valid, `rst`, the decoder restart). Proved, **unbounded** (k-induction): the 8 bit
valids are one-hot, and every bit delivered since the last restart is of the phase after the previous
one. The helper invariant: the samples in flight (capture, E1, E2, the output) are of consecutive
phases, ending at the counter.

### 2.2 The decoder ≡ the 8 decoding chains (formal)

The same run, task `prove`: `shared_miter.sv` holds the 8 `btle_rx_core` of `ble-rx-dm`
(`EXTERNAL_DEMOD = 1`, their own searches, scramblers, CRCs and state machines, taken from `38755a0`) and
`rx_decoder_shared` fed the same bits, bit valids and hit flags (the reference's: the search is proved on
`ble-rx-aa`), in `btle_rx`'s environment (its phase counter and the shared demodulator's valid timing).
Free on every clock: the sample valid, every phase's bit, `rst`, the decoder restart, the Access Address,
the channel number and the CRC seed. Property: per phase, the octet on every clock, `octet_valid`,
`payload_length_valid` and with it the payload length, `decode_end` and with it `crc_ok`.

| Task | Result |
|---|---|
| `prove`: **unbounded** (k-induction, depth 2, bitwuzla) with the helper invariants | **PASS**, in seconds |
| `bmc`: 30 clocks from reset, without the invariants | **PASS** |
| non-vacuity: 7 mutants of `rx_decoder_shared.v` | **7/7 make the proof fail**: `reset_keeps_outputs` with a counterexample from reset, the other 6 by a failing induction step; their concrete failing traces come from the lockstep (§ 2.3) |

The helper invariants, proved like the property: the order of the phases not yet written to the ring
(as § 2.1), from the phase of the last write; the two output stages are the last writes; before the first
write since a restart every entry is the reset state; each reference phase at rest equals its ring entry
(the entry `(last write − phase) mod 8`) and is well formed (state not 3; IDLE with its fields cleared; no
pending payload-length or end-of-packet condition), with its octet equal to the decoder's; the phase whose
bit is registered has advanced its scrambler; the phases in the two output stages equal their entry once
the remaining clocks of the state machine are applied, and their pulses equal the output registers.

### 2.3 Clock-by-clock lockstep of `btle_rx`

`scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh` (adapted from `ble-rx-aa`'s
`rx_aa_lockstep`), [`results/validation/shared/`](../../results/validation/shared/): the reference
`btle_rx` (every receiver module of the reference revision, renamed) and `ble-rx-shared`'s run side by side;
on every clock the testbench compares every output (`hit_flag`, `decode_run`, `decode_end`, `crc_ok`,
`best_phase`, `payload_length`, `pdu_octet_mem_data` at a random read address) and, per phase, the hit, the
octet (on every clock), `octet_valid`, `payload_length_valid` with the payload length, `decode_end` with
`crc_ok`. Stimulus: the three packets of the Python model between noise; samples on every clock, every other
clock or at random; resets, also in mid-packet; decoder restarts forced in both designs at random; the
Access Address per segment the packet's, a random one or 0, and the channel number and CRC seed the
packet's or random, both also changed in mid-segment.

| Campaign | Runs | Compared over |
|---|---|---|
| `line`, against corrected `master` | **60/60** | 25 481 557 clocks, 17 575 367 samples, 17 435 phase hits, 103 790 phase octets, 12 973 payload lengths, 1 245 phase decode ends, 419 packets with a correct CRC, 1 695 resets, 34 033 forced restarts, 3 224 random configurations |
| `line`, against `ble-rx-dm` | **60/60** | the same stimulus: 103 827 phase octets, 1 244 phase decode ends, 418 correct CRCs |
| `adv` (`RX_ADV_AA_ONLY = 1`, the advertising address), against corrected `master` | **60/60** | 25 399 407 clocks, 11 848 phase hits, 83 244 phase octets, 62 phase decode ends |

Mutation check: 7 mutants, each run on packets decoded to the end (example 2 in `line`; the advertising
packet with forced restarts 128 times rarer in `adv`): the state of the wrong ring entry; the pulses one
register short; a hit that does not restart the CRC; a restart that does not clear the first output
register; the pulses taken after they are cleared (`f2`/`f3` swapped); the scrambler not advanced; the
octet not cleared at `E_t+3`. **7/7 caught** in each of the three campaigns.

A first version of the mutation check ran on the advertising packet with the default restarts: the long
packet then never completes (0 phase decode ends), and 4 mutants of the end of a packet were not caught; one
mutant (`p3_v` alone left out of the reset) was equivalent. The check was corrected before the campaign:
packets decoded to the end, and a mutant that changes behaviour.

### 2.4 The product audit's matrix, lint

| Check | Result |
|---|---|
| The 270-case matrix against `fca6ac6` (`scripts/validation/run_rx_regression.sh`) | **270/270** ([`shared-matrix`](../../results/validation/shared-matrix/)) |
| The same with `RX_ADV_AA_ONLY = 1` | 220 PASS, **50 ERROR: the 50 data-channel cases the reference receives** (examples 1 and 2, `btle_rx_tb` 25, `btle_controller_tb` 25), as on `ble-rx-aa` ([`shared-matrix-adv`](../../results/validation/shared-matrix-adv/)) |
| Lint gate, Verilator 5.020 `--lint-only --Wall`, warnings fatal | **2/2 configurations** (`RX_ADV_AA_ONLY` 0 and 1), 12 reviewed exceptions, none new ([`shared-lint`](../../results/validation/shared-lint/)) |
| Gate-level lockstep of the controller (the activity runs of § 13.4) | every output identical to corrected `master` on every clock, in the 5 scenarios, both configurations |
| The repository's test suite on a clean clone of `4e701b1` | **34 tests, OK** (2 skipped: they need `REGRESSION_VECTORS`) |

## 3. What is not claimed

- **Not proved on FPGA or silicon**; no board test.
- **The formal proof isolates the decoder**: it takes the hit flags of the reference's searches; the
  shared search is proved on `ble-rx-aa`, and the whole `btle_rx` (search and decoder together) is checked
  by the lockstep and the matrix.
- **The advertising campaign completes few packets** (62 phase decode ends): the long advertising packet
  seldom ends between forced restarts; its mutation check runs with rarer restarts, and the proof (§ 2.2)
  does not depend on the address.
- **Area, timing and activity** are in `RX_BRANCH_COMPARISON.md` § 13, with their limits; the ring costs
  activity, and an indexed bank, measured as the alternative, halves that cost for part of the area.

## 4. Reproducing

From WSL, at the root of `ble-rx-shared`, with the OSS CAD Suite 2026-09-07, Verilator 5.020 for the lint
gate, and Python 3.11 with numpy 2.4.6:

```bash
scripts/validation/formal_shared/run_formal_shared.sh <label>
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> line 20 200 fca6ac6
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> adv 20 200 fca6ac6
scripts/validation/rx_shared_lockstep/run_rx_shared_lockstep.sh <label> line 20 200 ble-rx-dm
scripts/validation/run_rx_regression.sh <label>-matrix fca6ac6
DUT_DEFAULTS="$ADV" scripts/validation/run_rx_regression.sh <label>-matrix-adv fca6ac6
python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```
