# Switching activity, run `ble-tx-rom`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs origin/ble-tx-rom (66a775118b493f28c1ce399bb85d528fb5520b0f, verilog tree 5c6bc01c224c10e943a8ededcf30c69bc65fb4da), GAUSS_TABLE=1 (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 916.0 → 916.1 | +0.0 % | 501 → 499 | 3.55e+08 → 3.55e+08 | -0.0 % | 9.03e+08 → 8.44e+08 | -6.5 % | -4.7 % | 2 839 726 → 2 639 726 |
| tx | 100 000 | 307.7 → 282.3 | -8.2 % | 759 → 874 | 1.37e+08 → 1.32e+08 | -4.2 % | 9.03e+08 → 8.44e+08 | -6.5 % | -6.2 % | 2 776 130 → 2 114 799 |
| mixed | 100 000 | 1041.3 → 1028.4 | -1.2 % | 879 → 928 | 3.99e+08 → 3.96e+08 | -0.7 % | 9.03e+08 → 8.44e+08 | -6.5 % | -4.8 % | 3 165 890 → 2 736 445 |
| idle | 100 000 | 987.6 → 986.8 | -0.1 % | 621 → 618 | 3.87e+08 → 3.86e+08 | -0.1 % | 9.03e+08 → 8.44e+08 | -6.5 % | -4.6 % | 3 096 050 → 2 896 050 |
| idle0 | 100 000 | 113.3 → 113.8 | +0.4 % | 327 → 326 | 7.17e+07 → 7.14e+07 | -0.3 % | 9.03e+08 → 8.44e+08 | -6.5 % | -6.1 % | 2 299 975 → 2 099 975 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 37.9 → 38.0 | +0.1 % | 1.19e+07 → 1.19e+07 | +0.2 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1003 → 0.1002 | 168 → 168 |
| btle_ll | 9558 → 9592 | 32.3 → 32.4 | +0.1 % | 9.74e+06 → 9.61e+06 | -1.3 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0026 → 0.0026 | 67 → 67 |
| btle_rx | 36842 → 36963 | 839.8 → 839.7 | -0.0 % | 3.42e+08 → 3.42e+08 | -0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0215 → 0.0215 | 257 → 254 |
| btle_tx (other) | 3829 → 1310 | 48.1 → 64.3 | +33.7 % | 1.46e+07 → 2.32e+07 | +58.5 % | 7.01e+07 → 4.06e+07 | -42.0 % | 0.0114 → 0.0420 | 137 → 202 |
| clock_domain_conversion | 186 → 186 | 37.4 → 37.4 | +0.0 % | 4.34e+06 → 4.34e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.1507 → 0.1507 | 180 → 180 |
| gauss_filter | 2286 → 163 | 40.1 → 11.0 | -72.4 % | 1.65e+07 → 5.29e+06 | -68.0 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0163 → 0.0597 | 38 → 25 |
| top glue | 219 → 219 | 12.7 → 12.7 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0197 → 0.0197 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 28.9 → 28.9 | -0.0 % | 8.72e+06 → 8.76e+06 | +0.5 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0765 → 0.0763 | 114 → 114 |
| btle_ll | 9558 → 9592 | 32.6 → 32.7 | +0.2 % | 9.48e+06 → 9.36e+06 | -1.3 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0026 → 0.0026 | 67 → 67 |
| btle_rx | 36842 → 36963 | 827.0 → 827.0 | -0.0 % | 3.34e+08 → 3.34e+08 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0212 → 0.0212 | 243 → 241 |
| btle_tx (other) | 3829 → 1310 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 7.01e+07 → 4.06e+07 | -42.0 % | 0.0000 → 0.0000 | 0 → 0 |
| clock_domain_conversion | 186 → 186 | 23.3 → 23.3 | +0.0 % | 2.57e+06 → 2.57e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.0941 → 0.0941 | 63 → 63 |
| gauss_filter | 2286 → 163 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 5.1 → 5.1 | -0.2 % | 1.77e+06 → 1.77e+06 | +0.1 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0134 → 0.0134 | 15 → 15 |
| btle_ll | 9558 → 9592 | 20.9 → 20.9 | +0.0 % | 6.66e+06 → 6.52e+06 | -2.1 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0017 → 0.0017 | 45 → 45 |
| btle_rx | 36842 → 36963 | 81.3 → 81.8 | +0.6 % | 6.35e+07 → 6.34e+07 | -0.2 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0021 → 0.0021 | 260 → 259 |
| btle_tx (other) | 3829 → 1310 | 96.7 → 129.2 | +33.6 % | 2.94e+07 → 4.65e+07 | +58.3 % | 7.01e+07 → 4.06e+07 | -42.0 % | 0.0229 → 0.0843 | 215 → 445 |
| clock_domain_conversion | 186 → 186 | 23.0 → 23.0 | +0.0 % | 2.91e+06 → 2.91e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.0929 → 0.0929 | 60 → 60 |
| gauss_filter | 2286 → 163 | 80.6 → 22.2 | -72.4 % | 3.32e+07 → 1.06e+07 | -68.0 % | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0327 → 0.1200 | 164 → 50 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 299 | 41.4 → 41.4 | +0.1 % | 1.46e+07 → 1.46e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1095 → 0.1093 | 152 → 152 |
| btle_ll | 9558 → 9592 | 19.9 → 19.9 | +0.0 % | 5.69e+06 → 5.55e+06 | -2.4 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0016 → 0.0016 | 45 → 45 |
| btle_rx | 36842 → 36963 | 879.4 → 878.6 | -0.1 % | 3.62e+08 → 3.62e+08 | -0.1 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0226 → 0.0225 | 257 → 254 |
| btle_tx (other) | 3829 → 1310 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 7.01e+07 → 4.06e+07 | -42.0 % | 0.0000 → 0.0000 | 0 → 0 |
| clock_domain_conversion | 186 → 186 | 38.8 → 38.8 | +0.0 % | 4.32e+06 → 4.32e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.1566 → 0.1566 | 135 → 135 |
| gauss_filter | 2286 → 163 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 4.18e+06 | -87.6 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 15.0 → 15.0 | +0.0 % | 0 → 0 | n/a | 0 → 0 | n/a | 0.0233 → 0.0233 | 32 → 32 |

## Most active non-clock nets, scenario `mixed`

ref:

| Toggle rate | Block | Net |
|---:|---|---|
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/rx_sample_phase` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/rx_iq_valid` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_50_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_183_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_173_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_165_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_ref/clock_domain_conversion_iq_i/_104_` |
| 1.000 | btle_rx | `tb_activity/u_ref/btle_phy_i.btle_rx_i/_32365_` |
| 1.000 | btle_ll | `tb_activity/u_ref/btle_ll_i/ref_1pps_counter[0]` |
| 1.000 | btle_ll | `tb_activity/u_ref/btle_ll_i/clk_cross_bus_bb_to_s_axi_i.write_data[13]` |

dut:

| Toggle rate | Block | Net |
|---:|---|---|
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/rx_sample_phase` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/rx_iq_valid` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_50_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_183_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_173_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_165_` |
| 1.000 | clock_domain_conversion | `tb_activity/u_dut/clock_domain_conversion_iq_i/_104_` |
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_32483_` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/ref_1pps_counter[0]` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/clk_cross_bus_bb_to_s_axi_i.write_data[13]` |

