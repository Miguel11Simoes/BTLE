# Area run `master`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `btle_tx` | 6166 | 547 | 8875.6 | 3 | 36864 |
