# Area run `ble-tx-sin8`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 438 | 93 | 870.6 | 2 | 8192 |
| `btle_tx` | 6512 | 625 | 9571.2 | 3 | 12288 |
