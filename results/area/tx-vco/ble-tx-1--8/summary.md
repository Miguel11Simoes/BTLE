# Area run `ble-tx-1--8`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 645 | 91 | 1059.7 | 2 | 4096 |
| `btle_tx` | 6766 | 623 | 9790.1 | 3 | 8192 |
