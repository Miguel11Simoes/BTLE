# Area run `ble-tx-cordic`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 1942 | 31 | 2317.9 | 0 | 0 |
| `btle_tx` | 2868 | 236 | 4142.2 | 1 | 2048 |
