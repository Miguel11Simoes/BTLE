# Area run `ble-tx-min`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 206 | 38 | 353.8 | 0 | 0 |
| `scramble` | 82 | 17 | 147.9 | 0 | 0 |
| `bit_repeat_upsample` | 34 | 8 | 61.2 | 0 | 0 |
| `gauss_filter` | 166 | 22 | 256.7 | 0 | 0 |
| `vco` | 435 | 31 | 597.4 | 0 | 0 |
| `gfsk_modulation` | 767 | 79 | 1122.8 | 0 | 0 |
| `btle_tx` | 1470 | 239 | 2531.3 | 1 | 256 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4477 | 202 | 5709.7 | 0 | 0 |
| `btle_rx` | 36757 | 2068 | 48602.7 | 8 | 32768 |
| `btle_phy` | 38329 | 2307 | 51218.3 | 9 | 33024 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9523 | 2036 | 16737.8 | 3 | 17862 |
| `btle_controller` | 48140 | 4414 | 68701.1 | 13 | 1099462 |
