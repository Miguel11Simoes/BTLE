# Area run `ble-tx-table-reg`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `gauss_filter` | 10097 | 2822 | 23221.5 | 0 | 0 |
| `gfsk_modulation` | 10422 | 2873 | 23615.5 | 2 | 32768 |
| `btle_tx` | 11328 | 3048 | 25201.6 | 3 | 36864 |
| `gauss_table_builder` | 493 | 53 | 778.0 | 0 | 0 |
| `gauss_table_reg` | 8899 | 2560 | 20870.1 | 0 | 0 |
