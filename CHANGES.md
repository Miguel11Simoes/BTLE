# Changes relative to upstream BTLE

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Author:** Miguel Simões

---

This repository is a derivative work of [BTLE](https://github.com/JiaoXianjun/BTLE)
by Xianjun Jiao, used under the Apache License 2.0. The `LICENSE` and `NOTICE`
files of the original are kept unchanged.

**Baseline:** tag `upstream-baseline` = `8540186` ("Fix the bin_file_to_iq.m",
2026-06-08), 640 commits, all of them authored upstream. Nothing in that tag
is my work. Everything listed below is.

Apache 2.0 section 4(b) requires a derivative work to carry prominent notices
stating that files were changed. This file is that notice. It is also the
record the dissertation needs of what was inherited and what I built.

## How to read this file

There is one entry per change, newest last. Each entry states what changed,
why, and where the evidence is. A change with no evidence is a work in
progress and says so.

| Date | Area | Change | Evidence |
|---|---|---|---|
| 2026-09-18 | repo | Derived this repository from the upstream baseline; added this file and `docs/SCOPE.md`. No functional change to any inherited source. | `git diff upstream-baseline..HEAD` |
| 2026-09-18 | docs | Organised `docs/` into numbered folders matching `snitch_cluster_tese`. Moved `docs/SCOPE.md` to `docs/02 Design Decisions/`, rewritten in English and corrected after reading the code. Added the index, the architecture description, the reconstructed LL register map, the test inventory, the reproduction guide, the conventions and the upstream documentation map. No inherited source changed. | `docs/README.md` |
| 2026-09-18 | README | **Modified inherited file:** added a short fork notice at the top of `README.md` that points to `CHANGES.md` and `docs/`. The upstream text below it is unchanged. | `git diff upstream-baseline..HEAD -- README.md` |
| 2026-09-18 | build | **Modified inherited file:** `.gitignore` now also ignores editor folders, Python caches, and the test vectors and simulation outputs that the flows generate in `verilog/`. The line that was already there is kept. | `git diff upstream-baseline..HEAD -- .gitignore` |
| 2026-09-18 | area | *Branch `ble-opt`.* Added `scripts/area/` (a per-module Yosys flow: Nangate45, SRAMs blackboxed as macros, provenance recorded) and the first run `results/area/baseline-upstream/` on the unmodified RTL. The controller measures 50 295 std cells and 1 136 070 SRAM bits. Added `.gitattributes` (LF for scripts) and ignored the mapped netlists in `.gitignore`. No RTL changed. | `results/area/baseline-upstream/summary.md`, `provenance.txt` |
| 2026-09-18 | docs | *Branch `ble-opt`.* Added `docs/02 Design Decisions/AREA_REDUCTION_PLAN.md`. Corrected issue U1: the second copies of the UART and clock-generator modules inside `btle_ll.v` sit under `` `ifdef AVOID_DUPLICATION `` and are never compiled, so nothing is defined twice and the top-level testbench command should work as written. | `btle_ll.v` lines 2218–2783 |

| 2026-09-28 | tx | *Branch `ble-tx-table`, commit `dfcc15c`.* Branch created at `69c8b51` of `ble-opt` (before B1) to hold **only B2**. **Modified inherited files** `gauss_filter.v` (`GAUSS_TABLE`, `GAUSS_TABLE_TAPS`), `gfsk_modulation.v` and `btle_tx.v` (all three byte-identical to `ble-opt`), `btle_phy.v` and `btle_controller.v` (only the `GAUSS_TABLE` parameter, passed down). No B1, A1 or A2. The default keeps the original FIR (proved against `upstream-baseline`, per module). Configuration `GAUSS_TABLE=1`: controller 50 295 → 48 227 std cells (−4.1 %); SRAM unchanged. | `docs/04 Validation/TX_TABLE_VALIDATION.md`; `results/area/tx-table/`; `results/validation/tx-table/` |
| 2026-09-28 | tb | *Branch `ble-tx-table`, commit `4c8d66a`.* **Modified inherited file** `btle_controller_tb.v`: the declaration move of `de0cc54` (issue U9), so the top-level testbench compiles in Icarus. The file-list comment keeps the upstream text. | `git show 4c8d66a` |
| 2026-09-28 | validation | *Branch `ble-tx-table`.* `scripts/area/run_area.sh` gains `AREA_PARAMS` (from `39f5851`). Added `scripts/validation/`: `formal_gauss/` (unchanged from `ble-opt`), `equiv_defaults/` (fixed in `6153835`: renames only the instances that were moved into `generate` blocks), `ctl_lockstep/` (adapted: dut `GAUSS_TABLE=1`, every output and every register compared) and `run_rx_regression.sh` (with `DUT_DEFAULTS`). `.gitattributes`: LF for `*.sby` (`ec3ccf0`). | the scripts' headers |
| 2026-09-28 | compare | *Branches `ble-opt`, `ble-tx-table`, `ble-rx-dm`.* Added the measurement harnesses of `ble-opt` (`scripts/area`, `scripts/power`, `scripts/timing`, identical on the three branches), `scripts/compare/` and `scripts/branch_config.sh`. Run `all-branches`: area, static timing and switching activity of every branch in its own configuration, in one run. Added `docs/04 Validation/BRANCH_COMPARISON.md`, the same file on every branch. No inherited file changed. | `docs/04 Validation/BRANCH_COMPARISON.md`; `results/compare/all-branches/` |

## Files inherited and not modified

Everything not listed above. To see the exact list at any time:

```bash
git diff --stat upstream-baseline..HEAD
```
