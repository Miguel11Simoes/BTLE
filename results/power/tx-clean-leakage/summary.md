Leakage of the standard cells (liberty `NangateOpenCellLibrary_typical.lib`, cell_leakage_power, 1nW), SRAM macros excluded (blackboxes).

| Block | Cells | Leakage (µW) | of which flip-flops (µW) | Not priced (macros, `$print`) |
|---|---:|---:|---:|---|
| upstream | 3408 | 112.61 | 31.96 | $print × 1, sdpram_one_clk × 2, sdpram_two_clk × 1 |
| corrected master | 5822 | 182.58 | 43.27 | $print × 1, sdpram_one_clk × 2, sdpram_two_clk × 1 |
| ble-tx-rom | 1462 | 51.24 | 18.67 | $print × 1, sdpram_one_clk × 1 |
| ble-tx-min | 1487 | 51.71 | 18.91 | $print × 1, sdpram_one_clk × 1 |
| ble-tx-min, flip-flops | 2233 | 87.84 | 38.45 | $print × 1 |

Source: run tx-clean (results/area/tx-clean/<configuration>/btle_tx/stat.json, ble-tx-min at b81bf288) and run tx-min (results/area/tx-min/<configuration>/btle_tx/stat.json: upstream-baseline, master, ble-tx-rom), liberty sha256 8d540a4d4cf6d09d
