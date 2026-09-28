# Switching activity, run `ble-tx-table`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs origin/ble-tx-table (eaaf6cf67ea514ea66751b39c116446351b6505f, verilog tree 2d36551e0bf844c7b97e00679522c2838829fd35), GAUSS_TABLE=1 (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 920.3 → 918.9 | -0.1 % | 517 → 516 | 3.52e+08 → 3.52e+08 | -0.1 % | 8.76e+08 → 8.46e+08 | -3.4 % | -2.4 % | 2 718 167 → 2 718 167 |
| tx | 100 000 | 292.2 → 237.5 | -18.7 % | 754 → 661 | 1.24e+08 → 1.03e+08 | -16.6 % | 8.76e+08 → 8.46e+08 | -3.4 % | -5.0 % | 2 745 143 → 2 745 143 |
| mixed | 100 000 | 984.3 → 956.4 | -2.8 % | 839 → 827 | 3.73e+08 → 3.62e+08 | -2.8 % | 8.76e+08 → 8.46e+08 | -3.4 % | -3.2 % | 3 044 741 → 3 044 741 |
| idle | 100 000 | 989.4 → 989.6 | +0.0 % | 631 → 634 | 3.82e+08 → 3.82e+08 | +0.1 % | 8.76e+08 → 8.46e+08 | -3.4 % | -2.3 % | 3 096 050 → 3 096 050 |
| idle0 | 100 000 | 134.8 → 133.8 | -0.8 % | 339 → 337 | 7.22e+07 → 7.21e+07 | -0.1 % | 8.76e+08 → 8.46e+08 | -3.4 % | -3.1 % | 2 299 975 → 2 299 975 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 37.6 → 37.6 | +0.0 % | 1.15e+07 → 1.15e+07 | -0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0995 → 0.0995 | 152 → 152 |
| btle_ll | 9484 → 9455 | 41.5 → 40.6 | -2.0 % | 1.21e+07 → 1.19e+07 | -2.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0034 → 0.0033 | 87 → 86 |
| btle_rx | 36947 → 36986 | 791.1 → 790.6 | -0.1 % | 3.2e+08 → 3.2e+08 | -0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0203 → 0.0202 | 242 → 242 |
| btle_tx (other) | 1089 → 1089 | 37.4 → 37.4 | +0.0 % | 9.62e+06 → 9.62e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0280 → 0.0280 | 111 → 111 |
| clock_domain_conversion | 183 → 183 | 32.3 → 32.3 | +0.0 % | 3.79e+06 → 3.79e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1322 → 0.1322 | 177 → 177 |
| gauss_filter | 2286 → 265 | 39.1 → 12.6 | -67.8 % | 1.6e+07 → 5.87e+06 | -63.4 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0159 → 0.0439 | 38 → 27 |
| top glue | 219 → 219 | 12.3 → 12.3 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0191 → 0.0191 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 29.1 → 29.1 | +0.0 % | 8.78e+06 → 8.78e+06 | -0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0770 → 0.0770 | 115 → 115 |
| btle_ll | 9484 → 9455 | 41.7 → 40.9 | -2.0 % | 1.19e+07 → 1.16e+07 | -2.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0034 → 0.0033 | 87 → 86 |
| btle_rx | 36947 → 36986 | 819.0 → 818.5 | -0.1 % | 3.28e+08 → 3.28e+08 | -0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0210 → 0.0210 | 235 → 235 |
| btle_tx (other) | 1089 → 1089 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 20.3 → 20.3 | +0.0 % | 2.28e+06 → 2.28e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0833 → 0.0833 | 60 → 60 |
| gauss_filter | 2286 → 265 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 5.3 → 5.3 | +0.0 % | 1.79e+06 → 1.79e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0139 → 0.0139 | 16 → 16 |
| btle_ll | 9484 → 9455 | 28.9 → 29.4 | +1.7 % | 8.91e+06 → 9.12e+06 | +2.4 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0024 → 0.0024 | 63 → 64 |
| btle_rx | 36947 → 36986 | 91.6 → 90.1 | -1.7 % | 6.06e+07 → 6.03e+07 | -0.5 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0023 → 0.0023 | 250 → 247 |
| btle_tx (other) | 1089 → 1089 | 68.0 → 68.0 | +0.0 % | 1.77e+07 → 1.77e+07 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0508 → 0.0508 | 213 → 213 |
| clock_domain_conversion | 183 → 183 | 19.2 → 19.2 | +0.0 % | 2.49e+06 → 2.49e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0786 → 0.0786 | 57 → 57 |
| gauss_filter | 2286 → 265 | 79.1 → 25.4 | -67.9 % | 3.23e+07 → 1.18e+07 | -63.4 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0321 → 0.0886 | 155 → 64 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 41.8 → 41.8 | +0.0 % | 1.46e+07 → 1.46e+07 | -0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1105 → 0.1105 | 154 → 154 |
| btle_ll | 9484 → 9455 | 27.9 → 28.4 | +1.8 % | 7.93e+06 → 8.15e+06 | +2.7 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0023 → 0.0023 | 63 → 64 |
| btle_rx | 36947 → 36986 | 869.9 → 869.6 | -0.0 % | 3.54e+08 → 3.54e+08 | -0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0223 → 0.0223 | 244 → 246 |
| btle_tx (other) | 1089 → 1089 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 35.8 → 35.8 | +0.0 % | 4.03e+06 → 4.03e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1469 → 0.1469 | 132 → 132 |
| gauss_filter | 2286 → 265 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 15.0 → 15.0 | +0.0 % | 0 → 0 | n/a | 0 → 0 | n/a | 0.0233 → 0.0233 | 32 → 32 |

## Most active non-clock nets, scenario `mixed`

ref:

| Toggle rate | Block | Net |
|---:|---|---|
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/rx_iq_valid` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_52_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_182_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_173_` |
| 1.000 | btle_tx (other) | `tb_activity/u_ref/btle_phy_i.btle_tx_i/gfsk_modulation_i.bit_repeat_upsample_i.bit_upsample_valid_internal` |
| 1.000 | btle_tx (other) | `tb_activity/u_ref/btle_phy_i.btle_tx_i/_644_` |
| 1.000 | btle_tx (other) | `tb_activity/u_ref/btle_phy_i.btle_tx_i/_513_` |
| 1.000 | btle_rx | `tb_activity/u_ref/btle_phy_i.btle_rx_i/_32451_` |
| 1.000 | btle_ll | `tb_activity/u_ref/btle_ll_i/uart_frame_tx_i.tx_clk_gen_inst.count[0]` |
| 1.000 | btle_ll | `tb_activity/u_ref/btle_ll_i/ref_1pps_counter[0]` |

dut:

| Toggle rate | Block | Net |
|---:|---|---|
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/rx_iq_valid` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_52_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_182_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_173_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/gfsk_modulation_i.bit_repeat_upsample_i.bit_upsample_valid_internal` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_644_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_513_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_32498_` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/uart_frame_tx_i.tx_clk_gen_inst.count[0]` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/ref_1pps_counter[0]` |

