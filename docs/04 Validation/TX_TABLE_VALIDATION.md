# Validation of the Gaussian table alone (B2, branch `ble-tx-table`)

> Validation correction (2026-10-04): earlier success claims for all 270 checks are withdrawn. The strict rerun is **FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**. See [the integrity audit](VALIDATION_INTEGRITY.md) for evidence and limitations.

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `ble-tx-table`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-28  
**Author:** Miguel Simões  
**Status:** executed. RTL commit `dfcc15c`; harnesses `6e2c5b1` and `6153835`.

---

## Purpose

Branch `ble-opt` applies four reductions together (B1, A1, A2, B2). This branch
holds **only B2**, the fixed-tap Gaussian table in the transmitter, on top of
the upstream design, so that its effect can be measured and proved on its own.
This report records the evidence that B2 alone keeps every function of the
transmitter (and leaves the rest of the design untouched), and the cells it
saves. The comparison with the other branches is in
[BRANCH_COMPARISON.md](BRANCH_COMPARISON.md).

## 1. What is on this branch

| Change | On this branch | Where it is |
|---|---|---|
| B2: Gaussian FIR → distributed-arithmetic tables (`GAUSS_TABLE`) | **yes** | here and on `ble-opt` |
| B1: one shared demodulator instead of 8 | no: `btle_rx` has the 8 upstream demodulators | `ble-rx-dm`, `ble-opt` |
| A1: no IQ-capture RAM (`ENABLE_IQ_CAPTURE`) | no: the 1 Mbit capture RAM is there | `ble-opt` |
| A2: minimal Link Layer (`LL_MINIMAL`) | no: full `btle_ll`, UART HCI included | `ble-opt` |
| Model update into NVM (`firmware/model_update/`) | no | `ble-opt` |

The branch starts at `69c8b51`, the last `ble-opt` commit before B1 (area
flow and baseline measurement, no RTL change), so its history up to that
point is the same as `ble-opt`'s.

**The B2 code is the `ble-opt` code.** `gauss_filter.v`, `gfsk_modulation.v`
and `btle_tx.v` are byte-identical to `ble-opt` (commit `39f5851` was the only
one to touch them there, and only for B2). `btle_phy.v` and `btle_controller.v`
carry only the B2 lines of that commit: the `GAUSS_TABLE` parameter, passed
down `btle_controller → btle_phy → btle_tx → gfsk_modulation → gauss_filter`.

```bash
git diff ble-opt ble-tx-table -- verilog/gauss_filter.v verilog/gfsk_modulation.v verilog/btle_tx.v   # empty
git diff --stat upstream-baseline ble-tx-table -- verilog                                              # 6 files
```

The sixth file is `btle_controller_tb.v`, with the declaration move of `de0cc54`
(issue U9) so that the top-level testbench compiles in Icarus.

**Configuration.** As on `ble-opt`, the default (`GAUSS_TABLE=0`) is the
original FIR, so the Vivado flow of the boards is unchanged. The branch is
measured and validated in its configuration, **`GAUSS_TABLE=1`**.

**Function removed in that configuration:** the runtime change of the
Gaussian taps. The taps become a synthesis parameter (`GAUSS_TABLE_TAPS`,
default the BLE BT = 0.5 taps of `python/btlelib.py`); register 1 and the
`ext_tx_gauss_filter_tap_*` port are ignored. Nothing else is removed.

## 2. Evidence that nothing needed was lost

Four independent checks, each reproducible with one command. Each run records
its commit, tools and inputs in a `provenance.txt` under
[`results/validation/tx-table/`](../../results/validation/tx-table/).

### 2.1 The table is the FIR, for every input (formal, unbounded)

`scripts/validation/formal_gauss/run_formal_gauss.sh`, the `ble-opt` harness
unchanged. The upstream FIR is loaded through its own tap interface with the
taps the table was built from; then the input bits, their valid signals and
the resets are free on every clock, and the outputs must be equal on every
clock.

| Result | |
|---|---|
| Proof | **PASS, unbounded** ("successful proof by k-induction", depth 40) |
| Mutants | 3 of 3 make the proof fail: wrong tap mirroring, a table group one position off, a wrong sign |

### 2.2 The default configuration is upstream (formal, per module)

`scripts/validation/equiv_defaults/run_equiv_defaults.sh tx-table upstream-baseline …`:
Yosys equivalence checking (`equiv_make`, `equiv_simple`, `equiv_induct`,
`equiv_status -assert`), RAMs mapped to flip-flops so their contents are part
of the proof, against `upstream-baseline` itself.

| Module | Result |
|---|---|
| `gauss_filter` | equivalent (450 `$equiv` cells, all proven) |
| `gfsk_modulation` | equivalent (33 294) |
| `btle_tx` | equivalent (37 622) |
| `btle_phy` | equivalent (73 598) |
| `btle_controller` | **equivalent (96 609)** |

This is what guarantees that the boards, which use the defaults, see the
upstream design. The method is the one of
`STICKER_REDUCTIONS_VALIDATION.md` on `ble-opt` (IQ-capture RAM reduced to
64 words on both sides, `async2sync` on both sides).

**Harness fix.** The first run stopped with "There is already an object
`sdpram_two_clk_auxiliary_daemon_i`" in every module. The script renames the
instances that `ble-opt` moved into `generate` blocks; this branch has no such
blocks, so the rename collided with the original name. Commit `6153835`
emits a rename only where the new RTL has the block. No RTL changed.

### 2.3 Controller through the registers, every output compared

`scripts/validation/ctl_lockstep/run_ctl_lockstep.sh`, adapted from `ble-opt`:
the **upstream `btle_controller`** and this branch's controller with
**`GAUSS_TABLE=1`** run side by side, driven through the AXI-lite registers in
mode 0 (the path the boards use) with the software sequence of
`firmware/btle_ll.c`, packets of the Python model between random noise
(a third with a corrupted tail), TX through registers 4–9, and a final read of
all 64 registers.

Because nothing is removed on this branch, the comparison is stricter than on
`ble-opt`: **every output on every clock**, including the IQ-capture data,
`ll_itrpt2` and `uart_tx`, and **every register read** must be equal.

| Result | |
|---|---|
| Runs | **15 of 15 without a mismatch** (3 packets × 5 seeds × 6 packets) |
| Clocks compared | 923 385 |
| RX packets | 90 interrupts; 57 with a correct CRC, 33 corrupted on purpose |
| TX packets through the registers | 90, the I/Q output identical on every clock |
| AXI register reads, all compared | 2 404 |
| Mutation check | **4 of 4 caught**: one table tap wrong (24 → 23), table group B one position off, a wrong sign, and the IQ-capture half flag without its mid-buffer point (caught on `ll_itrpt2` at clock 32 777, which shows that the outputs `ble-opt` excludes are compared here) |

The counts are the same as the `ble-opt` run, as they should be: the stimulus
depends only on the upstream side and the seeds.

### 2.4 Upstream testbenches, with the table switched on

`DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1" scripts/validation/run_rx_regression.sh tx-table`.
`DUT_DEFAULTS` rewrites the parameter default in the copy under test only, so
the upstream testbenches, which instantiate the modules with their defaults,
run on the table. For 3 packets × SNR {20, 12, 8} dB × clock error
{0, 20, 50} ppm × sample delay {0, 5}, both designs must give the same verdict
**and** the same output files, byte for byte.

**FAIL: 118 PASS, 20 BOTH_FAIL, 18 NO_STIMULUS, 114 ERROR; 0 DIFFERENT**.

The earlier table counted incomplete checks as successful. Corrected per-bench counts are in the [integrity audit](VALIDATION_INTEGRITY.md).

### 2.5 Gate level

The cross-branch comparison runs the **synthesised netlists** of upstream and
of this branch side by side in five scenarios, every output compared on every
clock, and finds no mismatch. See [BRANCH_COMPARISON.md](BRANCH_COMPARISON.md).

## 3. Area (measured)

`AREA_PARAMS="GAUSS_TABLE=1" scripts/area/run_area.sh tx-table`, same flow as
every earlier run (Yosys 0.68, Nangate45, SRAMs as macros). Results in
[`results/area/tx-table/`](../../results/area/tx-table/summary.md).

| Top | Upstream | B2 alone | Change |
|---|---:|---:|---:|
| `gauss_filter` | 2 286 | 253 | −2 033 (−88.9 %) |
| `gfsk_modulation` | 2 466 | 426 | −2 040 (−82.7 %) |
| `btle_tx` | 3 409 | 1 392 | −2 017 (−59.2 %) |
| `btle_phy` | 40 339 | 38 083 | −2 256 (−5.6 %) |
| **`btle_controller`, std cells** | **50 295** | **48 227** | **−2 068 (−4.1 %)** |
| `btle_controller`, flip-flops | 4 578 | 4 422 | −156 |
| `btle_controller`, cell area (µm²) | 71 706 | 68 667 | −4.2 % |
| `btle_controller`, SRAM bits | 1 136 070 | 1 136 070 | 0 |

The Gaussian filter loses 156 of its 178 flip-flops (mostly the 9 × 16-bit
runtime tap registers), and its 17-term sum over runtime taps becomes three
table lookups and a three-term sum. `gauss_filter` alone measures exactly as in the
`ble-opt` run `sticker` (253 cells, 22 flip-flops), as expected from identical
code. Modules that did not change move by a few cells (`btle_rx`
36 864 → 36 884), the flow noise already recorded on `ble-opt`: ABC's result
depends on everything Yosys reads.

B2 is a small saving on its own, because the upstream controller is dominated
by the 8 demodulators (62 % of the cells), which this branch keeps.

## 4. What is not claimed

- No FPGA or board test.
- Timing and switching activity are in [BRANCH_COMPARISON.md](BRANCH_COMPARISON.md),
  with the same limits as on `ble-opt` (pre-layout, ideal wires, a proxy and
  not power).
- The table is exact for the taps it was built from. Runtime-programmable
  taps are gone in this configuration; if they are needed, the table can
  become a 1-kbit RAM written by software, as `ble-opt` notes.

## 5. Reproducing

From WSL, at the repository root, on this branch:

```bash
scripts/validation/formal_gauss/run_formal_gauss.sh <label>
scripts/validation/equiv_defaults/run_equiv_defaults.sh <label> upstream-baseline \
    gauss_filter gfsk_modulation btle_tx btle_phy btle_controller
scripts/validation/ctl_lockstep/run_ctl_lockstep.sh <label>
DUT_DEFAULTS="gauss_filter.v:GAUSS_TABLE=1" scripts/validation/run_rx_regression.sh <label>
AREA_PARAMS="GAUSS_TABLE=1" scripts/area/run_area.sh <label>
```

Tools: OSS CAD Suite 2026-09-07 (Yosys 0.68+195, Icarus 14, SBY, Bitwuzla,
yosys-slang) and Python 3.11 with numpy 2.4.6. The five runs take about
2 minutes each in parallel, except `equiv_defaults` on `btle_controller`.
