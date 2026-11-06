# Area run `eeprom`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `tag_capture` | 229 | 27 | 350.3 | 0 | 0 |
| `tag_bus` | 162 | 29 | 269.2 | 0 | 0 |
| `crc24` | 206 | 38 | 353.8 | 0 | 0 |
| `scramble` | 82 | 17 | 147.9 | 0 | 0 |
| `bit_repeat_upsample` | 34 | 8 | 61.2 | 0 | 0 |
| `gauss_filter` | 166 | 22 | 256.7 | 0 | 0 |
| `vco` | 434 | 31 | 593.2 | 0 | 0 |
| `gfsk_modulation` | 764 | 79 | 1115.9 | 0 | 0 |
| `btle_tx` | 1619 | 265 | 2772.3 | 0 | 0 |
| `tag_core` | 3994 | 719 | 6698.4 | 0 | 0 |
| `tag_chip` | 3921 | 718 | 6601.9 | 0 | 0 |
| `btle_phy` | 3981 | 719 | 6712.2 | 0 | 0 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9525 | 2014 | 16693.4 | 4 | 18182 |
| `btle_controller` | 12516 | 2483 | 21468.1 | 5 | 1066758 |
