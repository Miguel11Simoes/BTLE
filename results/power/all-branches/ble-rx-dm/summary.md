# Switching activity, run `ble-rx-dm`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs origin/ble-rx-dm (92d6e5429185534b168a6cfce1337540d8c14a88, verilog tree aa807f8228cdcf2db6dca8648980b08c6e195f54), default parameters (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 920.3 → 837.0 | -9.1 % | 517 → 2757 | 3.52e+08 → 3.18e+08 | -9.8 % | 8.76e+08 → 7.52e+08 | -14.1 % | -12.9 % | 2 718 167 → 2 718 167 |
| tx | 100 000 | 292.2 → 405.7 | +38.8 % | 754 → 850 | 1.24e+08 → 1.68e+08 | +35.3 % | 8.76e+08 → 7.52e+08 | -14.1 % | -8.0 % | 2 745 143 → 2 745 143 |
| mixed | 100 000 | 984.3 → 1004.5 | +2.1 % | 839 → 4002 | 3.73e+08 → 3.78e+08 | +1.5 % | 8.76e+08 → 7.52e+08 | -14.1 % | -9.5 % | 3 044 741 → 3 044 741 |
| idle | 100 000 | 989.4 → 1128.7 | +14.1 % | 631 → 4247 | 3.82e+08 → 4.31e+08 | +12.9 % | 8.76e+08 → 7.52e+08 | -14.1 % | -5.9 % | 3 096 050 → 3 096 050 |
| idle0 | 100 000 | 134.8 → 249.4 | +85.0 % | 339 → 439 | 7.22e+07 → 1.15e+08 | +59.8 % | 8.76e+08 → 7.52e+08 | -14.1 % | -8.5 % | 2 299 975 → 2 299 975 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 37.6 → 37.7 | +0.3 % | 1.15e+07 → 1.15e+07 | -0.1 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0995 → 0.0995 | 152 → 152 |
| btle_ll | 9484 → 9533 | 41.5 → 41.7 | +0.6 % | 1.21e+07 → 1.21e+07 | +0.3 % | 3.87e+08 → 3.87e+08 | -0.0 % | 0.0034 → 0.0034 | 87 → 87 |
| btle_rx | 36947 → 10082 | 791.1 → 811.5 | +2.6 % | 3.2e+08 → 3.25e+08 | +1.6 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0203 → 0.0706 | 242 → 3408 |
| btle_tx (other) | 1089 → 1087 | 37.4 → 36.9 | -1.5 % | 9.62e+06 → 9.85e+06 | +2.5 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0280 → 0.0276 | 111 → 108 |
| clock_domain_conversion | 183 → 183 | 32.3 → 32.3 | +0.0 % | 3.79e+06 → 3.79e+06 | +0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.1322 → 0.1322 | 177 → 177 |
| gauss_filter | 2286 → 2286 | 39.1 → 39.1 | +0.0 % | 1.6e+07 → 1.6e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0159 → 0.0159 | 38 → 38 |
| top glue | 219 → 219 | 12.3 → 12.3 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0191 → 0.0191 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 29.1 → 29.1 | +0.0 % | 8.78e+06 → 8.78e+06 | -0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0770 → 0.0769 | 115 → 115 |
| btle_ll | 9484 → 9533 | 41.7 → 42.0 | +0.8 % | 1.19e+07 → 1.19e+07 | +0.4 % | 3.87e+08 → 3.87e+08 | -0.0 % | 0.0034 → 0.0034 | 87 → 87 |
| btle_rx | 36947 → 10082 | 819.0 → 735.3 | -10.2 % | 3.28e+08 → 2.94e+08 | -10.5 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0210 → 0.0640 | 235 → 2475 |
| btle_tx (other) | 1089 → 1087 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
| clock_domain_conversion | 183 → 183 | 20.3 → 20.3 | +0.0 % | 2.28e+06 → 2.28e+06 | -0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0833 → 0.0833 | 60 → 60 |
| gauss_filter | 2286 → 2286 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 5.3 → 5.3 | +0.0 % | 1.79e+06 → 1.79e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0139 → 0.0139 | 16 → 16 |
| btle_ll | 9484 → 9533 | 28.9 → 29.0 | +0.4 % | 8.91e+06 → 8.9e+06 | -0.1 % | 3.87e+08 → 3.87e+08 | -0.0 % | 0.0024 → 0.0024 | 63 → 63 |
| btle_rx | 36947 → 10082 | 91.6 → 206.1 | +125.0 % | 6.06e+07 → 1.04e+08 | +71.3 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0023 → 0.0179 | 250 → 350 |
| btle_tx (other) | 1089 → 1087 | 68.0 → 66.8 | -1.7 % | 1.77e+07 → 1.81e+07 | +2.7 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0508 → 0.0500 | 213 → 209 |
| clock_domain_conversion | 183 → 183 | 19.2 → 19.2 | +0.0 % | 2.49e+06 → 2.49e+06 | -0.0 % | 1.01e+07 → 1.01e+07 | +0.0 % | 0.0786 → 0.0786 | 57 → 57 |
| gauss_filter | 2286 → 2286 | 79.1 → 79.1 | +0.0 % | 3.23e+07 → 3.23e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0321 → 0.0321 | 155 → 155 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 41.8 → 41.8 | +0.1 % | 1.46e+07 → 1.46e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1105 → 0.1103 | 154 → 154 |
| btle_ll | 9484 → 9533 | 27.9 → 28.0 | +0.4 % | 7.93e+06 → 7.93e+06 | -0.1 % | 3.87e+08 → 3.87e+08 | -0.0 % | 0.0023 → 0.0023 | 63 → 63 |
| btle_rx | 36947 → 10082 | 869.9 → 1009.0 | +16.0 % | 3.54e+08 → 4.03e+08 | +14.0 % | 3.93e+08 → 2.69e+08 | -31.5 % | 0.0223 → 0.0878 | 244 → 3860 |
| btle_tx (other) | 1089 → 1087 | 6.0 → 6.0 | +0.0 % | 1.45e+06 → 1.45e+06 | +0.0 % | 4.29e+07 → 4.29e+07 | +0.0 % | 0.0045 → 0.0045 | 6 → 6 |
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
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_174_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_123_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/gfsk_modulation_i.bit_repeat_upsample_i.bit_upsample_valid_internal` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_655_` |
| 1.000 | btle_tx (other) | `tb_activity/u_dut/btle_phy_i.btle_tx_i/_511_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/gfsk_demodulation_shared_i.s_valid` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_9802_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_7278_` |

