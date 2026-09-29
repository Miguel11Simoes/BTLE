# Area run `ble-tx-sin4`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 2286 | 178 | 3366.0 | 0 | 0 |
| `vco` | 179 | 18 | 274.2 | 2 | 8192 |
| `gfsk_modulation` | 2539 | 232 | 3852.2 | 2 | 8192 |
| `btle_tx` | 3465 | 407 | 5427.7 | 3 | 12288 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4438 | 202 | 5669.0 | 0 | 0 |
| `btle_rx` | 36884 | 2068 | 48818.7 | 8 | 32768 |
| `btle_phy` | 40384 | 2475 | 54220.4 | 11 | 45056 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9453 | 2036 | 16746.3 | 3 | 17862 |
| `btle_controller` | 50397 | 4581 | 71862.8 | 15 | 1111494 |
