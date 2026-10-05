# Area run `ble-tx-sin4`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 179 | 18 | 274.2 | 2 | 8192 |
| `btle_tx` | 6274 | 550 | 9029.1 | 3 | 12288 |
