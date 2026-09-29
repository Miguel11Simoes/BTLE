# Area run `ble-tx-table-sram`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 1362 | 267 | 2479.7 | 3 | 2560 |
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `gfsk_modulation` | 1535 | 318 | 2838.8 | 5 | 35328 |
| `btle_tx` | 2477 | 493 | 4434.5 | 6 | 39424 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4438 | 202 | 5669.0 | 0 | 0 |
| `btle_rx` | 36954 | 2068 | 48845.8 | 8 | 32768 |
| `btle_phy` | 39294 | 2561 | 53202.7 | 14 | 72192 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9453 | 2036 | 16746.3 | 3 | 17862 |
| `btle_controller` | 49324 | 4667 | 70895.6 | 18 | 1138630 |
