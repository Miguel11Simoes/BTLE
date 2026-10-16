# Switching activity, run `master`

Gate-level netlists (Nangate45), upstream `btle_controller` (ref) vs fca6ac64fb28cd57a496cb45af62cf9e0f9209d5 (fca6ac64fb28cd57a496cb45af62cf9e0f9209d5, verilog tree 6e670a62d71aec276eb10e6012030875a05d1095), default parameters (dut), simulated side by side on identical stimuli. Setup subtracted; window = the same number of bb_clk cycles for both. Capacitance figures are liberty pin capacitance x toggles (fF-toggles): a pre-layout proxy, NOT power.

## Totals per scenario

| Scenario | Window (cycles) | Toggles/cycle ref → dut | Δ toggles | Non-clock nets >10 % ref → dut | Data load·toggles ref → dut | Δ data | Clock (CK pins) ref → dut | Δ clock | Δ data+clock | RAM-port toggles ref → dut |
|---|---:|---|---:|---|---|---:|---|---:|---:|---|
| rx | 100 000 | 916.0 → 916.0 | +0.0 % | 501 → 501 | 3.55e+08 → 3.55e+08 | +0.0 % | 9.03e+08 → 9.03e+08 | +0.0 % | +0.0 % | 2 839 726 → 2 839 726 |
| tx | 100 000 | 307.7 → 307.7 | +0.0 % | 759 → 759 | 1.37e+08 → 1.37e+08 | +0.0 % | 9.03e+08 → 9.03e+08 | +0.0 % | +0.0 % | 2 776 130 → 2 776 130 |
| mixed | 100 000 | 1041.3 → 1041.3 | +0.0 % | 879 → 879 | 3.99e+08 → 3.99e+08 | +0.0 % | 9.03e+08 → 9.03e+08 | +0.0 % | +0.0 % | 3 165 890 → 3 165 890 |
| idle | 100 000 | 987.6 → 987.6 | +0.0 % | 621 → 621 | 3.87e+08 → 3.87e+08 | +0.0 % | 9.03e+08 → 9.03e+08 | +0.0 % | +0.0 % | 3 096 050 → 3 096 050 |
| idle0 | 100 000 | 113.3 → 113.3 | +0.0 % | 327 → 327 | 7.17e+07 → 7.17e+07 | +0.0 % | 9.03e+08 → 9.03e+08 | +0.0 % | +0.0 % | 2 299 975 → 2 299 975 |

Toggles exclude the clock nets; clock activity is in the CK-pin column.

## Per block, scenario `mixed`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 37.9 → 37.9 | +0.0 % | 1.19e+07 → 1.19e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1003 → 0.1003 | 168 → 168 |
| btle_ll | 9558 → 9558 | 32.3 → 32.3 | +0.0 % | 9.74e+06 → 9.74e+06 | +0.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0026 → 0.0026 | 67 → 67 |
| btle_rx | 36842 → 36842 | 839.8 → 839.8 | +0.0 % | 3.42e+08 → 3.42e+08 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0215 → 0.0215 | 257 → 257 |
| btle_tx (other) | 3829 → 3829 | 48.1 → 48.1 | +0.0 % | 1.46e+07 → 1.46e+07 | +0.0 % | 7.01e+07 → 7.01e+07 | +0.0 % | 0.0114 → 0.0114 | 137 → 137 |
| clock_domain_conversion | 186 → 186 | 37.4 → 37.4 | +0.0 % | 4.34e+06 → 4.34e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.1507 → 0.1507 | 180 → 180 |
| gauss_filter | 2286 → 2286 | 40.1 → 40.1 | +0.0 % | 1.65e+07 → 1.65e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0163 → 0.0163 | 38 → 38 |
| top glue | 219 → 219 | 12.7 → 12.7 | +0.0 % | 2.26e+03 → 2.26e+03 | +0.0 % | 0 → 0 | n/a | 0.0197 → 0.0197 | 32 → 32 |

## Per block, scenario `rx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 28.9 → 28.9 | +0.0 % | 8.72e+06 → 8.72e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0765 → 0.0765 | 114 → 114 |
| btle_ll | 9558 → 9558 | 32.6 → 32.6 | +0.0 % | 9.48e+06 → 9.48e+06 | +0.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0026 → 0.0026 | 67 → 67 |
| btle_rx | 36842 → 36842 | 827.0 → 827.0 | +0.0 % | 3.34e+08 → 3.34e+08 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0212 → 0.0212 | 243 → 243 |
| btle_tx (other) | 3829 → 3829 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 7.01e+07 → 7.01e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
| clock_domain_conversion | 186 → 186 | 23.3 → 23.3 | +0.0 % | 2.57e+06 → 2.57e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.0941 → 0.0941 | 63 → 63 |
| gauss_filter | 2286 → 2286 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
| top glue | 219 → 219 | 11.1 → 11.1 | +0.0 % | 1.38e+03 → 1.38e+03 | +0.0 % | 0 → 0 | n/a | 0.0173 → 0.0173 | 14 → 14 |

## Per block, scenario `tx`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 5.1 → 5.1 | +0.0 % | 1.77e+06 → 1.77e+06 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.0134 → 0.0134 | 15 → 15 |
| btle_ll | 9558 → 9558 | 20.9 → 20.9 | +0.0 % | 6.66e+06 → 6.66e+06 | +0.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0017 → 0.0017 | 45 → 45 |
| btle_rx | 36842 → 36842 | 81.3 → 81.3 | +0.0 % | 6.35e+07 → 6.35e+07 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0021 → 0.0021 | 260 → 260 |
| btle_tx (other) | 3829 → 3829 | 96.7 → 96.7 | +0.0 % | 2.94e+07 → 2.94e+07 | +0.0 % | 7.01e+07 → 7.01e+07 | +0.0 % | 0.0229 → 0.0229 | 215 → 215 |
| clock_domain_conversion | 186 → 186 | 23.0 → 23.0 | +0.0 % | 2.91e+06 → 2.91e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.0929 → 0.0929 | 60 → 60 |
| gauss_filter | 2286 → 2286 | 80.6 → 80.6 | +0.0 % | 3.32e+07 → 3.32e+07 | +0.0 % | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0327 → 0.0327 | 164 → 164 |
| top glue | 219 → 219 | 7.1 → 7.1 | +0.0 % | 3.03e+03 → 3.03e+03 | +0.0 % | 0 → 0 | n/a | 0.0111 → 0.0111 | 0 → 0 |

## Per block, scenario `idle`

| Block | Cells ref → dut | Toggles/cycle ref → dut | Δ | Data load·toggles ref → dut | Δ data | Clock ref → dut | Δ clock | Mean toggle rate per net ref → dut | Nets >10 % ref → dut |
|---|---|---|---:|---|---:|---|---:|---|---|
| auxiliary_daemon | 298 → 298 | 41.4 → 41.4 | +0.0 % | 1.46e+07 → 1.46e+07 | +0.0 % | 9.12e+06 → 9.12e+06 | +0.0 % | 0.1095 → 0.1095 | 152 → 152 |
| btle_ll | 9558 → 9558 | 19.9 → 19.9 | +0.0 % | 5.69e+06 → 5.69e+06 | +0.0 % | 3.87e+08 → 3.87e+08 | +0.0 % | 0.0016 → 0.0016 | 45 → 45 |
| btle_rx | 36842 → 36842 | 879.4 → 879.4 | +0.0 % | 3.62e+08 → 3.62e+08 | +0.0 % | 3.93e+08 → 3.93e+08 | +0.0 % | 0.0226 → 0.0226 | 257 → 257 |
| btle_tx (other) | 3829 → 3829 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 7.01e+07 → 7.01e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
| clock_domain_conversion | 186 → 186 | 38.8 → 38.8 | +0.0 % | 4.32e+06 → 4.32e+06 | +0.0 % | 1.03e+07 → 1.03e+07 | +0.0 % | 0.1566 → 0.1566 | 135 → 135 |
| gauss_filter | 2286 → 2286 | 0.0 → 0.0 | n/a | 0 → 0 | n/a | 3.38e+07 → 3.38e+07 | +0.0 % | 0.0000 → 0.0000 | 0 → 0 |
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
| 1.000 | btle_rx | `tb_activity/u_dut/btle_phy_i.btle_rx_i/_32365_` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/ref_1pps_counter[0]` |
| 1.000 | btle_ll | `tb_activity/u_dut/btle_ll_i/clk_cross_bus_bb_to_s_axi_i.write_data[13]` |

