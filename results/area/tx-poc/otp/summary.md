# Area run `otp`

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
| `tag_core` | 2370 | 393 | 3856.5 | 0 | 0 |
| `tag_chip` | 2278 | 393 | 3772.7 | 0 | 0 |
| `btle_phy` | 2385 | 393 | 3878.5 | 0 | 0 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9525 | 2014 | 16693.4 | 4 | 18182 |
| `btle_controller` | 10841 | 2157 | 18619.5 | 5 | 1066758 |
