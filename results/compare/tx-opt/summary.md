# Cross-branch comparison, run `tx-opt`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-opt` | `origin/ble-tx-opt` | `516a509` | `c76351d` | GAUSS_TABLE=1 |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Std cells | 50 295 | 48 559 (-3.5 %) |
| Flip-flops | 4 578 | 4 500 (-1.7 %) |
| Cell area (µm²) | 71 706 | 69 412 (-3.2 %) |
| SRAM bits | 1 136 070 | 1 111 494 (-2.2 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-opt` |
|---|---:|---:|
| `btle_controller` | 50 295 | 48 559 (-3.5 %) |
| `btle_phy` | 40 339 | 38 600 (-4.3 %) |
| `btle_rx` | 36 864 | 36 931 (+0.2 %) |
| `btle_tx` | 3 409 | 1 696 (-50.2 %) |
| `gauss_filter` | 2 286 | 253 (-88.9 %) |
| `btle_ll` | 9 453 | 9 453 (0) |
| `auxiliary_daemon` | 299 | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Unbuffered path | 6.073 ns | 6.689 ns (+10.1 %) |
| Logic path | 1.631 ns | 1.558 ns (-4.5 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) |
| Min period | 1.991 ns | 1.917 ns (-3.7 %) |
| Slack at 62.5 ns | 60.509 ns | 60.583 ns |
| Fmax | 502.3 MHz | 521.6 MHz (+3.8 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-opt` | `btle_phy_i.btle_rx_i.genblk1[0].btle_rx_core_i.gfsk_demodulation_i.i0[3]` | `btle_phy_i.btle_rx_i.genblk1[0].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-opt` |
|---|---:|---:|
| `rx` | 1.23e+09 | 1.21e+09 (-1.2 %) |
| `tx` | 1e+09 | 9.68e+08 (-3.1 %) |
| `mixed` | 1.25e+09 | 1.23e+09 (-1.8 %) |
| `idle` | 1.26e+09 | 1.24e+09 (-1.1 %) |
| `idle0` | 9.48e+08 | 9.33e+08 (-1.5 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Non-clock toggles / cycle | 920.3 | 920.8 (+0.1 %) |
| Nets with activity > 10 % | 517 | 515 (-0.4 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.53e+08 (+0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.61e+08 (-1.7 %) |
| **Data + clock** | 1.23e+09 | 1.21e+09 (-1.2 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-opt` |
|---|---:|---:|
| btle_rx | 819.0 | 819.6 (+0.1 %) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 41.7 | 41.7 (-0.1 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Non-clock toggles / cycle | 292.2 | 248.0 (-15.1 %) |
| Nets with activity > 10 % | 754 | 701 (-7.0 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.07e+08 (-13.4 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.61e+08 (-1.7 %) |
| **Data + clock** | 1e+09 | 9.68e+08 (-3.1 %) |
| RAM-port toggles | 2 745 143 | 2 718 637 (-1.0 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-opt` |
|---|---:|---:|
| btle_rx | 91.6 | 90.8 (-0.9 %) |
| gauss_filter | 79.1 | 24.8 (-68.6 %) |
| btle_tx (other) | 68.0 | 77.8 (+14.4 %) |
| btle_ll | 28.9 | 30.1 (+3.9 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) |
| clock_domain_conversion | 19.2 | 19.2 (0) |
| top glue | 7.1 | 7.1 (0) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Non-clock toggles / cycle | 984.3 | 962.7 (-2.2 %) |
| Nets with activity > 10 % | 839 | 837 (-0.2 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.65e+08 (-2.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.61e+08 (-1.7 %) |
| **Data + clock** | 1.25e+09 | 1.23e+09 (-1.8 %) |
| RAM-port toggles | 3 044 741 | 3 032 443 (-0.4 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-opt` |
|---|---:|---:|
| btle_rx | 791.1 | 791.5 (+0.1 %) |
| gauss_filter | 39.1 | 12.3 (-68.6 %) |
| btle_tx (other) | 37.4 | 42.3 (+12.9 %) |
| btle_ll | 41.5 | 41.5 (-0.1 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Non-clock toggles / cycle | 989.4 | 990.9 (+0.2 %) |
| Nets with activity > 10 % | 631 | 630 (-0.2 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (+0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.61e+08 (-1.7 %) |
| **Data + clock** | 1.26e+09 | 1.24e+09 (-1.1 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-opt` |
|---|---:|---:|
| btle_rx | 869.9 | 870.2 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 27.9 | 29.1 (+4.1 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-opt` |
|---|---:|---:|
| Non-clock toggles / cycle | 134.8 | 135.1 (+0.2 %) |
| Nets with activity > 10 % | 339 | 336 (-0.9 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.24e+07 (+0.3 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.61e+08 (-1.7 %) |
| **Data + clock** | 9.48e+08 | 9.33e+08 (-1.5 %) |
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
| `ble-tx-opt`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-opt`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
