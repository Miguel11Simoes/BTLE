# Area run `ble-tx-fir2`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `gauss_filter` | 1560 | 170 | 2311.5 | 0 | 0 |
| `gfsk_modulation` | 1748 | 221 | 2703.1 | 2 | 32768 |
| `btle_tx` | 2707 | 396 | 4295.9 | 3 | 36864 |
