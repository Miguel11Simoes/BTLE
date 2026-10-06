# Reproducing the upstream baseline

**Project:** BTLE — reconfigurable RISC-V baseband  
**Branch:** `risc-v-ble`  
**Base:** tag `upstream-baseline` (`8540186`)  
**Date:** 2026-09-18  
**Author:** Miguel Simões  
**Status:** procedure written from the upstream sources. **Not executed yet.**  
When a step is run, record the command, tool versions and outcome in
[../Validation/UPSTREAM_TEST_INVENTORY.md](../Validation/UPSTREAM_TEST_INVENTORY.md).

---

## Purpose

This guide gives the steps that produce the behaviour and area reference, to be
run before any change to the RTL. The steps are ordered by cost: the first ones
need only free tools, and the last ones need Vivado, a board or OpenLane.

## 0. Environment

The upstream scripts assume Linux (bash, `~/Xilinx/…` paths). On Windows, use
WSL2 with Ubuntu, and run everything from inside WSL.

```bash
sudo apt install iverilog gtkwave python3 python3-numpy python3-matplotlib cmake build-essential
git clone https://github.com/Miguel11Simoes/btle-riscv-tese.git
cd btle-riscv-tese
git checkout risc-v-ble
```

Submodules (`fpga/adi-hdl`, `BTLE-hw-img`) are only needed for step 5.
`fpga/adi-hdl` uses an SSH URL (`git@github.com:…`), so fetching it requires a
GitHub SSH key.

## 1. Generate the test vectors

```bash
cd python
python3 test_vector_for_btle_verilog.py 2        # example 2: LL_DATA, channel 10
```

This writes about thirty `.txt` files into `verilog/`. Examples 0 and 1 give
other packets, and the optional arguments are `snr ppm sample_delay`.

## 2. Unit testbenches (Icarus)

```bash
cd ../verilog
iverilog -o crc24_tb crc24_tb.v crc24.v crc24_core.v && vvp crc24_tb
iverilog -o scramble_tb scramble_tb.v scramble.v scramble_core.v && vvp scramble_tb
iverilog -o gauss_filter_tb gauss_filter_tb.v gauss_filter.v && vvp gauss_filter_tb
iverilog -o vco_tb vco_tb.v vco.v sdpram_one_clk.v && vvp vco_tb
iverilog -o gfsk_demodulation_tb gfsk_demodulation_tb.v gfsk_demodulation.v && vvp gfsk_demodulation_tb
iverilog -o search_unique_bit_sequence_tb search_unique_bit_sequence_tb.v search_unique_bit_sequence.v && vvp search_unique_bit_sequence_tb
```

Then run TX, RX core and RX with the commands in the headers of
`btle_tx_tb.v`, `btle_rx_core_tb.v` and `btle_rx_tb.v`. Expect `Test PASS` or
`0 difference found`.

## 3. Top-level testbench

Use the command in the header of `btle_controller_tb.v` as written. Keep
`uart_frame_rx.v`, `uart_frame_tx.v`, `rx_clk_gen.v` and `tx_clk_gen.v` in the
list: the copies inside `btle_ll.v` are excluded by
`` `ifdef AVOID_DUPLICATION ``, so these files are the only definitions.
Record the result.

## 4. Python model checks

```bash
cd ../python
python3 test_btle_ber.py
```

`test_alignment_with_btle_sdr.py` also needs the C tools:
`cd host && mkdir build && cd build && cmake .. && make`. That in turn needs
libhackrf (or libbladerf with `-DUSE_BLADERF=1`) installed, although no radio
has to be connected.

## 5. Area reference

Pick **one** of these, depending on decision D4 in
[../Design Decisions/SCOPE.md](../Design%20Decisions/SCOPE.md):

- **FPGA:** `verilog/btle_controller.sh` opens Vivado 2022.2 on the
  standalone controller (Zynq 7z020). Record LUT/FF/BRAM/DSP utilisation and
  timing.
- **ASIC:** run `open_btle_baseband_chip/open_btle_baseband_chip.ipynb` (Colab,
  OpenLane2, SKY130). Upstream reports that this flow **did not close** (STA
  fails on `btle_rx_core`, routing fails on the full design), so expect to fix
  constraints before the flow produces a usable number.

## 6. On the board (optional)

This needs an AntSDR, AntSDR E200 or SDRPi. Follow `fpga/README.md`: ADI
Kuiper image, `fpga/<board>/btle.sh`, `fpga/helpers/all_gen_and_scp.sh`,
`firmware/compile.sh`, then `host/ble_fpga_ctl`. It is only needed to show real
over-the-air behaviour, and is not required for the thesis baseline.
