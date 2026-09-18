# Changes relative to upstream BTLE

This repository is a derivative work of [BTLE](https://github.com/JiaoXianjun/BTLE)
by Xianjun Jiao, used under the Apache License 2.0. The `LICENSE` and `NOTICE`
files of the original are kept unchanged.

**Baseline:** tag `upstream-baseline` = `8540186` ("Fix the bin_file_to_iq.m",
2026-06-08), 640 commits, every one of them authored upstream. Nothing in that
tag is my work. Everything listed below is.

Apache 2.0 section 4(b) asks a derivative work to carry prominent notices
stating that files were changed. This file is that notice, and it is also the
record I need for the dissertation: what was inherited, and what I built.

## How to read this file

One entry per change, newest last. Each entry states what changed, why, and
where the evidence is. A change with no evidence is a work in progress and
says so.

| Date | Area | Change | Evidence |
|---|---|---|---|
| 2026-09-18 | repo | Derived this repository from the upstream baseline; added this file and `docs/SCOPE.md`. No functional change to any inherited source. | `git diff upstream-baseline..HEAD` |

## Files inherited and not modified

Everything not listed above. To see this precisely at any moment:

```bash
git diff --stat upstream-baseline..HEAD
```
