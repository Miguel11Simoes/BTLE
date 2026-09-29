# Cross-branch comparison, run `tx-variants`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-table-reg` | `origin/ble-tx-table-reg` | `93a25cd` | `c8675f2` | GAUSS_TABLE=1 |
| `ble-tx-table-sram` | `origin/ble-tx-table-sram` | `1fe3534` | `3887f20` | GAUSS_TABLE=1 |
| `ble-tx-fir2` | `origin/ble-tx-fir2` | `f88d66f` | `07255a3` | <none: defaults> |
| `ble-tx-sin4` | `origin/ble-tx-sin4` | `3b9f7e8` | `fd4e70c` | <none: defaults> |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Std cells | 50 295 | 58 091 (+15.5 %) | 49 324 (-1.9 %) | 49 620 (-1.3 %) | 50 397 (+0.2 %) |
| Flip-flops | 4 578 | 7 222 (+57.8 %) | 4 667 (+1.9 %) | 4 570 (-0.2 %) | 4 581 (+0.1 %) |
| Cell area (µm²) | 71 706 | 91 556 (+27.7 %) | 70 896 (-1.1 %) | 70 652 (-1.5 %) | 71 863 (+0.2 %) |
| SRAM bits | 1 136 070 | 1 136 070 (0) | 1 138 630 (+0.2 %) | 1 136 070 (0) | 1 111 494 (-2.2 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| `btle_controller` | 50 295 | 58 091 (+15.5 %) | 49 324 (-1.9 %) | 49 620 (-1.3 %) | 50 397 (+0.2 %) |
| `btle_phy` | 40 339 | 48 192 (+19.5 %) | 39 294 (-2.6 %) | 39 655 (-1.7 %) | 40 384 (+0.1 %) |
| `btle_rx` | 36 864 | 36 954 (+0.2 %) | 36 954 (+0.2 %) | 36 980 (+0.3 %) | 36 884 (+0.1 %) |
| `btle_tx` | 3 409 | 11 328 (+232.3 %) | 2 477 (-27.3 %) | 2 707 (-20.6 %) | 3 465 (+1.6 %) |
| `gauss_filter` | 2 286 | 10 097 (+341.7 %) | 1 362 (-40.4 %) | 1 560 (-31.8 %) | 2 286 (0) |
| `btle_ll` | 9 453 | 9 453 (0) | 9 453 (0) | 9 453 (0) | 9 453 (0) |
| `auxiliary_daemon` | 299 | 299 (0) | 299 (0) | 299 (0) | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) | 183 (0) | 183 (0) | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Unbuffered path | 6.073 ns | 6.479 ns (+6.7 %) | 7.115 ns (+17.2 %) | 6.408 ns (+5.5 %) | 7.081 ns (+16.6 %) |
| Logic path | 1.631 ns | 1.636 ns (+0.3 %) | 1.652 ns (+1.3 %) | 1.517 ns (-7.0 %) | 1.647 ns (+1.0 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) | 0.359 ns (0) | 0.359 ns (0) | 0.359 ns (0) |
| Min period | 1.991 ns | 1.995 ns (+0.2 %) | 2.011 ns (+1.0 %) | 1.877 ns (-5.7 %) | 2.007 ns (+0.8 %) |
| Slack at 62.5 ns | 60.509 ns | 60.505 ns | 60.489 ns | 60.623 ns | 60.493 ns |
| Fmax | 502.3 MHz | 501.2 MHz (-0.2 %) | 497.2 MHz (-1.0 %) | 532.8 MHz (+6.1 %) | 498.3 MHz (-0.8 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-table-reg` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i0[6]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-table-sram` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.i0[6]` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-fir2` | `btle_phy_i.btle_rx_i.genblk1[3].btle_rx_core_i.gfsk_demodulation_i.i0[4]` | `btle_phy_i.btle_rx_i.genblk1[3].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-sin4` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.i0[6]` | `btle_phy_i.btle_rx_i.genblk1[6].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| `rx` | 1.23e+09 | 1.73e+09 (+40.8 %) | 1.25e+09 (+1.4 %) | 1.23e+09 (-0.1 %) | 1.23e+09 (0) |
| `tx` | 1e+09 | — | — | 9.89e+08 (-1.1 %) | 1e+09 (+0.4 %) |
| `mixed` | 1.25e+09 | 1.76e+09 (+40.8 %) | 1.26e+09 (+0.6 %) | 1.24e+09 (-0.5 %) | 1.25e+09 (+0.1 %) |
| `idle` | 1.26e+09 | 1.76e+09 (+39.9 %) | 1.27e+09 (+1.4 %) | 1.26e+09 (-0.1 %) | 1.26e+09 (0) |
| `idle0` | 9.48e+08 | 1.45e+09 (+53.0 %) | 9.65e+08 (+1.8 %) | 9.47e+08 (-0.1 %) | 9.48e+08 (0) |

### Scenario `rx`

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Non-clock toggles / cycle | 920.3 | 918.6 (-0.2 %) | 919.8 (-0.1 %) | 921.9 (+0.2 %) | 917.5 (-0.3 %) |
| Nets with activity > 10 % | 517 | 516 (-0.2 %) | 517 (0) | 519 (+0.4 %) | 514 (-0.6 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.52e+08 (-0.2 %) | 3.53e+08 (+0.1 %) | 3.53e+08 (0) | 3.51e+08 (-0.3 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 1.38e+09 (+57.3 %) | 8.93e+08 (+1.9 %) | 8.74e+08 (-0.2 %) | 8.76e+08 (+0.1 %) |
| **Data + clock** | 1.23e+09 | 1.73e+09 (+40.8 %) | 1.25e+09 (+1.4 %) | 1.23e+09 (-0.1 %) | 1.23e+09 (0) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) | 2 922 980 (+7.5 %) | 2 718 167 (0) | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| btle_rx | 819.0 | 816.2 (-0.3 %) | 816.8 (-0.3 %) | 819.3 (0) | 816.7 (-0.3 %) |
| gauss_filter | 0.0 | 1.0 (n/a) | 1.3 (n/a) | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) | 6.0 (0) | 6.0 (0) |
| btle_ll | 41.7 | 41.8 (+0.2 %) | 42.2 (+1.1 %) | 43.0 (+3.1 %) | 41.2 (-1.1 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) | 29.1 (0) | 29.1 (0) | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) | 20.3 (0) | 20.3 (0) | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) | 11.1 (0) | 11.1 (0) | 11.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Non-clock toggles / cycle | 984.3 | 988.0 (+0.4 %) | 958.7 (-2.6 %) | 971.0 (-1.4 %) | 987.0 (+0.3 %) |
| Nets with activity > 10 % | 839 | 836 (-0.4 %) | 824 (-1.8 %) | 841 (+0.2 %) | 851 (+1.4 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.8e+08 (+1.8 %) | 3.64e+08 (-2.5 %) | 3.68e+08 (-1.2 %) | 3.74e+08 (+0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 1.38e+09 (+57.3 %) | 8.93e+08 (+1.9 %) | 8.74e+08 (-0.2 %) | 8.76e+08 (+0.1 %) |
| **Data + clock** | 1.25e+09 | 1.76e+09 (+40.8 %) | 1.26e+09 (+0.6 %) | 1.24e+09 (-0.5 %) | 1.25e+09 (+0.1 %) |
| RAM-port toggles | 3 044 741 | 3 044 741 (0) | 3 373 130 (+10.8 %) | 3 044 741 (0) | 3 032 443 (-0.4 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| btle_rx | 791.1 | 788.2 (-0.4 %) | 788.9 (-0.3 %) | 791.4 (0) | 788.8 (-0.3 %) |
| gauss_filter | 39.1 | 45.6 (+16.4 %) | 15.4 (-60.8 %) | 24.2 (-38.1 %) | 39.1 (0) |
| btle_tx (other) | 37.4 | 37.4 (0) | 37.4 (0) | 37.4 (0) | 42.8 (+14.4 %) |
| btle_ll | 41.5 | 41.6 (+0.2 %) | 41.9 (+1.0 %) | 42.7 (+3.0 %) | 41.1 (-1.1 %) |
| auxiliary_daemon | 37.6 | 37.7 (+0.3 %) | 37.6 (0) | 37.6 (0) | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) | 32.3 (0) | 32.3 (0) | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) | 12.3 (0) | 12.3 (0) | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Non-clock toggles / cycle | 989.4 | 989.1 (0) | 990.3 (+0.1 %) | 991.3 (+0.2 %) | 987.3 (-0.2 %) |
| Nets with activity > 10 % | 631 | 627 (-0.6 %) | 634 (+0.5 %) | 638 (+1.1 %) | 629 (-0.3 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (0) | 3.82e+08 (+0.1 %) | 3.82e+08 (+0.1 %) | 3.81e+08 (-0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 1.38e+09 (+57.3 %) | 8.93e+08 (+1.9 %) | 8.74e+08 (-0.2 %) | 8.76e+08 (+0.1 %) |
| **Data + clock** | 1.26e+09 | 1.76e+09 (+39.9 %) | 1.27e+09 (+1.4 %) | 1.26e+09 (-0.1 %) | 1.26e+09 (0) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) | 3 300 863 (+6.6 %) | 3 096 050 (0) | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| btle_rx | 869.9 | 867.1 (-0.3 %) | 868.0 (-0.2 %) | 870.3 (+0.1 %) | 867.8 (-0.2 %) |
| gauss_filter | 0.0 | 1.0 (n/a) | 1.3 (n/a) | 0.0 (0) | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) | 6.0 (0) | 6.0 (0) | 6.0 (0) |
| btle_ll | 27.9 | 29.4 (+5.3 %) | 29.4 (+5.3 %) | 29.4 (+5.4 %) | 27.9 (0) |
| auxiliary_daemon | 41.8 | 41.8 (+0.1 %) | 41.8 (0) | 41.8 (0) | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) | 35.8 (0) | 35.8 (0) | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) | 15.0 (0) | 15.0 (0) | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-table-reg` | `ble-tx-table-sram` | `ble-tx-fir2` | `ble-tx-sin4` |
|---|---:|---:|---:|---:|---:|
| Non-clock toggles / cycle | 134.8 | 135.4 (+0.4 %) | 135.9 (+0.8 %) | 135.8 (+0.7 %) | 134.8 (0) |
| Nets with activity > 10 % | 339 | 335 (-1.2 %) | 338 (-0.3 %) | 340 (+0.3 %) | 335 (-1.2 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.23e+07 (+0.1 %) | 7.25e+07 (+0.4 %) | 7.25e+07 (+0.3 %) | 7.2e+07 (-0.3 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 1.38e+09 (+57.3 %) | 8.93e+08 (+1.9 %) | 8.74e+08 (-0.2 %) | 8.76e+08 (+0.1 %) |
| **Data + clock** | 9.48e+08 | 1.45e+09 (+53.0 %) | 9.65e+08 (+1.8 %) | 9.47e+08 (-0.1 %) | 9.48e+08 (0) |
| RAM-port toggles | 2 299 975 | 2 299 975 (0) | 2 504 788 (+8.9 %) | 2 299 975 (0) | 2 299 975 (0) |

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
| `ble-tx-table-reg`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-tx-table-sram`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-tx-fir2`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `ble-tx-sin4`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-table-reg`: gate-level outputs identical to upstream on every clock, 5 scenarios | **FAIL** |
| `ble-tx-table-sram`: gate-level outputs identical to upstream on every clock, 5 scenarios | **FAIL** |
| `ble-tx-fir2`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-sin4`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: FAIL
