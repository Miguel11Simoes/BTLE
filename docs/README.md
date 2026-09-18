# Documentation index

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

This folder holds the documentation written for the dissertation. It covers the
code inherited from the upstream [BTLE](https://github.com/JiaoXianjun/BTLE)
project and the work built on top of it. The upstream documentation stays where
the upstream put it. [07 Reference Manual](07%20Reference%20Manual/UPSTREAM_DOCUMENTATION.md)
lists where each piece is.

## Where to start

| If you want to... | Read |
|---|---|
| Know what this repository is and what is mine | [../CHANGES.md](../CHANGES.md) |
| Understand the inherited hardware | [01 Architecture/UPSTREAM_ARCHITECTURE.md](01%20Architecture/UPSTREAM_ARCHITECTURE.md) |
| Program the Link Layer registers | [01 Architecture/LL_REGISTER_MAP.md](01%20Architecture/LL_REGISTER_MAP.md) |
| Know what the thesis is trying to decide | [02 Design Decisions/SCOPE.md](02%20Design%20Decisions/SCOPE.md) |
| See where the BLE area goes and how to shrink it | [02 Design Decisions/AREA_REDUCTION_PLAN.md](02%20Design%20Decisions/AREA_REDUCTION_PLAN.md) |
| Know what is tested and what is not | [04 Validation/UPSTREAM_TEST_INVENTORY.md](04%20Validation/UPSTREAM_TEST_INVENTORY.md) |
| Reproduce the upstream results | [06 Guides/REPRODUCE_UPSTREAM.md](06%20Guides/REPRODUCE_UPSTREAM.md) |
| Add a document or record a change | [06 Guides/CONTRIBUTING.md](06%20Guides/CONTRIBUTING.md) |

## Folder layout

The numbering matches the `snitch_cluster_tese` repository, so the same kind of
document has the same number in both theses. A folder exists only once it has
content, which is why some numbers are missing.

| Folder | Holds | Status |
|---|---|---|
| `01 Architecture/` | How the hardware is built: hierarchy, clocks, interfaces, registers | Upstream described |
| `02 Design Decisions/` | Scope, open questions, decisions and the reasons for them; area reduction plan | Four decisions open; area baseline measured |
| `03 RISC-V Integration/` | Implementation of the core and its interface to the PHY | Not started |
| `04 Validation/` | Test inventory, evidence, results | Inventory only; nothing executed yet |
| `05 Thesis/` | Reports written for the dissertation | Not started |
| `06 Guides/` | How to reproduce, build and contribute | Written, not yet executed |
| `07 Reference Manual/` | Pointers to the upstream documentation | Written |
| `09 Meetings and Discussions/` | Meeting notes with the supervisor | Not started |

## Repository map

Everything outside `docs/`, `CHANGES.md` and the header of `README.md` is
inherited unchanged from tag `upstream-baseline`. The folders stay where the
upstream put them. The Vivado projects, the test-vector generator and the
OpenLane notebook use relative paths between folders (for example
`fpga/*/btle.tcl` loads `../../verilog/`), so moving a folder would break those
flows.

| Path | What it is | Origin |
|---|---|---|
| `verilog/` | BLE baseband RTL (PHY + Link Layer) and unit testbenches | upstream |
| `python/` | Bit-true Python model; generates the testbench vectors into `verilog/` | upstream |
| `matlab/` | Early algorithm studies and fixed-point checks | upstream |
| `fpga/` | Vivado projects for AD9361 + Zynq boards (AntSDR, AntSDR E200, SDRPi) | upstream |
| `firmware/` | `btle_ll.c`: Linux user-space program on the Zynq ARM that drives the baseband | upstream |
| `host/btle-tools/` | `btle_rx` / `btle_tx`: the original SDR sniffer and transmitter for HackRF/bladeRF | upstream |
| `host/ble_fpga_ctl/` | Host PC tools for the FPGA board (Wireshark bridge, commands, IQ capture) | upstream |
| `host/python/btle_cli/` | Python CLI/TUI around `btle_rx`/`btle_tx` | upstream |
| `open_btle_baseband_chip/` | Chip write-up and Colab notebook (Python, Verilog, Vivado, OpenLane2/SKY130) | upstream |
| `usrp_replay_example/` | Replay of a recorded BLE packet on a USRP | upstream |
| `doc/` | Third-party PDFs (TI BLE intro, iBeacon, sniffer guide) | upstream |
| `fpga/adi-hdl/`, `BTLE-hw-img/` | Git submodules (ADI HDL library, prebuilt images); empty until initialised | upstream |
| `docs/` | This documentation | mine |
| `CHANGES.md` | Derivation notice and change log against the baseline | mine |
| `scripts/area/` | Per-module Yosys area flow (Nangate45, SRAMs as macros) | mine |
| `results/area/<label>/` | Area runs: summary, stats, compressed logs, provenance | mine |

## Conventions

Every document written here starts with the same header block (Project, Branch,
Date, Author) and has `Author: Miguel Simões`. Claims are either backed by a
file, a command or a log, or marked as not verified.
[06 Guides/CONTRIBUTING.md](06%20Guides/CONTRIBUTING.md) has the full rules.
