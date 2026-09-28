# Switching activity, run `ble-opt`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs ble-opt (f540e99ded01cc1c9f4b6b5dd5df0fd72c8c8d2e, verilog tree b78aa3706fe50f542d00756fb94b014afe1adb4d), ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1 (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 920.3 → 797.7 | -13.3 % | 517 → 2664 | 3.52e+08 → 3.07e+08 | -13.0 % | 8.76e+08 → 5.14e+08 | -41.4 % | -33.2 % | 2 718 167 → 1 609 287 |
| tx | 100 000 | 292.2 → 328.5 | +12.4 % | 754 → 706 | 1.24e+08 → 1.39e+08 | +12.5 % | 8.76e+08 → 5.14e+08 | -41.4 % | -34.7 % | 2 745 143 → 2 045 158 |
| mixed | 100 000 | 984.3 → 939.7 | -4.5 % | 839 → 3908 | 3.73e+08 → 3.57e+08 | -4.3 % | 8.76e+08 → 5.14e+08 | -41.4 % | -30.3 % | 3 044 741 → 1 826 225 |
| idle | 100 000 | 989.4 → 1101.5 | +11.3 % | 631 → 4180 | 3.82e+08 → 4.23e+08 | +10.8 % | 8.76e+08 → 5.14e+08 | -41.4 % | -25.5 % | 3 096 050 → 1 599 990 |
| idle0 | 100 000 | 134.8 → 224.8 | +66.7 % | 339 → 384 | 7.22e+07 → 1.08e+08 | +49.6 % | 8.76e+08 → 5.14e+08 | -41.4 % | -34.4 % | 2 299 975 → 1 599 990 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 234 | 37.6 → 32.3 | -14.3 % | 1.15e+07 → 9.72e+06 | -15.6 % | 9.12e+06 → 6.27e+06 | -31.2 % | 0.0995 → 0.1208 | 152 → 135 |
| btle_ll | 9484 → 4311 | 41.5 → 11.0 | -73.4 % | 1.21e+07 → 3.08e+06 | -74.6 % | 3.87e+08 → 1.81e+08 | -53.2 % | 0.0034 → 0.0019 | 87 → 21 |
| btle_rx | 36947 → 10074 | 791.1 → 808.8 | +2.2 % | 3.2e+08 → 3.24e+08 | +1.4 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0203 → 0.0704 | 242 → 3406 |
| btle_tx (other) | 1089 → 1083 | 37.4 → 37.7 | +0.8 % | 9.62e+06 → 1e+07 | +4.2 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0280 → 0.0283 | 111 → 111 |
| clock_domain_conversion | 183 → 183 | 32.3 → 32.3 | +0.0 % | 3.79e+06 → 3.79e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1322 → 0.1322 | 177 → 177 |
| gauss_filter | 2286 → 264 | 39.1 → 12.3 | -68.6 % | 1.6e+07 → 5.75e+06 | -64.1 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0159 → 0.0430 | 38 → 26 |
| top glue | 219 → 219 | 12.3 → 12.3 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0191 → 0.0191 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 234 | 29.1 → 23.8 | -18.2 % | 8.78e+06 → 6.99e+06 | -20.4 % | 9.12e+06 → 6.27e+06 | -31.2 % | 0.0770 → 0.0892 | 115 → 99 |
| btle_ll | 9484 → 4311 | 41.7 → 11.3 | -73.0 % | 1.19e+07 → 3.03e+06 | -74.5 % | 3.87e+08 → 1.81e+08 | -53.2 % | 0.0034 → 0.0019 | 87 → 21 |
| btle_rx | 36947 → 10074 | 819.0 → 732.2 | -10.6 % | 3.28e+08 → 2.93e+08 | -10.7 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0210 → 0.0637 | 235 → 2464 |
| btle_tx (other) | 1089 → 1083 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 20.3 → 20.3 | +0.0 % | 2.28e+06 → 2.28e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0833 → 0.0833 | 60 → 60 |
| gauss_filter | 2286 → 264 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 234 | 5.3 → 0.0 | -100.0 % | 1.79e+06 → 0 | -100.0 % | 9.12e+06 → 6.27e+06 | -31.2 % | 0.0139 → 0.0000 | 16 → 0 |
| btle_ll | 9484 → 4311 | 28.9 → 10.5 | -63.8 % | 8.91e+06 → 3.03e+06 | -66.0 % | 3.87e+08 → 1.81e+08 | -53.2 % | 0.0024 → 0.0018 | 63 → 21 |
| btle_rx | 36947 → 10074 | 91.6 → 205.3 | +124.1 % | 6.06e+07 → 1.04e+08 | +71.0 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0023 → 0.0179 | 250 → 353 |
| btle_tx (other) | 1089 → 1083 | 68.0 → 68.6 | +0.9 % | 1.77e+07 → 1.85e+07 | +4.6 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0508 → 0.0515 | 213 → 212 |
| clock_domain_conversion | 183 → 183 | 19.2 → 19.2 | +0.0 % | 2.49e+06 → 2.49e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0786 → 0.0786 | 57 → 57 |
| gauss_filter | 2286 → 264 | 79.1 → 24.8 | -68.6 % | 3.23e+07 → 1.16e+07 | -64.1 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0321 → 0.0869 | 155 → 63 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 234 | 41.8 → 36.3 | -13.1 % | 1.46e+07 → 1.28e+07 | -12.4 % | 9.12e+06 → 6.27e+06 | -31.2 % | 0.1105 → 0.1359 | 154 → 137 |
| btle_ll | 9484 → 4311 | 27.9 → 9.5 | -66.1 % | 7.93e+06 → 2.51e+06 | -68.3 % | 3.87e+08 → 1.81e+08 | -53.2 % | 0.0023 → 0.0016 | 63 → 21 |
| btle_rx | 36947 → 10074 | 869.9 → 1006.0 | +15.6 % | 3.54e+08 → 4.02e+08 | +13.7 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0223 → 0.0876 | 244 → 3852 |
| btle_tx (other) | 1089 → 1083 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 35.8 → 35.8 | +0.0 % | 4.03e+06 → 4.03e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1469 → 0.1469 | 132 → 132 |
| gauss_filter | 2286 → 264 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
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
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_655_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_507_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/gfsk_demodulation_shared_i.s_valid` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_9796_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_7270_` |

