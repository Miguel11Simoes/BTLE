# Area run `ble-tx-table`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `gauss_filter` | 253 | 22 | 348.5 | 0 | 0 |
| `gfsk_modulation` | 426 | 73 | 716.6 | 2 | 32768 |
| `btle_tx` | 1392 | 248 | 2325.6 | 3 | 36864 |
