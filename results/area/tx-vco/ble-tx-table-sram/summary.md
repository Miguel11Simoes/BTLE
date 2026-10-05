# Area run `ble-tx-table-sram`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `btle_tx` | 5176 | 636 | 7883.2 | 6 | 39424 |
