# Area run `ble-tx-opt`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 253 | 22 | 348.5 | 0 | 0 |
| `vco` | 438 | 93 | 870.6 | 2 | 8192 |
| `gfsk_modulation` | 776 | 151 | 1438.0 | 2 | 8192 |
| `btle_tx` | 1696 | 326 | 3028.9 | 3 | 12288 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4438 | 202 | 5669.0 | 0 | 0 |
| `btle_rx` | 36931 | 2068 | 48843.2 | 8 | 32768 |
| `btle_phy` | 38600 | 2394 | 51818.7 | 11 | 45056 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9453 | 2036 | 16746.3 | 3 | 17862 |
| `btle_controller` | 48559 | 4500 | 69411.6 | 15 | 1111494 |
