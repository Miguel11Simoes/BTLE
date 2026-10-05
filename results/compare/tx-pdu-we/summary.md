# Cross-branch comparison, run `tx-pdu-we`

Each branch in its own configuration, measured in one run with the same flows (Yosys 0.68 + ABC, Nangate45, SRAMs as macros; ABC `stime` register to register; Verilator gate-level simulation, 100 000-cycle windows, one shared vector set: `vectors.tar.gz`). Differences are relative to `master`.

## Configurations

| Branch | Measured revision | Commit | `verilog/` tree | Parameters |
|---|---|---|---|---|
| `master` | `upstream-baseline` | `8540186` | `4bacca3` | <none: defaults> |
| `ble-tx-pdu-we` | `ble-tx-pdu-we` | `eec6c8f` | `f61412f` | GAUSS_TABLE=1 PDU_WRITE_STROBE=1 |

## Area, `btle_controller`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Std cells | 50 295 | 48 056 (-4.5 %) |
| Flip-flops | 4 578 | 4 432 (-3.2 %) |
| Cell area (µm²) | 71 706 | 68 767 (-4.1 %) |
| SRAM bits | 1 136 070 | 1 105 350 (-2.7 %) |

Std cells per top (each top synthesised alone):

| Top | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| `btle_controller` | 50 295 | 48 056 (-4.5 %) |
| `btle_phy` | 40 339 | 38 136 (-5.5 %) |
| `btle_rx` | 36 864 | 36 910 (+0.1 %) |
| `btle_tx` | 3 409 | 1 299 (-61.9 %) |
| `gauss_filter` | 2 286 | 166 (-92.7 %) |
| `btle_ll` | 9 453 | 9 478 (+0.3 %) |
| `auxiliary_daemon` | 299 | 299 (0) |
| `clock_domain_conversion_iq` | 183 | 183 (0) |

## Static timing, `btle_controller`, 62.5 ns (16 MHz)

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Unbuffered path | 6.073 ns | 7.146 ns (+17.7 %) |
| Logic path | 1.631 ns | 1.690 ns (+3.6 %) |
| Register overhead | 0.359 ns | 0.359 ns (0) |
| Min period | 1.991 ns | 2.050 ns (+3.0 %) |
| Slack at 62.5 ns | 60.509 ns | 60.450 ns |
| Fmax | 502.3 MHz | 487.9 MHz (-2.9 %) |

| Branch | Worst path start | End |
|---|---|---|
| `master` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.i1[5]` | `btle_phy_i.btle_rx_i.genblk1[2].btle_rx_core_i.gfsk_demodulation_i.signal_for_decision[31]` |
| `ble-tx-pdu-we` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[16]` | `btle_ll_i.clk_cross_bus_bb_to_s_axi_i.write_data[76]` |

## Switching activity (gate level, same stimuli, 100 000 cycles per scenario)

Data + clock pin switched capacitance (liberty pin capacitance × toggles, no wires): a pre-layout proxy, not power. Δ against upstream in the same simulation.

| Scenario | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| `rx` | 1.23e+09 | 1.2e+09 (-2.2 %) |
| `tx` | 1e+09 | 9.74e+08 (-2.6 %) |
| `mixed` | 1.25e+09 | 1.22e+09 (-2.1 %) |
| `idle` | 1.26e+09 | 1.23e+09 (-2.2 %) |
| `idle0` | 9.48e+08 | 9.2e+08 (-2.9 %) |

### Scenario `rx`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Non-clock toggles / cycle | 920.3 | 920.1 (0) |
| Nets with activity > 10 % | 517 | 514 (-0.6 %) |
| Data load × toggles (fF) | 3.52e+08 | 3.53e+08 (0) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.48e+08 (-3.2 %) |
| **Data + clock** | 1.23e+09 | 1.2e+09 (-2.2 %) |
| RAM-port toggles | 2 718 167 | 2 718 167 (0) |

Toggles / cycle per block, `rx`:

| Block | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| btle_rx | 819.0 | 819.2 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 41.7 | 41.3 (-0.9 %) |
| auxiliary_daemon | 29.1 | 29.1 (0) |
| clock_domain_conversion | 20.3 | 20.3 (0) |
| top glue | 11.1 | 11.1 (0) |

### Scenario `tx`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Non-clock toggles / cycle | 292.2 | 290.8 (-0.5 %) |
| Nets with activity > 10 % | 754 | 781 (+3.6 %) |
| Data load × toggles (fF) | 1.24e+08 | 1.26e+08 (+1.4 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.48e+08 (-3.2 %) |
| **Data + clock** | 1e+09 | 9.74e+08 (-2.6 %) |
| RAM-port toggles | 2 745 143 | 3 182 191 (+15.9 %) |

Toggles / cycle per block, `tx`:

| Block | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| btle_rx | 91.6 | 90.1 (-1.6 %) |
| gauss_filter | 79.1 | 22.6 (-71.5 %) |
| btle_tx (other) | 68.0 | 123.6 (+81.9 %) |
| btle_ll | 28.9 | 29.9 (+3.5 %) |
| auxiliary_daemon | 5.3 | 5.3 (0) |
| clock_domain_conversion | 19.2 | 19.2 (0) |
| top glue | 7.1 | 7.1 (+0.2 %) |

### Scenario `mixed`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Non-clock toggles / cycle | 984.3 | 983.6 (-0.1 %) |
| Nets with activity > 10 % | 839 | 951 (+13.3 %) |
| Data load × toggles (fF) | 3.73e+08 | 3.74e+08 (+0.3 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.48e+08 (-3.2 %) |
| **Data + clock** | 1.25e+09 | 1.22e+09 (-2.1 %) |
| RAM-port toggles | 3 044 741 | 3 262 233 (+7.1 %) |

Toggles / cycle per block, `mixed`:

| Block | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| btle_rx | 791.1 | 791.1 (0) |
| gauss_filter | 39.1 | 11.2 (-71.5 %) |
| btle_tx (other) | 37.4 | 65.0 (+73.7 %) |
| btle_ll | 41.5 | 41.1 (-0.9 %) |
| auxiliary_daemon | 37.6 | 37.6 (0) |
| clock_domain_conversion | 32.3 | 32.3 (0) |
| top glue | 12.3 | 12.3 (0) |

### Scenario `idle`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Non-clock toggles / cycle | 989.4 | 990.6 (+0.1 %) |
| Nets with activity > 10 % | 631 | 632 (+0.2 %) |
| Data load × toggles (fF) | 3.82e+08 | 3.82e+08 (+0.2 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.48e+08 (-3.2 %) |
| **Data + clock** | 1.26e+09 | 1.23e+09 (-2.2 %) |
| RAM-port toggles | 3 096 050 | 3 096 050 (0) |

Toggles / cycle per block, `idle`:

| Block | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| btle_rx | 869.9 | 870.1 (0) |
| gauss_filter | 0.0 | 0.0 (0) |
| btle_tx (other) | 6.0 | 6.0 (0) |
| btle_ll | 27.9 | 28.9 (+3.6 %) |
| auxiliary_daemon | 41.8 | 41.8 (0) |
| clock_domain_conversion | 35.8 | 35.8 (0) |
| top glue | 15.0 | 15.0 (0) |

### Scenario `idle0`

| Measure | `master` | `ble-tx-pdu-we` |
|---|---:|---:|
| Non-clock toggles / cycle | 134.8 | 134.3 (-0.4 %) |
| Nets with activity > 10 % | 339 | 338 (-0.3 %) |
| Data load × toggles (fF) | 7.22e+07 | 7.23e+07 (+0.1 %) |
| Clock (CK pins) load × toggles (fF) | 8.76e+08 | 8.48e+08 (-3.2 %) |
| **Data + clock** | 9.48e+08 | 9.2e+08 (-2.9 %) |
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
| `ble-tx-pdu-we`: activity run on the shared vector set (`vectors.sha256`) | PASS |
| `master`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |
| `ble-tx-pdu-we`: gate-level outputs identical to upstream on every clock, 5 scenarios | PASS |

RESULT: PASS
