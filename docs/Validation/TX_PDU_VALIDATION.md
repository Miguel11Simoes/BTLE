> **Status update, 2026-10-05:** the corrected RTL and strict results are documented in [PRODUCT_VALIDATION.md](PRODUCT_VALIDATION.md) and [ASIC_READINESS.md](ASIC_READINESS.md). This document preserves historical implementation/measurement results. Its PPA values do not describe the corrected circuit; earlier equality/PASS claims are not product signoff.

# The packet buffer with one port, and exact rewrites of the transmitter (`ble-tx-pdu`)

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-pdu`, from `ble-tx-opt` (`894e9b2`)  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-10-04; corrected 2026-10-05 (the two-clock rule of a pair, § 2; the energy figure of § 6)  
**Author:** Miguel Simões  
**Status:** executed: `tests/test_tx_pdu.py` and `tests/test_vco_sin2.py` (with their mutants);
runs `tx-pdu` and `tx-pdu-one-port` of `scripts/validation/run_rx_regression.sh` (the strict
runner of the integrity audit); run `tx-pdu` of `scripts/validation/ctl_lockstep/run_ctl_lockstep.sh`,
`scripts/validation/formal_gauss/run_formal_gauss.sh` and
`scripts/validation/equiv_defaults/run_equiv_defaults.sh`; run `openram-pdu` of
`scripts/area/run_openram.sh`; run `tx-pdu` of `scripts/compare/run_compare.sh` (area, static
timing, gate-level lockstep and switching activity; `docs/Validation/BRANCH_COMPARISON.md`).
Every run was made at commit `b773316`; the commits after it change one comment of `btle_tx.v`
(`0731119`) and the documents.

---

## Purpose

With B2 and the one-port sine table of `ble-tx-sin2`, the transmitter was
estimated at 37 295 µm² (`BRANCH_COMPARISON.md` § 4.2), and 64 % of that is the
packet buffer, the one memory no branch had changed: 512 × 8 with two ports
and two clocks (23 708.0 µm²), although the transmitter reads one byte every
128 clocks and only bytes 0 to 256. This branch gives the buffer one port and
256 words plus a register, builds B2 and the memory of `ble-tx-sin2` into one
design, which had only been estimated, and rewrites five blocks of the
transmitter's logic so that they keep the same outputs on every clock. It
answers how small the transmitter gets without giving up more than B2 and
`ble-tx-sin2` already give up.

The changes come from an analysis of what was left after those two, made
before any RTL of this branch. A fixed VCO table (a ROM in logic, or a
CORDIC) was also considered; it would remove the table memory, but the COS
and SIN tables would stop being programmable, so it is not in this branch.

## 1. What the branch contains

| Part | Taken from | Files | How it is selected |
|---|---|---|---|
| Gaussian filter: B2's constant taps, the sum computed with the two positions of each tap added first | `ble-tx-table`, rewritten | `gauss_filter.v` (`gfsk_modulation.v`, `btle_phy.v` and `btle_controller.v` as on `ble-tx-table`) | `GAUSS_TABLE=1`; the default, 0, is the upstream FIR |
| VCO: the quarter sine table alone, 512 × 8 with one port, cos 0 in a register | `ble-tx-sin2`, without its change detector | `vco.v` | structural, always on |
| Packet buffer: 256 × 8 with one port on `clkb`, a register for byte 256, read on request | new | `btle_tx.v` (modules `pdu_buffer` and `pdu_buffer_ram`) | structural, always on |
| Counters of `bit_repeat_upsample`, `crc24`, `scramble` and `btle_tx` | new | those four files | structural, always on |
| Receiver, Link Layer, IQ-capture RAM, everything else | upstream | unchanged | — |

As on `ble-tx-table` and `ble-tx-opt`, B2 is a parameter that defaults to the
upstream FIR, and the branch is measured with it on
(`scripts/branch_config.sh` gives `GAUSS_TABLE=1`). The other changes are
structural, like the VCO memories of the `ble-tx-sin*` branches.

## 2. The packet buffer

Upstream writes the buffer from the processor's side: the pair (address,
data) of register 8 of the Link Layer, or of the `ext_tx_pdu_octet_mem_*`
inputs in baremetal mode, is written on **every** clock of `clkb`, the AXI
clock. The transmitter reads on `clk` (16 MHz), on every clock, and uses one
read per byte: the one of `clk_count` 127, which `octet` takes one clock
later. It reads bytes 0 to L + 1 of a packet with L payload bytes, at most
byte 256 (L ≤ 255). Here:

- **One port, 256 words, on `clkb`, and a register for byte 256.** Writes to
  addresses 0–255 go to the memory, the pair at 256 to the register, and the
  addresses above, which the transmitter never reads, are dropped. OpenRAM
  does not generate a memory of 257, 264 or 272 words in FreePDK45 (it fails
  in its timing characterisation), so 256 + 1 is the smallest buffer.
- **The pair is still written on every `clkb` clock**, except the one that
  reads, so the contents follow the processor's register as upstream's do.
- **The transmitter asks for each byte 12 clocks before it takes it.** The
  address, `bit_count` / 8 (§ 3), is set at [`clk_count`] 114, after the last
  bit of the byte before; the request is raised at 116. It toggles a
  flip-flop on `clk`; two flip-flops synchronize the toggle to `clkb`; the
  next `clkb` clock reads, and the one after puts the byte in a register on
  `clkb`, which `octet` takes at [`clk_count`] 0, as upstream takes the memory
  output. The byte is there 4 `clkb` clocks after the request at the latest,
  within the 12 `clk` clocks when `clkb` runs at 8 MHz or faster (the tests run
  it from 8 MHz to 100 MHz and on `clk` itself).

The bytes sent are upstream's whenever the packet is written before
`tx_start`, as the upstream testbenches and the controller lockstep (§ 4) do.
The repository's firmware (`firmware/btle_ll.c`) does not transmit, so a
driver written for it must do the same. A byte rewritten while it is being
read, between the request and the clock in which the transmitter takes it, may
differ: upstream reads it in the last of those clocks. Writing the addresses
the packet does not use is allowed at any time, with one condition while a
packet is sent: each pair must stay two `clkb` clocks, because a pair that
lasts one clock is not written if that clock reads. The Link Layer's register
8 keeps a pair at least three clocks (two AXI writes are at least three clocks
apart); the `ext_` pair of baremetal mode must do the same. (Corrected
2026-10-05: this paragraph first said "at any time" without the condition.)

The other place for the one-port memory, on `clk`, was tried first, in the
same analysis: there the pair has to cross from `clkb`, and a pair that lasts
one `clkb` clock (as in the upstream testbenches, which write one byte per
clock) is lost when the two clocks differ, whether it is sampled or handed
over. On `clkb` nothing crosses but the request and the byte.

## 3. The exact rewrites

Each keeps the outputs of its block on every clock inside `btle_tx`. The
figures are run `tx-pdu` (each top synthesised alone, `GAUSS_TABLE=1`), against
upstream for the first three and against the branch each part comes from for
the last two:

| Block | Upstream (or source branch) | Here | Std cells | Flip-flops | Cell area (µm²) |
|---|---|---|---:|---:|---:|
| `bit_repeat_upsample` | two 15-bit delay lines, used only through their OR | two 4-bit counters, loaded with 15 by a pulse | 94 → 61 | 36 → 14 | 225.6 → 110.1 |
| `crc24` | a 13-bit input count compared only with 40, a 5-bit CRC count, three states | one 6-bit count: up to 40, then on to 63 through the CRC (index 23 − (count − 40) = ~count[4:0]); two states | 287 → 210 | 52 → 38 | 495.3 → 359.1 |
| `scramble` | a 13-bit input count compared only with 40 and 41; a state register | a 6-bit count that stops at 41; the state is "count = 0" | 121 → 90 | 25 → 17 | 213.9 → 154.3 |
| `vco` (`ble-tx-sin2`) | the held sine pair written when it changes (a change detector and a pending flag) | written in every clock the port is free, which leaves the same contents | 408 → 349 | 76 → 63 | 740.0 → 635.7 |
| `gauss_filter` (`ble-tx-table`, `GAUSS_TABLE=1`) | distributed arithmetic: three constant tables indexed by the window | 2·Σ(b ? h : 0) − Σh, the two positions of each tap added first | 253 → 166 | 22 → 22 | 348.5 → 256.7 |

`btle_tx` itself: one bit counter for the preamble/access address and the PDU
(upstream has two), no `addr` register (the buffer is read at `bit_count` / 8,
which is upstream's `addr` in the clock whose read it uses), a 4-bit
`clk_count` (upstream's 7 bits are `bit_count[2:0]` and these 4), an 8-bit
`payload_length` without its all-ones value in IDLE, and no reset on registers
that are loaded before they are read. The comments in each file give the
argument; `crc24` relies on what `btle_tx` guarantees (at least 40 bits before
the last one, and the last bit never the first), and `scramble` on a packet of
fewer than 8 192 bits.

## 4. Evidence

| Check | What it compares | Result |
|---|---|---|
| The transmitter (`tests/test_tx_pdu.py`) | `btle_tx` against upstream's `btle_tx` (the FIR loaded with the project's taps, the full tables, the two-port buffer), every output on every clock; random packets (255 and 0 bytes first), resets that abort packets (the taps reloaded after each, as upstream's FIR loses them), CRC and channel loads, access-address changes, extra `tx_start`, table rewrites, and pairs written to the addresses the packet does not use while it is sent; `clkb` = `clk` and free at 100, 33.3, 16.1, 10 and 8 MHz; the repository's RAM models and one-port macro models of both memories | **36/36 runs, no difference**: per memory model, 2 776 037 clocks compared, 116 packets sent of 180 started (82 resets), 1 246 466 I/Q samples, 306 664 pairs written while sending; **11/11 mutants** caught (the read request too early, byte 256, a write in the reading clock, `payload_length`, `octet`, the upsampling window, the CRC order and start, the whitening start, the pairing of the taps and their sum) |
| The VCO (`tests/test_vco_sin2.py`) | the sweep against the `master` VCO; 4 × 1 000 000 clocks against the `ble-tx-sin4` VCO with random table writes | **5 120 clocks and 2 629 325 comparisons, no difference**, one-port macro model identical on every clock; **11/11 mutants** (three replaced: those of the change detector, which this VCO has not) |
| Formal (`formal_gauss`, run `tx-pdu`) | `gauss_filter` with `GAUSS_TABLE=1` against the upstream FIR loaded with the same taps, unbounded (k-induction) | **PASS**; 3/3 mutants make the proof fail |
| Defaults (`equiv_defaults`, run `tx-pdu`) | `gauss_filter` with its default parameters against `upstream-baseline` | **equivalent** (450 `$equiv` cells proved): the FIR is untouched |
| Controller through the registers (`ctl_lockstep`, run `tx-pdu`) | the whole controller against upstream, the tables and the packets written through the AXI registers, one after the other | **15/15 runs, 923 385 cycles compared, every output and every register read identical**; 90 packets sent, 90 received; **5/5 mutants** (a table tap, the pairing, the sign of the tap sum, the packet buffer's request, the IQ-capture half flag) |
| Upstream testbenches, strict (run `tx-pdu`, `GAUSS_TABLE=1`) | the 5 upstream testbenches over the 54 saved conditions of the integrity audit, against upstream | **FAIL, as on every branch**: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR, **0 DIFFERENT**; each of the 270 verdicts, with its reference and DUT status, equal to `master`'s strict run, and the 252 simulated checks give the same output files as upstream |
| The same on one-port macro models (run `tx-pdu-one-port`) | the same, with the buffer's and the VCO's memories on one-port macro models | **the same 270 verdicts, 0 DIFFERENT** |
| Gate-level lockstep (run `tx-pdu`, `BRANCH_COMPARISON.md` § 6.1) | both synthesised controllers, this branch and upstream, every output on every clock, 5 scenarios | **5/5 scenarios, no mismatch**; 25 packets transmitted and 27 sent to the receiver, the tables and the packets written through the registers |
| Integrity tests (`tests/test_validation*.py`) | the verdict guards of the integrity audit | 21 tests: 20 pass, 1 skipped (not applicable to this branch) |

The strict regression's FAIL is the upstream matrix of the integrity audit
(`VALIDATION_INTEGRITY.md`): upstream's own testbenches end with errors or
missing stimuli in 152 of the 270 checks, on `master` too, and this branch
fails exactly the same checks in exactly the same way. It shows no
difference; it does not show more than the 118 checks that pass.

## 5. Area

Yosys 0.68 + ABC, Nangate45, SRAMs blackboxed and counted in bits (run
`tx-pdu`; `ble-tx-opt` and `ble-tx-sin2` are runs `tx-opt` and `tx-1rw` of the
same harness). Each top is synthesised alone.

| Top | `master` | `ble-tx-opt` | `ble-tx-sin2` | **`ble-tx-pdu`** |
|---|---:|---:|---:|---:|
| `gauss_filter` (cells) | 2 286 | 253 | 2 286 | **166** |
| `vco` (cells) | 86 | 438 | 408 | **349** |
| `btle_tx`: cells / flip-flops | 3 409 / 404 | 1 696 / 326 | 3 687 / 465 | **1 305 / 256** |
| `btle_tx`: cell area (µm²) | 5 322.9 | 3 028.9 | 5 880.7 | **2 415.5** |
| `btle_controller`: cells / flip-flops | 50 295 / 4 578 | 48 559 / 4 500 | 50 621 / 4 639 | **48 164 / 4 430** |
| `btle_controller`: SRAM bits | 1 136 070 | 1 111 494 | 1 107 398 | **1 105 350** |

**The transmitter with its SRAM macros** (OpenRAM, FreePDK45; runs
`openram-tx`, `openram-sin8`, `openram-1rw-sweep` and `openram-pdu`; the
ports each RTL needs):

| | `master` | `ble-tx-opt` | `ble-tx-sin2` | **`ble-tx-pdu`** |
|---|---:|---:|---:|---:|
| TX cells (µm²) | 5 322.9 | 3 028.9 | 5 880.7 | **2 415.5** |
| COS/SIN macros (µm²) | 138 700.5 | 37 703.9 | 10 703.9 (1RW) | 10 703.9 (1RW) |
| Packet buffer (µm²) | 23 708.0 | 23 708.0 | 23 708.0 | **6 979.1** (1RW, 256 × 8) |
| **Total TX (µm²)** | **167 731.4** | **64 440.8** | **40 292.6** | **20 098.5** |
| vs `master` | — | −61.6 % | −76.0 % | **−88.0 %** |

Against `ble-tx-sin2`, the smallest transmitter built before, the branch
saves 20 194.1 µm² (−50.1 %): 16 728.9 in the packet buffer and 3 465.2 in
logic (B2, the rewrites and the buffer's port logic). The combination of B2
and the memory of `ble-tx-sin2`, estimated at 37 295.3 µm², is inside it; its
logic is 2 415.5 µm² here instead of the 2 883.4 estimated, because of the
rewrites. The memories are now 88.0 % of the transmitter, and the buffer is
the smaller of the two.

The buffer's macro, and two others for reference (run `openram-pdu`):

| Macro | Ports | Words × bits | Size (µm) | Area (µm²) |
|---|---|---|---|---:|
| `sram_1rw_8x256` (this branch) | 1RW | 256 × 8 | 85.290 × 81.828 | 6 979.1 |
| `sram_1rw_16x128_m8` | 1RW, 8-bit write mask | 128 × 16 | 86.390 × 77.000 | 6 652.0 |
| `sram_1rw1r_8x256` | 1RW1R | 256 × 8 | 146.405 × 114.410 | 16 750.2 |

Two bytes per word would save at most 327.1 µm² more, before the byte
multiplexer and the mask logic it needs; it is not built. A second port would
cost 2.4 times the area of the buffer.

The buffer's logic, module `pdu_buffer` synthesised alone with the same recipe,
is 73 cells, 23 flip-flops and 179.6 µm²: the request toggle, the reset and
request synchronizers (2 + 3 flip-flops), the read flag, the register of byte
256, the register of the byte read, and the address multiplexer of the one
port. The rest of the drop in `btle_tx` is the rewrites.

## 6. Timing and switching activity

Run `tx-pdu`, the whole controller against upstream
(`BRANCH_COMPARISON.md` §§ 5 and 6):

- **Timing:** minimum period 1.919 ns at the 62.5 ns (16 MHz) target, against
  1.991 ns upstream. The worst path is still the multiply of one of the 8
  upstream demodulators, in the receiver; the difference is flow noise. The
  flow times one clock, so the paths of the packet buffer's two clock domains
  are timed as if on it, and none of them is the worst. The 256 × 8 macro
  has its data 0.286 ns after the falling clock edge and a minimum period of
  1.059 ns in OpenRAM's model, far inside any AXI clock.
- **Switching activity** (pin-capacitance proxy, not power): −2.2 to −3.0 %
  over the five scenarios, against −1.1 to −3.1 % on `ble-tx-opt`. The 148
  flip-flops fewer than upstream (−156 in the filter, −44 in the three
  rewritten blocks, +48 in the VCO, +4 in the rest of `btle_tx`) put the
  clock-pin load 3.2 % down in every scenario. While transmitting, the filter
  switches as with B2 (79.1 → 21.7 toggles per cycle) and the rest of the
  transmitter 85 % more (68.0 → 125.7), as on `ble-tx-sin2`, whose two reads per
  sample it keeps; the RAM-port toggles rise 16.0 % in `tx` (7.2 % in `mixed`).
  OpenRAM's analytical model puts the leakage of the 256 × 8 one-port buffer
  at 2.3 µW, against 4.9 µW for upstream's 512 × 8 with two ports. (This
  report first added "0.42 pJ per access": that figure is the model's clock
  power, 0.42 mW with every gate at 100 MHz, the same for any cycle, not an
  energy per access. The buffer of this branch is written on every AXI clock;
  `ble-tx-pdu-we` writes it only when its pair is new, and measures the energy
  of both with SPICE, `BRANCH_COMPARISON.md` § 6.6.)

## 7. What the branch gives up

- **The runtime Gaussian taps** (as `ble-tx-table`): the taps are a synthesis
  parameter.
- **Arbitrary COS/SIN tables** (as `ble-tx-sin2`): each table must have
  quarter-wave symmetry and the cosine table must be cos[k] = sin[512 − k]
  (only cos[0] is stored); sine writes wait for a clock without a read, none
  while transmitting; the VCO takes at most one sample every two clocks. The
  project's tables and the transmitter meet this.
- **Rewriting a packet byte while it is read**: the packet must be written
  before `tx_start`, as the upstream testbenches do (the repository's
  firmware does not transmit); a byte rewritten in the 12 clocks between its
  request and its use may differ from upstream's; while a packet is sent, a
  pair must stay two AXI clocks (§ 2). The AXI clock must run at 8 MHz or
  faster.

The receiver, the Link Layer and the IQ-capture debug memory lose nothing.

## 8. Reproducing

From WSL, at the root of this branch:

```bash
python3 tests/test_tx_pdu.py --mutants                                          # IVERILOG, VVP in PATH
python3 tests/test_vco_sin2.py --mutants
python3 -m unittest discover -s tests -p 'test_validation*.py' -v
mkdir -p /tmp/btle-audited-vectors
tar -xzf results/validation/integrity-20261004/vectors.tar.gz -C /tmp/btle-audited-vectors
REGRESSION_VECTORS=/tmp/btle-audited-vectors/vectors DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1" \
  scripts/validation/run_rx_regression.sh <label>                               # expected exit 1, 0 DIFFERENT
# the same on the one-port macro models: in a separate clone
python3 tests/test_vco_sin2.py --write-one-port /tmp/vco.v && cp /tmp/vco.v verilog/vco.v
python3 tests/test_tx_pdu.py --write-one-port /tmp/btle_tx.v && cp /tmp/btle_tx.v verilog/btle_tx.v
scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>
scripts/validation/formal_gauss/run_formal_gauss.sh <label>
scripts/validation/equiv_defaults/run_equiv_defaults.sh <label> upstream-baseline gauss_filter
scripts/area/run_openram.sh <label> sram_1rw_8x256 sram_1rw_16x128_m8 sram_1rw1r_8x256
mkdir /tmp/vec && tar -xzf results/compare/all-branches/vectors.tar.gz -C /tmp/vec
VEC_DIR=/tmp/vec scripts/compare/run_compare.sh <label> master ble-tx-pdu
```
