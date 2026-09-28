# Area run `master`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `gauss_filter` | 2286 | 178 | 3366.0 | 0 | 0 |
| `gfsk_modulation` | 2466 | 229 | 3740.2 | 2 | 32768 |
| `btle_tx` | 3409 | 404 | 5322.9 | 3 | 36864 |
