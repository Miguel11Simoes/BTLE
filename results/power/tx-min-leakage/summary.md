Leakage of the standard cells (liberty `NangateOpenCellLibrary_typical.lib`, cell_leakage_power, 1nW), SRAM macros excluded (blackboxes).

| Block | Cells | Leakage (µW) | of which flip-flops (µW) | Not priced (macros, `$print`) |
|---|---:|---:|---:|---|
| upstream-baseline (8540186) | 3408 | 112.61 | 31.96 | $print × 1, sdpram_one_clk × 2, sdpram_two_clk × 1 |
| master (fca6ac6) | 5822 | 182.58 | 43.27 | $print × 1, sdpram_one_clk × 2, sdpram_two_clk × 1 |
| ble-tx-rom | 1462 | 51.24 | 18.67 | $print × 1, sdpram_one_clk × 1 |
| ble-tx-min (AdvData 32 x 8) | 1469 | 51.57 | 18.91 | $print × 1, sdpram_one_clk × 1 |
| ble-tx-min (AdvData in flip-flops) | 2250 | 88.32 | 38.45 | $print × 1 |

Source: run tx-min (results/area/tx-min/<configuration>/btle_tx/stat.json), liberty sha256 8d540a4d4cf6d09d
