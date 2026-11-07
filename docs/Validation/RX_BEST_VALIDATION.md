# Validation of the packed packet RAM (`ble-rx-best`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-best`, cut from `ble-rx-min` (`8e63e5ef`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: `ble-rx-shared` and corrected `master` (`fca6ac6`)  
**Date:** 2026-10-19  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `3d92ea80` (no RTL changed after it); harness `a3be8906`, the mutant patterns fixed in `10a6edc6`.
Area, timing and activity: `docs/Comparison/RX_BRANCH_COMPARISON.md` § 16.

---

## Purpose

`ble-rx-best` is `ble-rx-min` (§ 15 of the comparison) with its single-port packet RAM **sized to the
42 octets of Legacy Advertising**: each of the 8 phases owns 42 words, packed at `phase × 42 + word`,
in one macro of **336 × 8** instead of 512 × 8 (a parameter, `RX_PDU_PACKED`, default 1 on the branch).
This report records the evidence that the receiver delivers what `ble-rx-min` delivers, under the same
contract (§ 15) with the counter limit at 42 words, and that nothing else changes.

## 1. The change

- `verilog/rx_pdu_ram_1rw.v`, parameter `PHASE_WORDS` (0: the `{phase, word}` of `ble-rx-min`):
  - the macro address of a word is `phase × PHASE_WORDS + word` (a multiply by a constant and an
    add), and the macro has `NUM_PHASE × PHASE_WORDS` words;
  - **a write beyond a phase's words is dropped**: it would land in the next phase's. A Legacy
    Advertising packet has 42 octets at most (2 of header, 37 of payload, 3 of CRC), so its writes
    are words 0 to 41; only a longer decode (noise taken for a packet) reaches word 42, beyond the
    contract;
  - **each phase holds the word of its octet** with the octet (`held_word`, at its `octet_valid`). In
    `ble-rx-min` the write took its word from the counter when it was served: a hit that resets the
    counter while the write waits (up to about 80 clocks of `clkb`) sent it to word 63 of the same
    phase, which no read in the contract sees; packed, word 63 of phase *k* is word 21 of phase *k* + 1.
    The proof found it (§ 2.1).
- `verilog/btle_rx.v`, `btle_phy.v`, `btle_controller.v`: `RX_PDU_PACKED` (with `RX_PDU_1RW` and
  `RX_PDU_ADV_DEPTH` at 1: `PHASE_WORDS` = 42).
- `verilog/sdpram_one_clk.v`: `DEPTH`, the number of words (default 2^`ADDRESS_WIDTH`, as before);
  `scripts/area/summarize_area.py` counts `DATA_WIDTH × DEPTH` bits.

The contract is § 15's, with the counter limit **42** (a counter of 42 included: words 0 to 41)
instead of 63.

**The macro.** OpenRAM 1.2.48 builds the layout of a 336 × 8 macro but stops in its characterization:
the timing stimulus probes the address of all ones, which does not exist. `run_openram.sh
LAYOUT_ONLY=1` (`openram_layout.py`) writes the netlist, GDS and LEF without it; it gives the full
flow's sizes for 256 × 8 (6 979.1 µm²) and 512 × 8 (10 703.9 µm²), and 336 × 8 is **8 116.5 µm²**
([`openram-rx-best`](../../results/area/openram-rx-best/summary.md)). That macro has no timing or
power model, and its function at transistor level is not simulated (no macro here has DRC/LVS).

## 2. Evidence

The campaign's exit codes and logs: [`results/validation/best-campaign/`](../../results/validation/best-campaign/summary.txt).

### 2.1 Formal

| Check | Result |
|---|---|
| `formal_adv`, task `best1rw` ([`best-formal`](../../results/validation/best-formal/formal_adv/result.txt)): `rx_pdu_ram_1rw` with 42 packed words per phase against 8 `serial_in_ram_out` of 512 words, `pdu_1rw_miter.sv` with `PACKED` | **PASS, unbounded** (k-induction) |
| … `min1rw` (the unpacked memory, with the held word), and the tasks of § 14 | `one`, `depth`, `one512`, `min1rw`: **PASS**, unbounded |
| non-vacuity | **24/24 mutants** break the proof (with `packed_stride_41`, `packed_beyond_not_dropped`, `packed_word_not_held`) |

The first proof of the packed memory failed its induction: a write waiting while a hit reset its
phase's counter was served at word 63, packed into the next phase. The held word fixes it, and the
mutant that takes the word from the counter again (`packed_word_not_held`) breaks the proof.

### 2.2 Clock-by-clock lockstep of `btle_rx`

`scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh`, configuration `best`
([`results/validation/best/`](../../results/validation/best/)), as § 15's (samples never in consecutive
clocks, `clkb` equal or at 103 MHz, read bursts, the macro's rules and the write count checked), the
reads compared while the counter is 42 or below.

| Campaign (20 seeds × 3 packets, 200 segments) | Runs | Packet-RAM reads compared | Mutants |
|---|---|---|---|
| `adv`, `clkb` = `clk`, against `ble-rx-shared` | **60/60** | 1 241 598 | 17/17 |
| `adv`, `clkb` = `clk`, against corrected `master` | **60/60** | 1 241 598 | 17/17 |
| `adv`, `clkb` at 103 MHz, against `ble-rx-shared` | **60/60** | 7 975 453 (2 651 lost to a forced write) | 15/15 |
| `line`, `clkb` = `clk`, against `ble-rx-shared` | **60/60** | 1 893 257 (5 107 past the 42 words, not compared) | 16/16 |
| `line`, `clkb` at 103 MHz, against `ble-rx-shared` | **60/60** | 12 217 655 (32 909 past the 42 words) | 14/14 |

The mutants of § 15, with `write_address_off_by_one` on the held word, and three of the packing:
`word_not_held` (the word from the counter when served), `packed_not_packed` (the 336 words addressed
`{phase, word}`), `packed_stride_41` (phases 41 words apart; `adv` only: it shows when a phase writes its
word 41, which the packet of the mutation run, 37 octets, never does, and the proof rejects it).

### 2.3 The product audit's matrix, lint, the controller at gate level

| Check | Result |
|---|---|
| The 270-case matrix against `fca6ac6`, the defaults of `ble-rx-best` | 220 PASS, **50 ERROR: the 50 data-channel cases**, case by case those of `ble-rx-shared` (advertising only) ([`best-matrix-product`](../../results/validation/best-matrix-product/)) |
| The same, `RX_ADV_AA_ONLY = RX_PDU_ADV_DEPTH = 0`: full function (the packing is off: 512 words per phase) | **270/270** ([`best-matrix-full-1rw`](../../results/validation/best-matrix-full-1rw/)) |
| The same with every parameter at 0 | **270/270** ([`best-matrix-zero`](../../results/validation/best-matrix-zero/)) |
| Lint gate, Verilator 5.020 `--Wall` | **32/32 configurations** (with `RX_PDU_PACKED`), 12 reviewed exceptions, none new ([`best-lint`](../../results/validation/best-lint/)) |
| Gate-level lockstep of the controller against corrected `master`, `PDU_CONTRACT=1` | every compared output on every clock and every register read identical, **the 17 packets of `rx` and 9 of `mixed` read word by word through register 40 identical**, 5 scenarios ([`rx-best`](../../results/power/rx-best/ble-rx-best/summary.md)) |
| The repository's test suite on a clean clone of `10a6edc6` | **35 tests, OK (2 skipped: they need a saved matrix)** |

## 3. What is not claimed

Those of `RX_MIN_VALIDATION.md` § 3, and:

- **The 336 × 8 macro is a layout without characterization**: its area is OpenRAM's; its timing, power
  and transistor-level function are not checked (OpenRAM cannot write its timing stimulus).
- **A decode of more than 42 octets** (noise taken for a packet) keeps only its first 42 (63 on
  `ble-rx-min`); no Legacy Advertising packet has more.

## 4. Reproducing

From WSL, at the root of `ble-rx-best` (`ZADV`, `ZDEPTH`, `ZONE`, `NO1RW` as in `RX_MIN_VALIDATION.md` § 4):

```bash
LAYOUT_ONLY=1 scripts/area/run_openram.sh <label> sram_1rw_8x336 sram_1rw_8x256 sram_1rw_8x512
scripts/validation/formal_adv/run_formal_adv.sh <label> ble-rx-shared
for m in adv line; do for k in sync async; do
  scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh <label> $m best $k 20 200 ble-rx-shared; done; done
scripts/validation/rx_min_lockstep/run_rx_min_lockstep.sh <label> adv best sync 20 200 fca6ac6
scripts/validation/run_rx_regression.sh <label>-matrix-product fca6ac6
DUT_DEFAULTS="$ZADV $ZDEPTH" scripts/validation/run_rx_regression.sh <label>-matrix-full-1rw fca6ac6
DUT_DEFAULTS="$ZADV $ZDEPTH $ZONE $NO1RW" scripts/validation/run_rx_regression.sh <label>-matrix-zero fca6ac6
VERILATOR=/usr/bin/verilator python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```
