# Area run `ble-opt`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `btle_tx` | 1414 | 238 | 2362.3 | 3 | 36864 |
