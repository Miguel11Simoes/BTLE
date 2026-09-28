# Cross-branch comparison, run `all-branches`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-table` | `origin/ble-tx-table` | `eaaf6cf` | `2d36551` | GAUSS_TABLE=1 |
| `ble-rx-dm` | `origin/ble-rx-dm` | `92d6e54` | `aa807f8` | <none: defaults> |
| `ble-opt` | `ble-opt` | `f540e99` | `b78aa37` | ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1 |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Std cells | 50 295 | 48 227 (-4.1 %) | 23 346 (-53.6 %) | 16 102 (-68.0 %) |
| Flip-flops | 4 578 | 4 422 (-3.4 %) | 3 926 (-14.2 %) | 2 673 (-41.6 %) |
| Cell area (µm²) | 71 706 | 68 667 (-4.2 %) | 38 782 (-45.9 %) | 26 681 (-62.8 %) |
| SRAM bits | 1 136 070 | 1 136 070 (0) | 1 136 070 (0) | 87 046 (-92.3 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| `btle_controller` | 50 295 | 48 227 (-4.1 %) | 23 346 (-53.6 %) | 16 102 (-68.0 %) |
| `btle_phy` | 40 339 | 38 083 (-5.6 %) | 13 536 (-66.4 %) | 11 394 (-71.8 %) |
| `btle_rx` | 36 864 | 36 884 (+0.1 %) | 10 068 (-72.7 %) | 10 068 (-72.7 %) |
| `btle_tx` | 3 409 | 1 392 (-59.2 %) | 3 411 (+0.1 %) | 1 392 (-59.2 %) |
| `gauss_filter` | 2 286 | 253 (-88.9 %) | 2 286 (0) | 253 (-88.9 %) |
| `btle_ll` | 9 453 | 9 453 (0) | 9 453 (0) | 4 336 (-54.1 %) |
| `auxiliary_daemon` | 299 | 299 (0) | 299 (0) | 233 (-22.1 %) |
| `clock_domain_conversion_iq` | 183 | 183 (0) | 183 (0) | 183 (0) |

Additivity of the savings (std cells of `btle_controller`):

| Saving | Cells |
|---|---:|
| B2 alone (`ble-tx-table`) | 2 068 |
| B1 alone (`ble-rx-dm`) | 26 949 |
| A1 + A2, measured on their own tops (`auxiliary_daemon`, `btle_ll`) | 5 183 |
| **Sum of the parts** | **34 200** |
| **All together (`ble-opt`)** | **34 193** |
| Residual (interaction + flow noise) | -7 |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.546 ns (+7.8 %) | 3.913 ns (-35.6 %) | 4.044 ns (-33.4 %) |
| Logic path | 1.631 ns | 1.546 ns (-5.2 %) | 1.475 ns (-9.6 %) | 1.597 ns (-2.1 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) | 0.359 ns (0) | 0.347 ns (-3.3 %) |
| Min period | 1.991 ns | 1.905 ns (-4.3 %) | 1.834 ns (-7.9 %) | 1.944 ns (-2.4 %) |
| Slack at 62.5 ns | 60.509 ns | 60.595 ns | 60.666 ns | 60.556 ns |
| Fmax | 502.3 MHz | 524.9 MHz (+4.5 %) | 545.3 MHz (+8.6 %) | 514.3 MHz (+2.4 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-table` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[16]` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[76]` |
| `ble-rx-dm` | `btle_phy_i.btle_rx_i.gfsk_demodulation_shared_i.old_q[7]` | `btle_phy_i.btle_rx_i.gfsk_demodulation_shared_i.signal_for_decision[30]` |
| `ble-opt` | `btle_ll_i.gen_cross_bb_to_axi_min.clk_cross_bus_bb_to_s_axi_i.write_data[16]` | `btle_ll_i.gen_cross_bb_to_axi_min.clk_cross_bus_bb_to_s_axi_i.write_data[76]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| `rx` | 1.23e+09 | 1.2e+09 (-2.4 %) | 1.07e+09 (-12.9 %) | 8.2e+08 (-33.2 %) |
| `tx` | 1e+09 | 9.49e+08 (-5.0 %) | 9.19e+08 (-8.0 %) | 6.53e+08 (-34.7 %) |
| `mixed` | 1.25e+09 | 1.21e+09 (-3.2 %) | 1.13e+09 (-9.5 %) | 8.7e+08 (-30.3 %) |
| `idle` | 1.26e+09 | 1.23e+09 (-2.3 %) | 1.18e+09 (-5.9 %) | 9.37e+08 (-25.5 %) |
| `idle0` | 9.48e+08 | 9.18e+08 (-3.1 %) | 8.67e+08 (-8.5 %) | 6.22e+08 (-34.4 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Non-clock toggles / cycle | 920.3 | 918.9 (-0.1 %) | 837.0 (-9.1 %) | 797.7 (-13.3 %) |
| Nets with activity > 10 % | 517 | 516 (-0.2 %) | 2 757 (+433.3 %) | 2 664 (+415.3 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.52e+08 (-0.1 %) | 3.18e+08 (-9.8 %) | 3.07e+08 (-13.0 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.46e+08 (-3.4 %) | 7.52e+08 (-14.1 %) | 5.14e+08 (-41.4 %) |
| **Data + clock** | 1.23e+09 | 1.2e+09 (-2.4 %) | 1.07e+09 (-12.9 %) | 8.2e+08 (-33.2 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) | 2 718 167 (0) | 1 609 287 (-40.8 %) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| btle_rx | 819.0 | 818.5 (-0.1 %) | 735.3 (-10.2 %) | 732.2 (-10.6 %) |
| gauss_filter | 0.0 | 0.0 (0) | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) | 6.0 (0) |
| btle_ll | 41.7 | 40.9 (-2.0 %) | 42.0 (+0.8 %) | 11.3 (-73.0 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) | 29.1 (0) | 23.8 (-18.2 %) |
| clock_domain_conversion | 20.3 | 20.3 (0) | 20.3 (0) | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) | 11.1 (0) | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Non-clock toggles / cycle | 292.2 | 237.5 (-18.7 %) | 405.7 (+38.8 %) | 328.5 (+12.4 %) |
| Nets with activity > 10 % | 754 | 661 (-12.3 %) | 850 (+12.7 %) | 706 (-6.4 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.03e+08 (-16.6 %) | 1.68e+08 (+35.3 %) | 1.39e+08 (+12.5 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.46e+08 (-3.4 %) | 7.52e+08 (-14.1 %) | 5.14e+08 (-41.4 %) |
| **Data + clock** | 1e+09 | 9.49e+08 (-5.0 %) | 9.19e+08 (-8.0 %) | 6.53e+08 (-34.7 %) |
| RAM-port toggles | 2 745 143 | 2 745 143 (0) | 2 745 143 (0) | 2 045 158 (-25.5 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| btle_rx | 91.6 | 90.1 (-1.7 %) | 206.1 (+125.0 %) | 205.3 (+124.1 %) |
| gauss_filter | 79.1 | 25.4 (-67.9 %) | 79.1 (0) | 24.8 (-68.6 %) |
| btle_tx (other) | 68.0 | 68.0 (0) | 66.8 (-1.7 %) | 68.6 (+0.9 %) |
| btle_ll | 28.9 | 29.4 (+1.7 %) | 29.0 (+0.4 %) | 10.5 (-63.8 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) | 5.3 (0) | 0.0 (-100.0 %) |
| clock_domain_conversion | 19.2 | 19.2 (0) | 19.2 (0) | 19.2 (0) |
| top glue | 7.1 | 7.1 (0) | 7.1 (0) | 7.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Non-clock toggles / cycle | 984.3 | 956.4 (-2.8 %) | 1004.5 (+2.1 %) | 939.7 (-4.5 %) |
| Nets with activity > 10 % | 839 | 827 (-1.4 %) | 4 002 (+377.0 %) | 3 908 (+365.8 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.62e+08 (-2.8 %) | 3.78e+08 (+1.5 %) | 3.57e+08 (-4.3 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.46e+08 (-3.4 %) | 7.52e+08 (-14.1 %) | 5.14e+08 (-41.4 %) |
| **Data + clock** | 1.25e+09 | 1.21e+09 (-3.2 %) | 1.13e+09 (-9.5 %) | 8.7e+08 (-30.3 %) |
| RAM-port toggles | 3 044 741 | 3 044 741 (0) | 3 044 741 (0) | 1 826 225 (-40.0 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| btle_rx | 791.1 | 790.6 (-0.1 %) | 811.5 (+2.6 %) | 808.8 (+2.2 %) |
| gauss_filter | 39.1 | 12.6 (-67.8 %) | 39.1 (0) | 12.3 (-68.6 %) |
| btle_tx (other) | 37.4 | 37.4 (0) | 36.9 (-1.5 %) | 37.7 (+0.8 %) |
| btle_ll | 41.5 | 40.6 (-2.0 %) | 41.7 (+0.6 %) | 11.0 (-73.4 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) | 37.7 (+0.3 %) | 32.3 (-14.3 %) |
| clock_domain_conversion | 32.3 | 32.3 (0) | 32.3 (0) | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) | 12.3 (0) | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Non-clock toggles / cycle | 989.4 | 989.6 (0) | 1128.7 (+14.1 %) | 1101.5 (+11.3 %) |
| Nets with activity > 10 % | 631 | 634 (+0.5 %) | 4 247 (+573.1 %) | 4 180 (+562.4 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (+0.1 %) | 4.31e+08 (+12.9 %) | 4.23e+08 (+10.8 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.46e+08 (-3.4 %) | 7.52e+08 (-14.1 %) | 5.14e+08 (-41.4 %) |
| **Data + clock** | 1.26e+09 | 1.23e+09 (-2.3 %) | 1.18e+09 (-5.9 %) | 9.37e+08 (-25.5 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) | 3 096 050 (0) | 1 599 990 (-48.3 %) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| btle_rx | 869.9 | 869.6 (0) | 1009.0 (+16.0 %) | 1006.0 (+15.6 %) |
| gauss_filter | 0.0 | 0.0 (0) | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) | 6.0 (0) |
| btle_ll | 27.9 | 28.4 (+1.8 %) | 28.0 (+0.4 %) | 9.5 (-66.1 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) | 41.8 (+0.1 %) | 36.3 (-13.1 %) |
| clock_domain_conversion | 35.8 | 35.8 (0) | 35.8 (0) | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) | 15.0 (0) | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-table` | `ble-rx-dm` | `ble-opt` |
|---|---:|---:|---:|---:|
| Non-clock toggles / cycle | 134.8 | 133.8 (-0.8 %) | 249.4 (+85.0 %) | 224.8 (+66.7 %) |
| Nets with activity > 10 % | 339 | 337 (-0.6 %) | 439 (+29.5 %) | 384 (+13.3 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.21e+07 (-0.1 %) | 1.15e+08 (+59.8 %) | 1.08e+08 (+49.6 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.46e+08 (-3.4 %) | 7.52e+08 (-14.1 %) | 5.14e+08 (-41.4 %) |
| **Data + clock** | 9.48e+08 | 9.18e+08 (-3.1 %) | 8.67e+08 (-8.5 %) | 6.22e+08 (-34.4 %) |
| RAM-port toggles | 2 299 975 | 2 299 975 (0) | 2 299 975 (0) | 1 599 990 (-30.4 %) |

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
| `ble-tx-table`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-rx-dm`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-opt`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-table`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-rx-dm`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-opt`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
