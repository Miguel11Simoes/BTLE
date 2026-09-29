# Switching activity, run `ble-tx-sin8`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs origin/ble-tx-sin8 (e1847f938c54b02f3f2228f25866bfe04cd85f63, verilog tree 8ba2c0e09a7834f386853de68cf3eb085067b680), default parameters (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 920.3 → 921.1 | +0.1 % | 517 → 510 | 3.52e+08 → 3.52e+08 | -0.1 % | 8.76e+08 → 8.91e+08 | +1.7 % | +1.2 % | 2 718 167 → 2 718 167 |
| tx | 100 000 | 292.2 → 301.7 | +3.2 % | 754 → 784 | 1.24e+08 → 1.27e+08 | +2.8 % | 8.76e+08 → 8.91e+08 | +1.7 % | +1.8 % | 2 745 143 → 2 718 637 |
| mixed | 100 000 | 984.3 → 989.4 | +0.5 % | 839 → 845 | 3.73e+08 → 3.74e+08 | +0.4 % | 8.76e+08 → 8.91e+08 | +1.7 % | +1.3 % | 3 044 741 → 3 032 443 |
| idle | 100 000 | 989.4 → 991.0 | +0.2 % | 631 → 623 | 3.82e+08 → 3.82e+08 | +0.0 % | 8.76e+08 → 8.91e+08 | +1.7 % | +1.2 % | 3 096 050 → 3 096 050 |
| idle0 | 100 000 | 134.8 → 135.1 | +0.2 % | 339 → 326 | 7.22e+07 → 7.19e+07 | -0.5 % | 8.76e+08 → 8.91e+08 | +1.7 % | +1.5 % | 2 299 975 → 2 299 975 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 37.6 → 37.6 | +0.0 % | 1.15e+07 → 1.15e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0995 → 0.0995 | 152 → 152 |
| btle_ll | 9484 → 9516 | 41.5 → 42.2 | +1.6 % | 1.21e+07 → 1.16e+07 | -4.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0034 → 0.0034 | 87 → 88 |
| btle_rx | 36947 → 36978 | 791.1 → 791.0 | -0.0 % | 3.2e+08 → 3.2e+08 | +0.1 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0203 → 0.0203 | 242 → 233 |
| btle_tx (other) | 1089 → 1470 | 37.4 → 42.0 | +12.1 % | 9.62e+06 → 1.15e+07 | +19.3 % | 4.29e+07 → 5.77e+07 | +34.5 % | 0.0280 → 0.0234 | 111 → 125 |
| clock_domain_conversion | 183 → 183 | 32.3 → 32.3 | +0.0 % | 3.79e+06 → 3.79e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1322 → 0.1322 | 177 → 177 |
| gauss_filter | 2286 → 2286 | 39.1 → 39.1 | +0.0 % | 1.6e+07 → 1.6e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0159 → 0.0159 | 38 → 38 |
| top glue | 219 → 219 | 12.3 → 12.3 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0191 → 0.0191 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 29.1 → 29.1 | +0.0 % | 8.78e+06 → 8.78e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0770 → 0.0770 | 115 → 115 |
| btle_ll | 9484 → 9516 | 41.7 → 42.4 | +1.6 % | 1.19e+07 → 1.14e+07 | -4.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0034 → 0.0034 | 87 → 88 |
| btle_rx | 36947 → 36978 | 819.0 → 819.1 | +0.0 % | 3.28e+08 → 3.28e+08 | +0.1 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0210 → 0.0210 | 235 → 227 |
| btle_tx (other) | 1089 → 1470 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.46e+06 | +0.8 % | 4.29e+07 → 5.77e+07 | +34.5 % | 0.0045 → 0.0033 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 20.3 → 20.3 | +0.0 % | 2.28e+06 → 2.28e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0833 → 0.0833 | 60 → 60 |
| gauss_filter | 2286 → 2286 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 5.3 → 5.3 | +0.0 % | 1.79e+06 → 1.79e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0139 → 0.0139 | 16 → 16 |
| btle_ll | 9484 → 9516 | 28.9 → 30.9 | +6.9 % | 8.91e+06 → 8.87e+06 | -0.4 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0024 → 0.0025 | 63 → 66 |
| btle_rx | 36947 → 36978 | 91.6 → 89.9 | -1.8 % | 6.06e+07 → 6.03e+07 | -0.5 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0023 → 0.0023 | 250 → 234 |
| btle_tx (other) | 1089 → 1470 | 68.0 → 77.1 | +13.5 % | 1.77e+07 → 2.14e+07 | +21.2 % | 4.29e+07 → 5.77e+07 | +34.5 % | 0.0508 → 0.0429 | 213 → 256 |
| clock_domain_conversion | 183 → 183 | 19.2 → 19.2 | +0.0 % | 2.49e+06 → 2.49e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0786 → 0.0786 | 57 → 57 |
| gauss_filter | 2286 → 2286 | 79.1 → 79.1 | +0.0 % | 3.23e+07 → 3.23e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0321 → 0.0321 | 155 → 155 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 41.8 → 41.8 | +0.0 % | 1.46e+07 → 1.46e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1105 → 0.1105 | 154 → 154 |
| btle_ll | 9484 → 9516 | 27.9 → 29.9 | +7.1 % | 7.93e+06 → 7.9e+06 | -0.4 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0023 → 0.0024 | 63 → 66 |
| btle_rx | 36947 → 36978 | 869.9 → 869.5 | -0.0 % | 3.54e+08 → 3.54e+08 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0223 → 0.0223 | 244 → 233 |
| btle_tx (other) | 1089 → 1470 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.46e+06 | +0.8 % | 4.29e+07 → 5.77e+07 | +34.5 % | 0.0045 → 0.0033 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 35.8 → 35.8 | +0.0 % | 4.03e+06 → 4.03e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1469 → 0.1469 | 132 → 132 |
| gauss_filter | 2286 → 2286 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
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
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_912_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_861_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_32485_` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/uart_frame_tx_i.tx_clk_gen_inst.count[0]` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/ref_1pps_counter[0]` |

