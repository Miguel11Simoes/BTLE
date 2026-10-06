# Upstream documentation map

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  

---

## Purpose

The upstream documentation is spread over several READMEs, a notebook and a
folder of PDFs. It is left where it is, so that its links and images keep
working, but for the folder of PDFs, `doc/`, which moved into `docs/` on
2026-10-06. This page says where each topic is covered and how reliable that
source is.

| Topic | Upstream source | Notes |
|---|---|---|
| Project overview, SDR tools `btle_rx`/`btle_tx`, packet descriptor syntax | [README.md](../../README.md) | For HackRF/bladeRF only. Unrelated to the FPGA/RTL path. |
| Chip design: features, BER claims, references, images | [open_btle_baseband_chip/README.md](../../open_btle_baseband_chip/README.md) | States that the OpenLane runs did not close. |
| Algorithm explanation and local run of Python, Icarus, Vivado and OpenLane | [open_btle_baseband_chip/open_btle_baseband_chip.md](../../open_btle_baseband_chip/open_btle_baseband_chip.md) (same content as the `.ipynb`) | The top-level Icarus command is out of date (issue U2). |
| FPGA boards: SD card, bitstream, Wireshark, IQ capture | [fpga/README.md](../../fpga/README.md) | Assumes Vivado 2022.2 in `~/Xilinx`, ADI Kuiper 2022_r2, and a `fpga_dev` branch. |
| Python CLI/TUI for the SDR tools | [host/python/btle_cli/README.md](../../host/python/btle_cli/README.md), [docs/MCP.md](../../host/python/btle_cli/docs/MCP.md) | Independent of the RTL. |
| USRP replay | [usrp_replay_example/README.md](../../usrp_replay_example/README.md) | |
| Supported HackRF/bladeRF library versions | [compatible_hackrf_bladerf_lib.txt](../../compatible_hackrf_bladerf_lib.txt) | |
| BLE background (third-party PDFs) | [docs/](../): `TI-BLE-INTRODUCTION.pdf`, `ibeacon.pdf`, `BLE_sniffer_guide.pdf` (upstream's `doc/` until 2026-10-06) | Not written by upstream. |
| Register map, hierarchy, clocks | not documented upstream | See [../Architecture/](../Architecture/). |

## External specification

The BLE Core Specification 5.3, Vol 6 (Low Energy Controller), Parts A
(physical layer) and B (link layer), is the reference that upstream follows.
T_IFS, channel selection and the PDU formats all come from Part B.
