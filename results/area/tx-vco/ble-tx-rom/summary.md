# Area run `ble-tx-rom`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 434 | 31 | 593.2 | 0 | 0 |
| `btle_tx` | 1446 | 236 | 2509.4 | 1 | 2048 |
