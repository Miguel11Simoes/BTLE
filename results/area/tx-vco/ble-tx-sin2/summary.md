# Area run `ble-tx-sin2`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 408 | 76 | 740.0 | 1 | 4096 |
| `btle_tx` | 6245 | 608 | 9208.4 | 2 | 8192 |
