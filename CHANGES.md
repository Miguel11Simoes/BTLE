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

## Files inherited and not modified

Everything not listed above. To see the exact list at any time:

```bash
git diff --stat upstream-baseline..HEAD
```
