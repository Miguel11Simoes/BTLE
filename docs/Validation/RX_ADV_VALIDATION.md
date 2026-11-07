# Validation of the packet memory for Legacy Advertising (`ble-rx-adv`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-rx-adv`, cut from `ble-rx-shared` (`2b1fd10a`)  
**Base:** tag `upstream-baseline` (`8540186`); reference: `ble-rx-shared` and corrected `master` (`fca6ac6`)  
**Date:** 2026-10-18  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `198d9a6d` (no RTL changed after it); harness `2064b38f`, `103d9d37`.
Area, timing and activity: `docs/Comparison/RX_BRANCH_COMPARISON.md` § 14.

---

## Purpose

This report records the evidence that the two new parameters of `btle_rx`, which reorganise the memory
where the receiver keeps the octets of each sampling phase:

| Parameter (default 0 = the original) | 1 |
|---|---|
| `RX_PDU_ADV_DEPTH` | the 8 per-phase packet RAMs hold **64 words** instead of 512 |
| `RX_PDU_ONE_RAM` | **one RAM for the 8 phases** (`rx_pdu_ram_shared`), the words `{phase, word}` |

1. **change nothing the receiver delivers on advertising traffic**: every output of `btle_rx` but the
   packet RAM's on every clock, and the packet RAM's read on the words of the packet;
2. **differ from the original only where the original's content is not defined**: the words at and
   beyond each phase's write counter, and the one read after a change of `best_phase`. The contract
   is stated in `verilog/rx_pdu_ram_shared.v` and proved.

The configuration of the product is the three restrictions together, `RX_ADV_AA_ONLY = 1` (§ 12 of the
comparison), `RX_PDU_ADV_DEPTH = 1` and `RX_PDU_ONE_RAM = 1`: a receiver of Legacy Advertising.

## 1. The change

The longest Legacy Advertising packet the decoder writes is the 2-octet header, 37 octets of payload
and the 3-octet CRC: **42 octets**. The original gives each of the 8 phases a RAM of 512 octets
(`serial_in_ram_out`, address `NUM_BIT_PAYLOAD_LENGTH + 1` bits): 32 768 bits, of which a Legacy
Advertising packet uses 42 octets per phase.

- **`RX_PDU_ADV_DEPTH = 1`**: the 8 RAMs and their write counters of 6 bits; `btle_rx` reads the low 6
  bits of `pdu_octet_mem_addr` (the high 3 are declared unused). 8 × 512 bits.
- **`RX_PDU_ONE_RAM = 1`**: one `sdpram_two_clk` of 8 × 2^W words (W = 6 with the first parameter, 9
  without), addressed `{phase, word}`. Each phase keeps its write counter (reset by `rst` or its hit,
  advanced by its `octet_valid`, as `serial_in_ram_out`); **one write port serves the 8 phases**
  because the decoder gives an `octet_valid` to one phase per clock at most (`rx_decoder_shared`'s one
  output stage, proved one-hot on `ble-rx-shared`). The read address is `{best_phase, word}`,
  registered on `clkb`, where the original read 8 RAMs and selected the phase after them.

What can differ, by construction:

- `serial_in_ram_out` writes on **every** clock (`write_enable` tied to 1), so the word at a phase's
  counter always shows the octet being assembled, and words above it what earlier writes left. The
  one RAM writes only valid octets. The words **below** the counter, the packet, are equal, while the
  counter is below 2^W: at 64 a 64-word `serial_in_ram_out` writes the octet being assembled over
  word 0.
- After a change of `best_phase`, the one read registered with the old phase shows the old phase's
  word.
- `best_phase` (baseband clock) enters the read-address register (AXI clock `clkb`); in the original
  it entered the multiplexer after the 8 registered reads. Both are the same unsynchronised crossing,
  safe while `best_phase` is stable, which it is while the link layer reads (below).

What the rest of the controller reads: `btle_ll`, after `decode_end`, reads addresses 0 to `len`
(`len` = 2 + payload length + 3, which is the phase's counter) and strobes the octets of words 0 to
`len` − 1, all below the counter (the first octet it latches comes from its previous address and goes
out with the strobe low). It reads within `len` + 5 AXI clocks, and `best_phase` changes only at a
decode end. The raw read port is also visible as the bare-metal output `ext_rx_pdu_octet_mem_data`
and as bits 7:0 of register 49; `firmware/btle_ll.c` reads bits 16 and 15:8 of register 49 only.

Files: `verilog/rx_pdu_ram_shared.v` (new), `verilog/btle_rx.v` (the two parameters, the generate of
the packet memory), `btle_phy.v` and `btle_controller.v` (the parameters passed down), the file lists.

## 2. Evidence

Every run records its commit, tools and inputs, keeps its logs, and refuses to overwrite a label. The
campaign's exit codes and logs: [`results/validation/adv-campaign/`](../../results/validation/adv-campaign/summary.txt).

### 2.1 The packet memory ≡ the 8 RAMs, under the contract (formal)

`scripts/validation/formal_adv/run_formal_adv.sh adv-formal`
([`results/validation/adv-formal/formal_adv/`](../../results/validation/adv-formal/formal_adv/result.txt)):
`pdu_miter.sv` holds the original, **8 `serial_in_ram_out` of 512 words** read at the full address with
the phase selected after the reads (`btle_rx`'s multiplexer), and the memory of `ble-rx-adv`, read at the
low W bits as `btle_rx` does. Free on every clock: each phase's reset (`rst` | hit), the 8 octets,
`octet_valid` (assumed one phase per clock at most), the read phase and the read address. Every RAM is
abstracted by `sdpram_watch.sv`, which keeps the one word at a free constant address, tied on both sides
to one watched (phase, word); a read of any other address returns a free value. The watched address is
arbitrary, so the proof covers every address.

Property: the read registered at a clock, of the watched word, with the read phase unchanged at that
clock, is equal on both sides when the word is below the reference phase's write counter and that
counter is below 2^W. Helper invariants: every counter of the DUT is the reference's modulo 2^W, and
the watched word is equal on both sides under the same condition.

| Task | Result |
|---|---|
| `one`: `rx_pdu_ram_shared`, 8 × 64 words (`RX_PDU_ADV_DEPTH = 1`, `RX_PDU_ONE_RAM = 1`) | **PASS, unbounded** (k-induction, depth 2, bitwuzla; base case from reset), 23 s |
| `depth`: 8 `serial_in_ram_out` of 64 words (`RX_PDU_ADV_DEPTH = 1`) | **PASS, unbounded** |
| `one512`: `rx_pdu_ram_shared`, 8 × 512 words (`RX_PDU_ONE_RAM = 1`) | **PASS, unbounded** |
| non-vacuity: 5 mutants of `rx_pdu_ram_shared.v` and 2 of the contract | **7/7 make the proof fail**: the counter not reset by the hit with a counterexample from reset; the write in the wrong phase's words, the read without the phase, every counter advanced by any octet, a write on every clock, the contract one counter value wider (`depth`: at 64, word 0 is overwritten) and without the condition on the read phase, by a failing induction step |

A bounded check from reset without the invariants was dropped: it took minutes per clock with both
solvers tried (bitwuzla, yices), and adds nothing to the induction proofs, whose base case starts from
reset; the concrete failing traces of the RTL mutants come from the lockstep (§ 2.2).

### 2.2 Clock-by-clock lockstep of `btle_rx`

`scripts/validation/rx_adv_lockstep/run_rx_adv_lockstep.sh` (adapted from `rx_shared_lockstep`),
[`results/validation/adv/`](../../results/validation/adv/): the reference `btle_rx` (every receiver
module of the reference revision, renamed) and `ble-rx-adv`'s in one configuration, side by side. On every
clock the testbench compares, **exactly**, `hit_flag`, `decode_run`, `decode_end`, `crc_ok`,
`best_phase`, `payload_length` and, per phase, the hit, the octet, `octet_valid`, `payload_length_valid`
with the payload length, `decode_end` with `crc_ok`; and `pdu_octet_mem_data` **under the contract**: the
read of a clock is compared when `best_phase` did not change at that clock, the read address is below
the reference phase's write counter (mirrored in the testbench: reset by `rst` or the phase's hit,
advanced by its `octet_valid`) and that counter is below the DUT's depth. The read address is drawn below
64 in 3 clocks of 4. Stimulus as on `ble-rx-shared`: the three packets of the Python model between noise,
samples on every clock, every other clock or at random, resets also in mid-packet, decoder restarts
forced in both designs at random; in `line` mode the Access Address per segment the packet's, a random
one or 0, the channel and CRC seed the packet's or random, also changed in mid-segment.

| Campaign (20 seeds × 3 packets, 200 segments) | Runs | Compared over | Mutants |
|---|---|---|---|
| `adv` (`RX_ADV_AA_ONLY = 1`), **one** RAM, against `ble-rx-shared` | **60/60** | 25 487 072 clocks, 17 682 852 samples, 11 903 phase hits, 84 095 phase octets, 2 234 decode ends; **755 418 packet-RAM reads** compared (754 862 of a non-zero word); not compared: 19 after a change of `best_phase`, 24 731 635 beyond the packet, 0 with a counter at the depth | **7/7** |
| `adv`, one RAM, against corrected `master` | **60/60** | the same totals | **7/7** |
| `adv`, **depth** (8 RAMs of 64 words), against `ble-rx-shared` | **60/60** | the same totals | **3/3** |
| `line` (any Access Address), one RAM, against `ble-rx-shared` | **60/60** | 25 517 383 clocks, 19 285 phase hits, 113 006 phase octets, 1 317 phase decode ends, 426 packets with a correct CRC; 1 119 942 reads compared, 531 after a change of `best_phase` | **7/7** |
| `line`, depth | **60/60** | 18 074 phase hits, 105 552 phase octets; 1 112 316 reads compared | **3/3** |
| `line`, one RAM of 8 × 512 words (`RX_PDU_ONE_RAM = 1` alone) | **60/60** | 19 317 phase hits, 110 447 phase octets; 1 120 459 reads compared | **6/6** |

Each campaign generates its packets with the Python model, whose channel noise is not seeded
(`python/btlelib.py`): the `line` campaigns differ by that in their totals; the three `adv` campaigns
gave the same totals. The counter of the phase read never reached 64 in any campaign (0 reads skipped
for it): the packets of the model are 37, 17 and 5 octets (payloads of 32, 12 and 0 octets).

The mutants (each run on the advertising packet, with forced restarts 128 times rarer, so packets are
written to the end): the read address one bit off; 32 words per phase (`depth`, `one`); a phase's RAM
(`depth`) or counter (`one`, `one512`) not restarted by its hit; the octet written in the wrong phase's
words; the read without the phase; every counter advanced by any phase's octet; a write on every clock,
as `serial_in_ram_out` (idle clocks write 0 at word 0 of phase 0). **Every mutant caught** in every
campaign.

### 2.3 The product audit's matrix, lint, the controller at gate level

| Check | Result |
|---|---|
| The 270-case matrix against `fca6ac6`, the product configuration (`RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM` = 1) | 220 PASS, **50 ERROR: the 50 data-channel cases the reference receives**, case by case the same as `ble-rx-shared`'s advertising configuration ([`adv-matrix-adv-one`](../../results/validation/adv-matrix-adv-one/)) |
| The same with `RX_ADV_AA_ONLY = 1` and `RX_PDU_ADV_DEPTH = 1` | the same 220 + 50 ([`adv-matrix-adv-depth`](../../results/validation/adv-matrix-adv-depth/)) |
| The same with `RX_PDU_ONE_RAM = 1` alone (512 words per phase, any Access Address) | **270/270** ([`adv-matrix-one512`](../../results/validation/adv-matrix-one512/)) |
| Lint gate, Verilator 5.020 `--Wall`, warnings fatal | **8/8 configurations** (`RX_ADV_AA_ONLY`, `RX_PDU_ADV_DEPTH`, `RX_PDU_ONE_RAM`), 12 reviewed exceptions, none new ([`adv-lint`](../../results/validation/adv-lint/)) |
| Gate-level lockstep of the controller against corrected `master` (the activity runs of § 14.4), depth | every output and register read identical on every clock, 5 scenarios |
| The same, one RAM, every output compared | **fails at cycle 21 410** of `rx` and `mixed`, before the first packet: `ext_rx_pdu_octet_mem_data` reads `0x80` (the octet being assembled at the counter) in `master`, `0x00` in the one RAM ([`ble-rx-adv-one-strict`](../../results/power/rx-adv/ble-rx-adv-one-strict/runs.txt)): the contract's difference, as expected |
| The same, one RAM, `PDU_CONTRACT=1` (the raw read port and bits 7:0 of register 49 left out) | every other output on every clock and every other register read identical, **the 17 packets of `rx` and 9 of `mixed` read word by word through register 40 identical**, 5 scenarios |
| The repository's test suite on a clean clone of `103d9d37` | **34 tests, OK** (2 skipped: they need `REGRESSION_VECTORS`) |

## 3. What is not claimed

- **Not proved on FPGA or silicon**; no board test.
- **Data-channel packets** are not received in the product configuration (`RX_ADV_AA_ONLY = 1`, § 12);
  and `RX_PDU_ADV_DEPTH = 1` alone would keep only packets of at most 63 octets (a data packet with up to
  58 octets of payload): it is meant for advertising only.
- **The raw read port is not the original's outside the packet** with `RX_PDU_ONE_RAM = 1`: the words at
  and above each phase's counter, and one read after a change of `best_phase`. Nothing in the
  controller or the firmware consumes them (§ 1); an external host using the bare-metal PHY interface
  must read only the words of the packet, after `decode_end`, as `btle_ll` does.
- **The formal proof isolates the packet memory**: it assumes one `octet_valid` per clock (proved on
  `ble-rx-shared`) and one clock for writes and reads; the whole `btle_rx` is checked by the lockstep,
  the controller by the matrix and the gate-level runs. The clock-domain crossing of `best_phase` into
  the read address is argued (§ 1), not proved.
- **RAM macro areas** are OpenRAM's (FreePDK45), not a foundry compiler's; their timing is not in the
  static timing analysis (the flow has no timing model for the macros).

## 4. Reproducing

From WSL, at the root of `ble-rx-adv`, with the OSS CAD Suite 2026-09-07, Verilator 5.020 for the lint
gate, and Python 3.11 with numpy 2.4.6 (`ADV`, `DEPTH` and `ONE`: the three parameters set to 1 as
defaults of `btle_rx.v`, `btle_phy.v`, `btle_controller.v`, and `search_unique_bit_sequence_shared.v` for
`RX_ADV_AA_ONLY`, as `file:PARAM=1` items):

```bash
scripts/validation/formal_adv/run_formal_adv.sh <label>
for c in one depth; do scripts/validation/rx_adv_lockstep/run_rx_adv_lockstep.sh <label> adv $c 20 200 ble-rx-shared; done
scripts/validation/rx_adv_lockstep/run_rx_adv_lockstep.sh <label> adv one 20 200 fca6ac6
for c in one depth one512; do scripts/validation/rx_adv_lockstep/run_rx_adv_lockstep.sh <label> line $c 20 200 ble-rx-shared; done
DUT_DEFAULTS="$ADV $DEPTH $ONE" scripts/validation/run_rx_regression.sh <label>-matrix-adv-one fca6ac6
DUT_DEFAULTS="$ADV $DEPTH" scripts/validation/run_rx_regression.sh <label>-matrix-adv-depth fca6ac6
DUT_DEFAULTS="$ONE" scripts/validation/run_rx_regression.sh <label>-matrix-one512 fca6ac6
VERILATOR=/usr/bin/verilator python3 scripts/validation/run_lint.py --output results/validation/<label>-lint
```
