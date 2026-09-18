# Area run `baseline-upstream`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 287 | 52 | 495.3 | 0 | 0 |
| `scramble` | 121 | 25 | 213.9 | 0 | 0 |
| `bit_repeat_upsample` | 94 | 36 | 225.6 | 0 | 0 |
| `gauss_filter` | 2286 | 178 | 3366.0 | 0 | 0 |
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `gfsk_modulation` | 2466 | 229 | 3740.2 | 2 | 32768 |
| `btle_tx` | 3409 | 404 | 5322.9 | 3 | 36864 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4438 | 202 | 5669.0 | 0 | 0 |
| `btle_rx` | 36864 | 2068 | 48824.3 | 8 | 32768 |
| `btle_phy` | 40339 | 2472 | 54040.3 | 11 | 69632 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9453 | 2036 | 16746.3 | 3 | 17862 |
| `btle_controller` | 50295 | 4578 | 71706.4 | 15 | 1136070 |
