# Area run `ble-tx-tag-12`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 206 | 38 | 353.8 | 0 | 0 |
| `scramble` | 82 | 17 | 147.9 | 0 | 0 |
| `bit_repeat_upsample` | 34 | 8 | 61.2 | 0 | 0 |
| `gauss_filter` | 166 | 22 | 256.7 | 0 | 0 |
| `vco` | 434 | 31 | 593.2 | 0 | 0 |
| `gfsk_modulation` | 801 | 79 | 1150.2 | 0 | 0 |
| `btle_tx` | 1790 | 323 | 3141.2 | 0 | 0 |
| `btle_phy` | 1789 | 323 | 3139.3 | 0 | 0 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9383 | 2014 | 16529.5 | 3 | 17862 |
| `btle_controller` | 10067 | 2023 | 17424.6 | 4 | 1066438 |
