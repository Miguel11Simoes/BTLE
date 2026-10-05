# Area run `ble-tx-opt`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 438 | 93 | 870.6 | 2 | 8192 |
| `btle_tx` | 1750 | 316 | 3078.2 | 3 | 12288 |
