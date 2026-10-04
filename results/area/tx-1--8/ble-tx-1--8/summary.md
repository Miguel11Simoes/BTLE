# Area run `ble-tx-1--8`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 2286 | 178 | 3366.0 | 0 | 0 |
| `vco` | 645 | 91 | 1059.7 | 2 | 4096 |
| `gfsk_modulation` | 3034 | 305 | 4655.5 | 2 | 4096 |
| `btle_tx` | 3939 | 480 | 6225.7 | 3 | 8192 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4438 | 202 | 5669.0 | 0 | 0 |
| `btle_rx` | 36951 | 2068 | 48916.9 | 8 | 32768 |
| `btle_phy` | 40964 | 2548 | 55026.9 | 11 | 40960 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9453 | 2036 | 16746.3 | 3 | 17862 |
| `btle_controller` | 50904 | 4654 | 72616.9 | 15 | 1107398 |
