# Cross-branch comparison, run `tx-1--8`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-1--8` | `origin/ble-tx-1--8` | `7e893fd` | `7ff12d1` | <none: defaults> |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Std cells | 50 295 | 50 904 (+1.2 %) |
| Flip-flops | 4 578 | 4 654 (+1.7 %) |
| Cell area (µm²) | 71 706 | 72 617 (+1.3 %) |
| SRAM bits | 1 136 070 | 1 107 398 (-2.5 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-1--8` |
|---|---:|---:|
| `btle_controller` | 50 295 | 50 904 (+1.2 %) |
| `btle_phy` | 40 339 | 40 964 (+1.5 %) |
| `btle_rx` | 36 864 | 36 951 (+0.2 %) |
| `btle_tx` | 3 409 | 3 939 (+15.5 %) |
| `gauss_filter` | 2 286 | 2 286 (0) |
| `btle_ll` | 9 453 | 9 453 (0) |
| `auxiliary_daemon` | 299 | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Unbuffered path | 6.073 ns | 6.243 ns (+2.8 %) |
| Logic path | 1.631 ns | 1.590 ns (-2.5 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) |
| Min period | 1.991 ns | 1.949 ns (-2.1 %) |
| Slack at 62.5 ns | 60.509 ns | 60.551 ns |
| Fmax | 502.3 MHz | 513.1 MHz (+2.2 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-1--8` | `btle_phy_i.btle_rx_i.genblk1[3].btle_rx_core_i.gfsk_demodulation_i.i0[6]` | `btle_phy_i.btle_rx_i.genblk1[3].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-1--8` |
|---|---:|---:|
| `rx` | 1.23e+09 | 1.24e+09 (+1.2 %) |
| `tx` | 1e+09 | 1.02e+09 (+2.3 %) |
| `mixed` | 1.25e+09 | 1.27e+09 (+1.5 %) |
| `idle` | 1.26e+09 | 1.27e+09 (+1.2 %) |
| `idle0` | 9.48e+08 | 9.62e+08 (+1.5 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Non-clock toggles / cycle | 920.3 | 920.2 (0) |
| Nets with activity > 10 % | 517 | 519 (+0.4 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.53e+08 (0) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.9e+08 (+1.6 %) |
| **Data + clock** | 1.23e+09 | 1.24e+09 (+1.2 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-1--8` |
|---|---:|---:|
| btle_rx | 819.0 | 818.7 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 41.7 | 41.8 (+0.3 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Non-clock toggles / cycle | 292.2 | 316.3 (+8.2 %) |
| Nets with activity > 10 % | 754 | 862 (+14.3 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.33e+08 (+7.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.9e+08 (+1.6 %) |
| **Data + clock** | 1e+09 | 1.02e+09 (+2.3 %) |
| RAM-port toggles | 2 745 143 | 2 711 198 (-1.2 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-1--8` |
|---|---:|---:|
| btle_rx | 91.6 | 91.8 (+0.2 %) |
| gauss_filter | 79.1 | 79.1 (0) |
| btle_tx (other) | 68.0 | 91.8 (+35.0 %) |
| btle_ll | 28.9 | 29.0 (+0.4 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) |
| clock_domain_conversion | 19.2 | 19.2 (0) |
| top glue | 7.1 | 7.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Non-clock toggles / cycle | 984.3 | 996.0 (+1.2 %) |
| Nets with activity > 10 % | 839 | 887 (+5.7 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.77e+08 (+1.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.9e+08 (+1.6 %) |
| **Data + clock** | 1.25e+09 | 1.27e+09 (+1.5 %) |
| RAM-port toggles | 3 044 741 | 3 028 595 (-0.5 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-1--8` |
|---|---:|---:|
| btle_rx | 791.1 | 790.9 (0) |
| gauss_filter | 39.1 | 39.1 (0) |
| btle_tx (other) | 37.4 | 49.2 (+31.5 %) |
| btle_ll | 41.5 | 41.5 (+0.1 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Non-clock toggles / cycle | 989.4 | 989.1 (0) |
| Nets with activity > 10 % | 631 | 634 (+0.5 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (0) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.9e+08 (+1.6 %) |
| **Data + clock** | 1.26e+09 | 1.27e+09 (+1.2 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-1--8` |
|---|---:|---:|
| btle_rx | 869.9 | 869.5 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 27.9 | 28.0 (+0.4 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-1--8` |
|---|---:|---:|
| Non-clock toggles / cycle | 134.8 | 135.1 (+0.2 %) |
| Nets with activity > 10 % | 339 | 341 (+0.6 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.23e+07 (+0.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.9e+08 (+1.6 %) |
| **Data + clock** | 9.48e+08 | 9.62e+08 (+1.5 %) |
| RAM-port toggles | 2 299 975 | 2 299 975 (0) |

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
| `ble-tx-1--8`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-1--8`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
