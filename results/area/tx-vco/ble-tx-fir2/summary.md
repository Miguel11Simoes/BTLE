# Area run `ble-tx-fir2`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `btle_tx` | 5326 | 539 | 7698.6 | 3 | 36864 |
