# Area run `ble-tx-table-sram`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `gauss_filter` | 1362 | 267 | 2479.7 | 3 | 2560 |
| `gfsk_modulation` | 1535 | 318 | 2838.8 | 5 | 35328 |
| `btle_tx` | 2477 | 493 | 4434.5 | 6 | 39424 |
| `gauss_table_builder` | 493 | 53 | 778.0 | 0 | 0 |
| `gauss_table_sram` | 56 | 16 | 139.4 | 3 | 2560 |
