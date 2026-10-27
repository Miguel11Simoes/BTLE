# Area run `ble-tx-min-flops`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 206 | 38 | 353.8 | 0 | 0 |
| `scramble` | 82 | 17 | 147.9 | 0 | 0 |
| `bit_repeat_upsample` | 34 | 8 | 61.2 | 0 | 0 |
| `gauss_filter` | 166 | 22 | 256.7 | 0 | 0 |
| `vco` | 434 | 31 | 593.2 | 0 | 0 |
| `gfsk_modulation` | 764 | 79 | 1115.9 | 0 | 0 |
| `btle_tx` | 2234 | 486 | 4420.4 | 0 | 0 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4477 | 202 | 5709.7 | 0 | 0 |
| `btle_rx` | 36764 | 2068 | 48664.7 | 8 | 32768 |
| `btle_phy` | 39146 | 2554 | 53153.4 | 8 | 32768 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9399 | 2014 | 16537.8 | 3 | 17862 |
| `btle_controller` | 48678 | 4639 | 70274.0 | 12 | 1099206 |
