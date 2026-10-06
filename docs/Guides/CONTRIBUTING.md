# Documentation and change conventions

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

## Purpose

These are the rules that keep this repository readable, and keep a clear
separation between what was inherited and what was built for the thesis.

## 1. Every new document

- Goes under `docs/`, in the folder that matches its kind (see
  [../README.md](../README.md)). Create a missing folder with the name the index
  gives it, without a number.
- Starts with this header:

  ```markdown
  # <Title>

  **Project:** BTLE — reconfigurable RISC-V baseband
  **Branch:** `<branch>`
  **Base:** tag `upstream-baseline` (`8540186`)      ← when it describes inherited code
  **Date:** <YYYY-MM-DD>
  **Author:** Miguel Simões
  **Status:** <draft | executed | superseded by …>  ← when it makes claims about results

  ---

  ## Purpose
  ```

- Uses `UPPER_SNAKE_CASE.md` for the file name.
- Gets a line in the index, [../README.md](../README.md).
- Cites a file and line, a command, or a log for every factual claim. A
  statement that has not been checked says so.
- When it is corrected, gets a revision-history table rather than a silent
  rewrite.

## 2. Every change to inherited code

- Gets a row in [../../CHANGES.md](../../CHANGES.md): date, area, what changed and
  why, and the evidence. This is the modification notice that Apache 2.0
  section 4(b) requires.
- Keeps the original author and SPDX header of the file. Add a line under it
  instead of replacing it:

  ```verilog
  // Author: Xianjun Jiao <putaoshu@msn.com>
  // SPDX-FileCopyrightText: 2025 Xianjun Jiao
  // SPDX-License-Identifier: Apache-2.0 license
  // Modified 2026-MM-DD by Miguel Simões: <one line>. See CHANGES.md.
  ```

- Does not move inherited folders. The Vivado, Python and OpenLane flows
  reference each other through relative paths.

## 3. Every new source file

Starts with:

```verilog
// Author: Miguel Simões
// SPDX-FileCopyrightText: 2026 Miguel Simões
// SPDX-License-Identifier: Apache-2.0
```

(or the `#` / `<!-- -->` form for scripts and Markdown).

## 4. Commits

Commits use the Conventional Commits form used in `snitch_cluster_tese`: `docs:`,
`fix(rtl):`, `feat(ll):`, `test:`, `build:`. Each commit covers one logical
change. At any time, `git diff --stat upstream-baseline..HEAD` must show only
files that `CHANGES.md` accounts for.
