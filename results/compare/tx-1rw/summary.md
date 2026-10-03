# Cross-branch comparison, run `tx-1rw`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-sin8-1rw` | `origin/ble-tx-sin8-1rw` | `fca3f53` | `132cca8` | <none: defaults> |
| `ble-tx-sin2` | `origin/ble-tx-sin2` | `35bca90` | `833ee9d` | <none: defaults> |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Std cells | 50 295 | 50 708 (+0.8 %) | 50 621 (+0.6 %) |
| Flip-flops | 4 578 | 4 642 (+1.4 %) | 4 639 (+1.3 %) |
| Cell area (µm²) | 71 706 | 72 414 (+1.0 %) | 72 278 (+0.8 %) |
| SRAM bits | 1 136 070 | 1 111 494 (-2.2 %) | 1 107 398 (-2.5 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| `btle_controller` | 50 295 | 50 708 (+0.8 %) | 50 621 (+0.6 %) |
| `btle_phy` | 40 339 | 40 550 (+0.5 %) | 40 593 (+0.6 %) |
| `btle_rx` | 36 864 | 36 952 (+0.2 %) | 36 928 (+0.2 %) |
| `btle_tx` | 3 409 | 3 729 (+9.4 %) | 3 687 (+8.2 %) |
| `gauss_filter` | 2 286 | 2 286 (0) | 2 286 (0) |
| `btle_ll` | 9 453 | 9 453 (0) | 9 453 (0) |
| `auxiliary_daemon` | 299 | 299 (0) | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.120 ns (+0.8 %) | 6.195 ns (+2.0 %) |
| Logic path | 1.631 ns | 1.614 ns (-1.0 %) | 1.578 ns (-3.2 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) | 0.359 ns (0) |
| Min period | 1.991 ns | 1.974 ns (-0.9 %) | 1.938 ns (-2.7 %) |
| Slack at 62.5 ns | 60.509 ns | 60.526 ns | 60.562 ns |
| Fmax | 502.3 MHz | 506.6 MHz (+0.9 %) | 516.0 MHz (+2.7 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-sin8-1rw` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.i0[6]` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-sin2` | `btle_phy_i.btle_rx_i.genblk1[0].btle_rx_core_i.gfsk_demodulation_i.i0[3]` | `btle_phy_i.btle_rx_i.genblk1[0].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| `rx` | 1.23e+09 | 1.24e+09 (+1.0 %) | 1.24e+09 (+0.9 %) |
| `tx` | 1e+09 | 1.02e+09 (+1.9 %) | 1.03e+09 (+3.4 %) |
| `mixed` | 1.25e+09 | 1.26e+09 (+1.3 %) | 1.27e+09 (+1.8 %) |
| `idle` | 1.26e+09 | 1.27e+09 (+1.0 %) | 1.27e+09 (+0.9 %) |
| `idle0` | 9.48e+08 | 9.6e+08 (+1.3 %) | 9.6e+08 (+1.2 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Non-clock toggles / cycle | 920.3 | 920.8 (+0.1 %) | 921.1 (+0.1 %) |
| Nets with activity > 10 % | 517 | 520 (+0.6 %) | 518 (+0.2 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.53e+08 (+0.1 %) | 3.52e+08 (0) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.88e+08 (+1.4 %) | 8.87e+08 (+1.3 %) |
| **Data + clock** | 1.23e+09 | 1.24e+09 (+1.0 %) | 1.24e+09 (+0.9 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| btle_rx | 819.0 | 819.3 (0) | 819.8 (+0.1 %) |
| gauss_filter | 0.0 | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) |
| btle_ll | 41.7 | 41.9 (+0.5 %) | 41.8 (+0.1 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Non-clock toggles / cycle | 292.2 | 310.2 (+6.2 %) | 346.6 (+18.6 %) |
| Nets with activity > 10 % | 754 | 839 (+11.3 %) | 915 (+21.4 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.3e+08 (+5.3 %) | 1.46e+08 (+18.0 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.88e+08 (+1.4 %) | 8.87e+08 (+1.3 %) |
| **Data + clock** | 1e+09 | 1.02e+09 (+1.9 %) | 1.03e+09 (+3.4 %) |
| RAM-port toggles | 2 745 143 | 2 718 637 (-1.0 %) | 3 174 938 (+15.7 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| btle_rx | 91.6 | 90.3 (-1.5 %) | 91.6 (0) |
| gauss_filter | 79.1 | 79.1 (0) | 79.1 (0) |
| btle_tx (other) | 68.0 | 86.7 (+27.6 %) | 122.2 (+79.7 %) |
| btle_ll | 28.9 | 29.5 (+2.0 %) | 29.1 (+0.6 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) | 5.3 (0) |
| clock_domain_conversion | 19.2 | 19.2 (0) | 19.2 (0) |
| top glue | 7.1 | 7.1 (0) | 7.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Non-clock toggles / cycle | 984.3 | 994.3 (+1.0 %) | 1012.1 (+2.8 %) |
| Nets with activity > 10 % | 839 | 882 (+5.1 %) | 951 (+13.3 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.77e+08 (+1.0 %) | 3.84e+08 (+2.9 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.88e+08 (+1.4 %) | 8.87e+08 (+1.3 %) |
| **Data + clock** | 1.25e+09 | 1.26e+09 (+1.3 %) | 1.27e+09 (+1.8 %) |
| RAM-port toggles | 3 044 741 | 3 032 443 (-0.4 %) | 3 258 655 (+7.0 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| btle_rx | 791.1 | 791.5 (+0.1 %) | 792.1 (+0.1 %) |
| gauss_filter | 39.1 | 39.1 (0) | 39.1 (0) |
| btle_tx (other) | 37.4 | 46.8 (+24.9 %) | 64.3 (+71.9 %) |
| btle_ll | 41.5 | 41.7 (+0.6 %) | 41.5 (-0.1 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Non-clock toggles / cycle | 989.4 | 990.5 (+0.1 %) | 990.7 (+0.1 %) |
| Nets with activity > 10 % | 631 | 638 (+1.1 %) | 635 (+0.6 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (+0.2 %) | 3.82e+08 (+0.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.88e+08 (+1.4 %) | 8.87e+08 (+1.3 %) |
| **Data + clock** | 1.26e+09 | 1.27e+09 (+1.0 %) | 1.27e+09 (+0.9 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| btle_rx | 869.9 | 870.4 (+0.1 %) | 871.0 (+0.1 %) |
| gauss_filter | 0.0 | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) |
| btle_ll | 27.9 | 28.5 (+2.1 %) | 28.1 (+0.7 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-sin8-1rw` | `ble-tx-sin2` |
|---|---:|---:|---:|
| Non-clock toggles / cycle | 134.8 | 134.1 (-0.6 %) | 135.0 (+0.1 %) |
| Nets with activity > 10 % | 339 | 344 (+1.5 %) | 343 (+1.2 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.2e+07 (-0.3 %) | 7.24e+07 (+0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.88e+08 (+1.4 %) | 8.87e+08 (+1.3 %) |
| **Data + clock** | 9.48e+08 | 9.6e+08 (+1.3 %) | 9.6e+08 (+1.2 %) |
| RAM-port toggles | 2 299 975 | 2 299 975 (0) | 2 299 975 (0) |

## Consistency checks

| Check | Result |
|---|---|
| `master` controller cells equal the committed run `baseline-upstream` (50 295) | PASS |
| upstream controller timed identically in every run (period and path) | PASS |
| `master` dut controller timed identically to the upstream reference | PASS |
| upstream side identical in every run, scenario `rx` | PASS |
| `master` equals upstream exactly, scenario `rx` | PASS |
| upstream side identical in every run, scenario `tx` | PASS |
| `master` equals upstream exactly, scenario `tx` | PASS |
| upstream side identical in every run, scenario `mixed` | PASS |
| `master` equals upstream exactly, scenario `mixed` | PASS |
| upstream side identical in every run, scenario `idle` | PASS |
| `master` equals upstream exactly, scenario `idle` | PASS |
| upstream side identical in every run, scenario `idle0` | PASS |
| `master` equals upstream exactly, scenario `idle0` | PASS |
| `master`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-tx-sin8-1rw`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-tx-sin2`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-sin8-1rw`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-sin2`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
