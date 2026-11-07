# Documentation index

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

This folder holds the documentation written for the dissertation. It covers the
code inherited from the upstream [BTLE](https://github.com/JiaoXianjun/BTLE)
project and the work built on top of it. The upstream documentation stays where
the upstream put it, but for its `doc/` folder, merged into this one
([Upstream documents](#upstream-documents)).
[Reference Manual](Reference%20Manual/UPSTREAM_DOCUMENTATION.md) lists where each piece is.

Latest lint and documentation update: [LINT_CLOSURE.md](Validation/LINT_CLOSURE.md).

## Where to start

| If you want to... | Read |
|---|---|
| Know what this repository is and what is mine | [../CHANGES.md](../CHANGES.md) |
| Understand the inherited hardware | [Architecture/UPSTREAM_ARCHITECTURE.md](Architecture/UPSTREAM_ARCHITECTURE.md) |
| Program the Link Layer registers | [Architecture/LL_REGISTER_MAP.md](Architecture/LL_REGISTER_MAP.md) |
| Know what the thesis is trying to decide | [Design Decisions/SCOPE.md](Design%20Decisions/SCOPE.md) |
| See where the BLE area goes and how to shrink it | [Design Decisions/AREA_REDUCTION_PLAN.md](Design%20Decisions/AREA_REDUCTION_PLAN.md) |
| Know what is tested and what is not | [Validation/UPSTREAM_TEST_INVENTORY.md](Validation/UPSTREAM_TEST_INVENTORY.md) |
| See the Gaussian table (B2) alone, its proofs and its saving | [Validation/TX_TABLE_VALIDATION.md](Validation/TX_TABLE_VALIDATION.md) |
| See B2 and the {cos, sin} memory together: its checks, area and activity | [Validation/TX_OPT_VALIDATION.md](Validation/TX_OPT_VALIDATION.md) |
| See the packet buffer with one port, with B2, the sine table of `ble-tx-sin2` and exact rewrites, the smallest transmitter with programmable VCO tables: its checks, area and activity | [Validation/TX_PDU_VALIDATION.md](Validation/TX_PDU_VALIDATION.md) |
| See the VCO without memory, its tables fixed in a ROM of an eighth of the wave: its checks, area, timing and SRAM energy | [Validation/TX_ROM_VALIDATION.md](Validation/TX_ROM_VALIDATION.md) |
| See the Legacy Advertising transmitter (header in registers, AdvA in ROM/OTP, AdvData in 32 x 8), the smallest transmitter measured: its checks, area, timing, activity, OTP and figures | [Validation/TX_MIN_VALIDATION.md](Validation/TX_MIN_VALIDATION.md) |
| Compare the final transmitter with upstream, every result side by side (signals, BER, area, timing, FPGA, power, layout, OTP), and read the decisions | [TX_FINAL_DECISIONS.md](TX_FINAL_DECISIONS.md) |
| Compare the senseworks tags (`ble-tx-tag-8/12/18`: the minimal ADV_NONCONN_IND with BCH parity, no receiver): packet, code, validation, area, timing, layout, FPGA, time on the air, and the choice | [Senseworks/TX_TAG_COMPARISON.md](Senseworks/TX_TAG_COMPARISON.md) |
| Read the tag of the proof of concept (`ble-tx-poc-gen`: a state machine with no processor, no memory, for several sensors, I2C and SPI, a table of slots chosen by pins, the rate on pins): what it is, its validation, area, layout and FPGA, the steps on the board | [`Senseworks/TX_POC_GEN.md`](Senseworks/TX_POC_GEN.md) (the plan: [`PLANO_PoC.md`](PLANO_PoC.md)) |
| Read the IoT tag (`ble-tx-iot`, `ble-iot-1byte`) | [Senseworks/TX_TAG_4_IOT.md](Senseworks/TX_TAG_4_IOT.md) |
| Read the IoT receiver (`ble-rx-iot`, the two-byte tag; `ble-rx-iot-1byte`, the one-byte; 2 phases, the CRC + 1 bit, no BCH, no transmitter): every result of `RX_FINAL_DECISIONS.md` for both, the PER on the tag's packets, the alternatives, the GF180 die sweep, the choice | [`Senseworks/RX_4_IOT.md`](Senseworks/RX_4_IOT.md) |
| Compare the senseworks gateways (`ble-rx-gateway-8/12/18`) with `ble-rx-micro` and `ble-rx-2p1c`: packet loss in the RTL, false accepts, area, timing, GF180 layout, FPGA | [Senseworks/RX_GATEWAY_COMPARISON.md](Senseworks/RX_GATEWAY_COMPARISON.md) |
| Read the first tag of the proof of concept (`ble-tx-poc`: the generic core, the profile from an EEPROM), the reference of the two below | [Senseworks/TX_POC.md](Senseworks/TX_POC.md) |
| Read the tag of the proof of concept for the TMP100 alone (`ble-tx-poc-tmp100`: the least area, no memory): its validation, area, layout, FPGA | [Senseworks/TX_POC_TMP100.md](Senseworks/TX_POC_TMP100.md) |
| Read the gateway of the proof of concept (`ble-rx-poc`: many tags into one gateway, the queue, UDP to the PC, the application): its validation end to end from the tags' RTL, FPGA | [Senseworks/RX_POC.md](Senseworks/RX_POC.md) |
| Compare the transmitter branches and `ble-opt`: area (the transmitter with its SRAM macros), timing, switching activity | [Validation/TX_BRANCH_COMPARISON.md](Validation/TX_BRANCH_COMPARISON.md) |
| Compare the receiver branches (`ble-rx-dm`, `ble-rx-dmult`): area, timing, switching activity | [Validation/RX_BRANCH_COMPARISON.md](Validation/RX_BRANCH_COMPARISON.md) |
| Choose where the Gaussian table lives (OTP, ROM, SRAM, REG) or a folded FIR, by TX area | [Design Decisions/GAUSS_FILTER_OPTIONS.md](Design%20Decisions/GAUSS_FILTER_OPTIONS.md) |
| Choose the single-port memory of the VCO tables (OpenRAM sweep: 512×16, 512×8, 256×16, 128×32, 64×64) | [Design Decisions/VCO_MEMORY_SWEEP.md](Design%20Decisions/VCO_MEMORY_SWEEP.md) |
| Reproduce the upstream results | [Guides/REPRODUCE_UPSTREAM.md](Guides/REPRODUCE_UPSTREAM.md) |
| Add a document or record a change | [Guides/CONTRIBUTING.md](Guides/CONTRIBUTING.md) |

## Folder layout

Folders are named by subject, without numeric prefixes. A folder is created
when it has content; planned sections are listed below.

| Folder | Holds | Status |
|---|---|---|
| `Architecture/` | How the hardware is built: hierarchy, clocks, interfaces, registers | Upstream described |
| `Design Decisions/` | Scope, open questions, decisions and the reasons for them; area reduction plan | Four decisions open; area baseline measured |
| `RISC-V Integration/` | Implementation of the core and its interface to the PHY | Not started |
| `Validation/` | Test inventory, evidence, results | B2 and the {cos, sin} memory together, checked and measured (branch `ble-tx-opt`); branches compared |
| `Thesis/` | Reports written for the dissertation | Not started |
| `Guides/` | How to reproduce, build and contribute | Written, not yet executed |
| `Senseworks/` | The senseworks system: the tag (transmitter only) and the gateway (receiver only) | The three tags measured (branches `ble-tx-tag-*`); this branch's tag measured, not on a board (`ble-tx-poc-gen`); the gateway not started |
| `Reference Manual/` | Pointers to the upstream documentation | Written |
| `Meetings and Discussions/` | Meeting notes with the supervisor | Not started |

## Upstream documents

Upstream's `doc/` folder moved here on 2026-10-06 with its three third-party
PDFs: [TI-BLE-INTRODUCTION.pdf](TI-BLE-INTRODUCTION.pdf), [ibeacon.pdf](ibeacon.pdf)
and [BLE_sniffer_guide.pdf](BLE_sniffer_guide.pdf). Its README read:

> See some docs which are useful in [https://github.com/JiaoXianjun/doc](https://github.com/JiaoXianjun/doc)
>
> See new type of discovery packet in host/btle-tools/src/packets_discovery.txt

## Repository map

Everything outside `docs/`, `CHANGES.md` and the header of `README.md` is
inherited unchanged from tag `upstream-baseline`. The folders stay where the
upstream put them, but for `doc/`, whose PDFs and README moved into `docs/` on
2026-10-06 (only the root `README.md` linked them). The Vivado projects, the test-vector generator and the
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
| `docs/*.pdf` | Third-party PDFs (TI BLE intro, iBeacon, sniffer guide), upstream's `doc/` until 2026-10-06 | upstream |
| `fpga/adi-hdl/`, `BTLE-hw-img/` | Git submodules (ADI HDL library, prebuilt images); empty until initialised | upstream |
| `docs/` | This documentation, and upstream's `doc/` (§ Upstream documents) | mine, but for the PDFs |
| `CHANGES.md` | Derivation notice and change log against the baseline | mine |
| `scripts/area/` | Per-module Yosys area flow (Nangate45, SRAMs as macros) | mine |
| `results/area/<label>/` | Area runs: summary, stats, compressed logs, provenance | mine |
| `scripts/validation/` | Regression, controller lockstep and formal-equivalence harnesses | mine |
| `results/validation/<label>/` | Validation runs: verdicts, logs, provenance | mine |
| `scripts/power/`, `results/power/<label>/` | Switching-activity harness (gate-level, SAIF) and its runs | mine |
| `scripts/timing/`, `results/timing/<label>/` | Static-timing harness (register-to-register, ABC `stime`) and its runs | mine |
| `scripts/compare/`, `results/compare/<label>/` | Cross-branch comparison (every branch in its configuration, one run) | mine |
| `scripts/branch_config.sh` | The configuration a branch is measured in | mine |

## Conventions

Every document written here starts with the same header block (Project, Branch,
Date, Author) and has `Author: Miguel Simões`. Claims are either backed by a
file, a command or a log, or marked as not verified.
[Guides/CONTRIBUTING.md](Guides/CONTRIBUTING.md) has the full rules.
