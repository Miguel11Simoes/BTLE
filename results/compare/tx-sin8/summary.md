# Cross-branch comparison, run `tx-sin8`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-sin8` | `origin/ble-tx-sin8` | `e1847f9` | `8ba2c0e` | <none: defaults> |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Std cells | 50 295 | 50 716 (+0.8 %) |
| Flip-flops | 4 578 | 4 656 (+1.7 %) |
| Cell area (µm²) | 71 706 | 72 484 (+1.1 %) |
| SRAM bits | 1 136 070 | 1 111 494 (-2.2 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-sin8` |
|---|---:|---:|
| `btle_controller` | 50 295 | 50 716 (+0.8 %) |
| `btle_phy` | 40 339 | 40 573 (+0.6 %) |
| `btle_rx` | 36 864 | 36 928 (+0.2 %) |
| `btle_tx` | 3 409 | 3 718 (+9.1 %) |
| `gauss_filter` | 2 286 | 2 286 (0) |
| `btle_ll` | 9 453 | 9 453 (0) |
| `auxiliary_daemon` | 299 | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Unbuffered path | 6.073 ns | 6.251 ns (+2.9 %) |
| Logic path | 1.631 ns | 1.550 ns (-5.0 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) |
| Min period | 1.991 ns | 1.910 ns (-4.1 %) |
| Slack at 62.5 ns | 60.509 ns | 60.590 ns |
| Fmax | 502.3 MHz | 523.6 MHz (+4.2 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-sin8` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[16]` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[76]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-sin8` |
|---|---:|---:|
| `rx` | 1.23e+09 | 1.24e+09 (+1.2 %) |
| `tx` | 1e+09 | 1.02e+09 (+1.8 %) |
| `mixed` | 1.25e+09 | 1.27e+09 (+1.3 %) |
| `idle` | 1.26e+09 | 1.27e+09 (+1.2 %) |
| `idle0` | 9.48e+08 | 9.62e+08 (+1.5 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Non-clock toggles / cycle | 920.3 | 921.1 (+0.1 %) |
| Nets with activity > 10 % | 517 | 510 (-1.4 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.52e+08 (-0.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.91e+08 (+1.7 %) |
| **Data + clock** | 1.23e+09 | 1.24e+09 (+1.2 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-sin8` |
|---|---:|---:|
| btle_rx | 819.0 | 819.1 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 41.7 | 42.4 (+1.6 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Non-clock toggles / cycle | 292.2 | 301.7 (+3.2 %) |
| Nets with activity > 10 % | 754 | 784 (+4.0 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.27e+08 (+2.8 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.91e+08 (+1.7 %) |
| **Data + clock** | 1e+09 | 1.02e+09 (+1.8 %) |
| RAM-port toggles | 2 745 143 | 2 718 637 (-1.0 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-sin8` |
|---|---:|---:|
| btle_rx | 91.6 | 89.9 (-1.8 %) |
| gauss_filter | 79.1 | 79.1 (0) |
| btle_tx (other) | 68.0 | 77.1 (+13.5 %) |
| btle_ll | 28.9 | 30.9 (+6.9 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) |
| clock_domain_conversion | 19.2 | 19.2 (0) |
| top glue | 7.1 | 7.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Non-clock toggles / cycle | 984.3 | 989.4 (+0.5 %) |
| Nets with activity > 10 % | 839 | 845 (+0.7 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.74e+08 (+0.4 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.91e+08 (+1.7 %) |
| **Data + clock** | 1.25e+09 | 1.27e+09 (+1.3 %) |
| RAM-port toggles | 3 044 741 | 3 032 443 (-0.4 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-sin8` |
|---|---:|---:|
| btle_rx | 791.1 | 791.0 (0) |
| gauss_filter | 39.1 | 39.1 (0) |
| btle_tx (other) | 37.4 | 42.0 (+12.1 %) |
| btle_ll | 41.5 | 42.2 (+1.6 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Non-clock toggles / cycle | 989.4 | 991.0 (+0.2 %) |
| Nets with activity > 10 % | 631 | 623 (-1.3 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (0) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.91e+08 (+1.7 %) |
| **Data + clock** | 1.26e+09 | 1.27e+09 (+1.2 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-sin8` |
|---|---:|---:|
| btle_rx | 869.9 | 869.5 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 27.9 | 29.9 (+7.1 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-sin8` |
|---|---:|---:|
| Non-clock toggles / cycle | 134.8 | 135.1 (+0.2 %) |
| Nets with activity > 10 % | 339 | 326 (-3.8 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.19e+07 (-0.5 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.91e+08 (+1.7 %) |
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
| `ble-tx-sin8`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-sin8`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
