# Upstream test inventory

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  
**Status:** inventory only. **No test has been executed in this fork yet.**  

---

## Purpose

This inventory lists what upstream can test, how each test gets its inputs,
and what is missing. It is the checklist for the reproduction step in
[../02 Design Decisions/SCOPE.md](../02%20Design%20Decisions/SCOPE.md), section 6.
The results column stays empty until a run produces a log. A test that has not
been run is not reported as passing.

## 1. How the RTL tests work

The testbenches take **no hand-written vectors**. They compare the RTL against
the Python bit-true model:

```
python/btlelib.py ──(test_vector_for_btle_verilog.py <example> [snr] [ppm] [delay])──►
    verilog/*.txt      (inputs and *_ref.txt expected outputs)
        │
        ▼
verilog/*_tb.v  (Icarus Verilog)  ──►  verilog/*_output*.txt, "Test PASS" / "difference found"
```

`test_vector_for_btle_verilog.py` writes into `../verilog/`, so it must be run
from `python/`. It has three built-in packets:

| `example_idx` | Packet | Channel |
|---|---|---|
| 0 | ADV discovery, `LOCAL_NAME09-SDR/Bluetooth/Low/Energy` | 37 |
| 1 | `LL_CONNECTION_UPDATE_REQ` | 9 |
| 2 | `LL_DATA`, empty payload, AA `11850A1B`, CRC init `123456` | 10 |

The optional arguments add channel impairments: SNR in dB (default 20), clock
error in ppm (default 0), and a sample delay (default 0). None of the generated
`.txt` files is committed. `.gitignore` excludes them.

## 2. RTL testbenches

Each command comes from the testbench's own header comment and is run from
`verilog/`.

| Testbench | DUT | Command (from the header) | Result |
|---|---|---|---|
| `crc24_tb.v` | CRC-24 | `iverilog -o crc24_tb crc24_tb.v crc24.v crc24_core.v` | not run |
| `scramble_tb.v` | Whitening | `iverilog -o scramble_tb scramble_tb.v scramble.v scramble_core.v` | not run |
| `bit_repeat_upsample_tb.v` | 8× upsampler | `iverilog -o bit_repeat_upsample_tb bit_repeat_upsample_tb.v bit_repeat_upsample.v` | not run |
| `gauss_filter_tb.v` | Gaussian FIR | `iverilog -o gauss_filter_tb gauss_filter_tb.v gauss_filter.v` | not run |
| `vco_tb.v` | COS/SIN VCO | `iverilog -o vco_tb vco_tb.v vco.v sdpram_one_clk.v` | not run |
| `gfsk_demodulation_tb.v` | GFSK demodulator | `iverilog -o gfsk_demodulation_tb gfsk_demodulation_tb.v gfsk_demodulation.v` | not run |
| `search_unique_bit_sequence_tb.v` | AA search | `iverilog -o search_unique_bit_sequence_tb search_unique_bit_sequence_tb.v search_unique_bit_sequence.v` | not run |
| `btle_tx_tb.v` | Full TX | see the header of `btle_tx_tb.v` | not run |
| `btle_rx_core_tb.v` | RX core | see the header of `btle_rx_core_tb.v` | not run |
| `btle_rx_tb.v` | Full RX | see the header of `btle_rx_tb.v` | not run |
| `btle_controller_tb.v` | PHY + LL + top | see the header; **expected to fail as written** (below) | not run |

Each testbench is followed by `vvp <name>`. A pass prints `Test PASS`, or
`0 difference found` for the RX/TX comparisons.

**Expected problem with `btle_controller_tb`:** its header command compiles
`btle_ll.v` **and** `uart_frame_rx.v`, `uart_frame_tx.v`, `rx_clk_gen.v` and
`tx_clk_gen.v`, and `btle_ll.v` already defines those modules (issue U1 in
[../01 Architecture/UPSTREAM_ARCHITECTURE.md](../01%20Architecture/UPSTREAM_ARCHITECTURE.md)).
Icarus normally rejects duplicate modules. Dropping the four separate files
from the command should work, but that is to be confirmed when it runs.

**No testbench covers `btle_ll.v` on its own.** The AXI-lite registers, the RX
PDU RAM and the counters are exercised only inside `btle_controller_tb`, and
only in `baremetal_phy_intf_mode = 1`, which bypasses the LL registers. The
path the boards actually use (mode 0, registers) has **no simulation coverage
upstream**.

## 3. Python model tests

Run from `python/`.

| Script | Checks | Needs |
|---|---|---|
| `test_alignment_with_btle_sdr.py <example>` | Python TX against the C `btle_tx`, compared by instantaneous frequency | `host/build/btle-tools/src/btle_tx` built |
| `test_btle_ber.py` | BER against SNR and clock error (upstream claims 0.1 % at 11.5 dB SNR with 20 ppm) | numpy, matplotlib |
| `test_btle_rx_by_captured_iq.py <file.bin>` | Decodes IQ captured on the board | a capture from `btle_ll -q` |

## 4. Host tools

| Test | Command | Needs |
|---|---|---|
| `btle_cli` unit tests | `cd host/python/btle_cli && pytest` (5 test files, `tests/`) | Python ≥ 3.11 |
| C tools build | `cd host && mkdir build && cd build && cmake .. && make` | libhackrf or libbladerf |

## 5. Hardware flows

| Flow | Entry point | Upstream result | Reproduced |
|---|---|---|---|
| Vivado, standalone controller | `verilog/btle_controller.sh` / `.tcl` (Zynq 7z020) | Utilisation image in `open_btle_baseband_chip/btle_controller_xilinx_7z020.jpg` | no |
| Vivado, board | `fpga/<board>/btle.sh` | Bitstream and boot image | no |
| OpenLane2, SKY130 | Colab notebook `open_btle_baseband_chip.ipynb` | `btle_rx_core` GDSII with **post-PnR STA failing**; full design **global routing failing** | no |

## 6. Gaps that matter for the thesis

1. The register path the boards use (mode 0) is not simulated.
2. No test measures the RX→TX turnaround, because upstream never transmits in response to a received packet.
3. No closed ASIC area or timing number exists for the full design.
4. No regression script runs the testbenches together. Each one is started by hand.

Closing gaps 1 and 4 comes before any RISC-V work, because they are the
oracle for "nothing regressed".
