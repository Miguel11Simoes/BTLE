# Validation of the smallest receiver of Legacy Advertising (`ble-rx-min`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-min`, cut from `ble-rx-adv` (`cf3d4ca9`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: `ble-rx-shared` and corrected `master` (`fca6ac6`)  
**Date:** 2026-10-19  
**Author:** Miguel Simões  
**Status:** executed. RTL commits `89549adc` (the demodulator of `ble-rx-dmult`), `c2ea1118` and
`a0e3fe47` (the single-port packet RAM; no RTL changed after it); harness `642870f9`, `552c78a0`,
`2f96ba64`, `d212e2be`, `accf3cb2`. Area, timing and activity: `docs/Comparison/RX_BRANCH_COMPARISON.md` § 15.

---

## Purpose

`ble-rx-min` is `ble-rx-adv` in its product configuration (§ 14 of the comparison: the advertising
address only, one packet RAM of 8 × 64 words) with the two remaining levers that cost no function:

| Lever | What | Default on `ble-rx-min` |
|---|---|---|
| The demodulator of `ble-rx-dmult` | the two products of a sample on **one multiplier**, in two clocks | always (not a parameter) |
| `RX_PDU_1RW` | the one packet RAM on a **single-port (1RW) macro** instead of a two-port (1RW1R) one | 1 |

and the defaults of `RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM` and `RX_PDU_1RW` set to 1:
synthesised as it is, the branch is the receiver of Legacy Advertising. This report records the
evidence that:

1. the receiver delivers on advertising traffic what `ble-rx-shared` and corrected `master` deliver,
   on every clock, every output but the raw read port of the packet RAM, and that port on the words
   of the packet (the contract of § 14, with a latency and one exception of its own, § 1.2);
2. every parameter at 0 is the original memory, and `RX_PDU_1RW = 1` with full function (any
   address, 512 words per phase) receives every packet the reference receives.

## 1. The change

### 1.1 One multiplier

`verilog/gfsk_demodulation_shared.v` of `ble-rx-dmult` (`f00bd9e`), unchanged; its validation is
`RX_DMULT_VALIDATION.md` (on `ble-rx-dmult`): the two products `old_i·new_q` and `new_i·old_q` in
two consecutive clocks on one multiplier, exact under its contract, **a sample at most every second
clock**, which `clock_domain_conversion_iq` gives the controller (proved there). Its proof
(`formal_dmult`) and the proof of the order of the phases on which the shared decoder relies
(`formal_shared`, task `order`) run again here, on this demodulator (§ 2.1).

### 1.2 One single-port packet RAM

`verilog/rx_pdu_ram_1rw.v`. The RAM of `ble-rx-adv` (`rx_pdu_ram_shared`: words `{phase, word}`,
each phase's write counter) on one 1RW macro, which is written or read in a clock, not both:

- **The macro is clocked by `clkb`**, the AXI clock (100 MHz on the three boards, `FCLK_CLK0` of the
  PS, against 16 MHz for the baseband clock `clk`), so the link layer keeps its read of one clock.
- **The writes cross from `clk`**: each phase holds its octet and flips a toggle at its
  `octet_valid` (a phase writes once per 64 samples at most, 128 clocks of `clk` or more); on `clkb`
  each toggle goes through two flip-flops and makes the phase pending; the lowest pending phase writes
  its held octet at `{phase, counter − 1}`.
- **The reads take the port first.** The port reads only when the output must change (another
  address, or the word shown has changed); a write takes the clocks the reads leave free, or, after
  `WRITE_WAIT` = 64 clocks of waiting, the next clocks until none is pending (forced). A read of the
  read phase's **pending** word is served from its held octet (**the bypass**), so a write that waits
  never makes a read stale; a write arriving for the word shown, or for the word read in that clock,
  marks the output stale.
- `rst` resets the write side on `clkb` through two flip-flops; the reads go on during it.

The contract, beyond § 14's (the words below each phase's counter, while it is below 64; one read
after a change of `best_phase`):

- **Latency**: the newest word of a phase is read right **4 clocks of `clkb`** after the clock of
  `clk` that writes the original's RAM (with equal clocks; proved). With `clkb` at 103 MHz the
  lockstep allows one clock more.
- **Lost reads**: a read that needs the port in the clock of a **forced** write keeps the previous
  word that clock (`lost_q`). A forced write needs a reader that changes its address on 64 consecutive
  clocks of `clkb`; the link layer changes it for `len` + 5 clocks per packet, 48 at most.
- **`rst`**: a write still crossing when `rst` rises is dropped; `rst` resets every counter at the
  next clock of `clk`, and its word is then beyond the packet.

**The first design lost reads that a reader meets**, and the evidence found it. In the first
version the writes took the port first; the matrix of the product audit
([`min-matrix-product-first`](../../results/validation/min-matrix-product-first/)) failed 18
advertising cases: 9 configurations of example 0, the advertising packet (8 to 20 dB), in both
`btle_rx_tb` and `btle_controller_tb`; each read one PDU byte wrong. These testbenches start reading 2 clocks after `decode_end`, while the last octets of the other
phases are still crossing; a write then took the port from the read of word 0. The lockstep had not
seen it: its contract excluded the lost reads, which is what hid them. The redesign (`a0e3fe47`) gives
the reads the port, adds the bypass, and the lockstep now **checks** that a read is lost only to a
forced write; the mutant `writes_first` (the first design) is caught by that check and by the proof.

### 1.3 Files

`verilog/rx_pdu_ram_1rw.v` (new), `verilog/gfsk_demodulation_shared.v` (of `ble-rx-dmult`),
`verilog/btle_rx.v` (`RX_PDU_1RW`; the defaults), `btle_phy.v` and `btle_controller.v` (`RX_PDU_1RW`
passed down; the defaults), `search_unique_bit_sequence_shared.v` (its default of `RX_ADV_AA_ONLY`),
the file lists. The 1RW macro is modelled with the repository's `sdpram_one_clk`, as
`cos_sin_table_ram` of `ble-tx-sin8-1rw` does: the flows count it as one macro of 4 096 bits.

## 2. Evidence

Every run records its commit, tools and inputs, keeps its logs, and refuses to overwrite a label. The
campaigns' exit codes and logs: [`results/validation/min-campaign/`](../../results/validation/min-campaign/summary.txt).

### 2.1 Formal

| Check | Result |
|---|---|
| `formal_dmult` ([`min-dmult`](../../results/validation/min-dmult/formal_dmult/result.txt)): the demodulator with one multiplier ≡ `ble-rx-dm`'s, under its contract | **PASS**, unbounded at 16 bits (products abstracted) and with the real multipliers at 4 bits; `cdc_gap` PASS; without the contract it fails, as required; every mutant rejected |
| `formal_shared` ([`min-shared-formal`](../../results/validation/min-shared-formal/formal_shared/result.txt)): the order of the phases with this demodulator, and the decoder ≡ the 8 chains | **PASS**, unbounded; 7/7 mutants |
| `formal_adv`, task `min1rw` ([`min-formal`](../../results/validation/min-formal/formal_adv/result.txt)): `rx_pdu_ram_1rw` against 8 `serial_in_ram_out` of 512 words, `pdu_1rw_miter.sv` | **PASS, unbounded** (k-induction, bitwuzla) |
| … and the tasks of § 14 (`one`, `depth`, `one512`) | **PASS**, unbounded |
| non-vacuity | **21/21 mutants** make the proofs fail; of the 14 of `min1rw`, 10 also with a concrete counterexample from reset in a BMC of 14 clocks; the other 4 (a lost read taken as done, the macro read and written in one clock, the contract without the lost reads: they need a forced write, 64 clocks of waiting; a write never cleared: harmless rewrites, which the lockstep counts) fail the induction, and the lockstep catches the 3 that are of the RTL |

`pdu_1rw_miter.sv`: one clock for `clk` and `clkb` (the crossing is exercised by the lockstep, at 103
MHz); free on every clock: each phase's hit, the octets, `octet_valid`, the read phase and address.
Assumed: `rst` at start-up only, one `octet_valid` per clock (proved of `rx_decoder_shared`), the octets
of a phase 16 clocks apart or more, and none while the phase's previous write is pending. That last
one is the write's completion, argued, not proved: a pending write waits 64 clocks of `clkb` at most,
then the pending writes go one per clock, so a write is done within 64 + 16 clocks, where the next
octet of its phase is 128 clocks of `clk` away or more; the lockstep counts the writes (§ 2.2).
Properties: the macro is never read and written in one clock; a read loses the port only to a forced
write; the read of the watched word, with the read phase unchanged and not lost, equals the
reference's when the word is below the counter, the counter below 64, and the word not the newest of
its phase or its octet 3 clocks before the read or more. Invariants: the counters; where each phase's
write is in the crossing, from the clocks since its octet and whether it is done; the held octet; the
watched word once written; the output equal to the word it shows (the held octet while its write is
pending).

### 2.2 Clock-by-clock lockstep of `btle_rx`

`scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh` (adapted from `rx_adv_lockstep`),
[`results/validation/min/`](../../results/validation/min/). As § 14's, every output and per-phase signal
exactly on every clock, the packet-RAM read under the contract, and:

- **a sample never in two consecutive clocks** (the contract of the demodulator);
- `clkb` equal to `clk`, or **a clock of its own at 103 MHz** (the read address on it);
- the read address held 0 to 3 clocks, or 8 to 71, and, 1 draw in 16, **bursts** of a new address on
  every clock for 80 to 319 clocks (the writes wait, are served by the bypass and forced);
- the checks of the macro: never read and written in one clock, **a read lost only to a forced
  write**, and as many writes as the reference's octets, less those a reset drops.

| Campaign (20 seeds × 3 packets, 200 segments) | Runs | Packet-RAM reads compared | Mutants |
|---|---|---|---|
| `adv`, `clkb` = `clk`, against `ble-rx-shared` | **60/60** | 1 241 597 (not compared: 464 newest words within the latency, 2 481 lost to a forced write, 50 around a reset); 88 299 macro writes, 24 639 clocks of a forced write that took the port | **14/14** |
| `adv`, `clkb` = `clk`, against corrected `master` | **60/60** | the same | **14/14** |
| `adv`, `clkb` at 103 MHz, against `ble-rx-shared` | **60/60**, 7 975 452 reads compared, 2 652 lost to a forced write, 12/12 mutants | | **12/12** |
| `line` (any address), `clkb` = `clk` | **60/60** | 1 886 830 | **14/14** |
| `line`, `clkb` at 103 MHz | **60/60**, 12 271 392 reads compared, 12/12 mutants | | **12/12** |
| `adv`, `RX_PDU_1RW = 0` (the two-port RAM of `ble-rx-adv` with this demodulator) | **60/60** | 1 244 542 | **5/5** |

The `adv` campaigns: 37 086 290 clocks each, 17 568 181 samples, 88 419 phase octets, 2 313 decode
ends. The mutants of the single-port RAM: the counter not reset by the hit, the octet in the wrong
phase's words or one word up, the read without the phase, the held octet taken on every clock, phase
0's octet written, a write's arrival for the word shown not noticed, a lost read taken as done, a write
never cleared, the macro read and written in one clock, no bypass, the writes first (the first design);
with § 14's read address one bit off and 32 words per phase. `held_every_clock` and
`stale_not_set_on_arrival` run with `clkb` = `clk` only: with `clkb` at 103 MHz they are equivalent
(the write lands before the octet register can change; with the address held, the write marks the
word stale itself, and the one read in between is within the latency's margin).

The two first `async` campaigns ([`…-negedge`](../../results/validation/min/)) sampled the macro's
checks at the falling edge of `clkb`; with asynchronous clocks `best_phase` (on `clk`) can change
before the rising edge, and `write_now` was counted twice: 2 of the 60 `line` runs ended on the write
count (1 914 writes against 1 913 octets, 1 666 against 1 665), every clock compare having passed. The
checks now sample the rising edge (`accf3cb2`); the two campaigns ran again.

### 2.3 The product audit's matrix, lint, the controller at gate level

| Check | Result |
|---|---|
| The 270-case matrix against `fca6ac6`, the defaults of `ble-rx-min` | 220 PASS, **50 ERROR: the 50 data-channel cases the reference receives**, case by case those of `ble-rx-shared` (advertising only) ([`min-matrix-product`](../../results/validation/min-matrix-product/)) |
| The same with `RX_ADV_AA_ONLY = RX_PDU_ADV_DEPTH = 0`: full function on the single-port RAM (one RAM of 8 × 512 words) | **270/270** ([`min-matrix-full-1rw`](../../results/validation/min-matrix-full-1rw/)) |
| The same with the four parameters at 0 (the original memory, with this demodulator) | **270/270** ([`min-matrix-zero`](../../results/validation/min-matrix-zero/)) |
| Lint gate, Verilator 5.020 `--Wall`, warnings fatal | **16/16 configurations** (`RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM`, `RX_PDU_1RW`), 12 reviewed exceptions, none new ([`min-lint`](../../results/validation/min-lint/)) |
| Gate-level lockstep of the controller against corrected `master` (the activity runs of § 15.4), `PDU_CONTRACT=1` as in § 14 | every compared output on every clock and every register read identical, **the 17 packets of `rx` and 9 of `mixed` read word by word through register 40 identical**, 5 scenarios |
| The repository's test suite on a clean clone of `accf3cb2` | **35 tests, OK (2 skipped: they need REGRESSION_VECTORS)** |

## 3. What is not claimed

- **Not proved on FPGA or silicon**; no board test.
- **Data-channel packets** are not received with the defaults of the branch (`RX_ADV_AA_ONLY = 1`); the
  full-function configuration (§ 2.3) is validated by the matrix, not by the lockstep or the proof.
- **The crossing of the writes is not proved**: the proof has one clock; the asynchronous `clkb` is
  checked by the lockstep at 103 MHz against 16 MHz, in simulation (no metastability). The write's
  completion before its phase's next octet is argued and counted, not proved (§ 2.1).
- **Lost reads** exist, for a reader that changes its address on 64 consecutive clocks; the link
  layer and the testbenches of the product audit are not such readers.
- **The macros' timing and power** are not in the flows: OpenRAM areas; the energy of § 15.4 is the
  SPICE characterization of the single-port macro alone (the two-port ones were never characterized).

## 4. Reproducing

From WSL, at the root of `ble-rx-min`, with the OSS CAD Suite 2026-09-07, Verilator 5.020 for the lint
gate, and Python 3.11 with numpy 2.4.6 (`ZADV`, `ZDEPTH`, `ZONE`, `NO1RW`: the parameters set to 0 as
`file:PARAM=0` items):

```bash
scripts/validation/formal_adv/run_formal_adv.sh <label> ble-rx-shared
scripts/validation/formal_dmult/run_formal_dmult.sh <label>
scripts/validation/formal_shared/run_formal_shared.sh <label>
for m in adv line; do for k in sync async; do
  scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh <label> $m min $k 20 200 ble-rx-shared; done; done
scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh <label> adv min sync 20 200 fca6ac6
scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh <label> adv one sync 20 200 ble-rx-shared
scripts/validation/run_rx_regression.sh <label>-matrix-product fca6ac6
DUT_DEFAULTS="$ZADV $ZDEPTH" scripts/validation/run_rx_regression.sh <label>-matrix-full-1rw fca6ac6
DUT_DEFAULTS="$ZADV $ZDEPTH $ZONE $NO1RW" scripts/validation/run_rx_regression.sh <label>-matrix-zero fca6ac6
VERILATOR=/usr/bin/verilator python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```
