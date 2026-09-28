# Area run `ble-opt`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 253 | 22 | 348.5 | 0 | 0 |
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `gfsk_modulation` | 426 | 73 | 716.6 | 2 | 32768 |
| `btle_tx` | 1392 | 248 | 2325.6 | 3 | 36864 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4495 | 202 | 5725.6 | 0 | 0 |
| `btle_rx` | 10068 | 1416 | 15887.9 | 8 | 32768 |
| `btle_phy` | 11394 | 1664 | 18208.0 | 11 | 69632 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 233 | 33 | 365.8 | 0 | 0 |
| `btle_ll` | 4336 | 954 | 7773.1 | 3 | 17414 |
| `btle_controller` | 16102 | 2673 | 26680.9 | 14 | 87046 |
