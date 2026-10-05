# Area run `ble-tx-pdu`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 349 | 63 | 635.7 | 1 | 4096 |
| `btle_tx` | 1399 | 268 | 2553.9 | 2 | 6144 |
