# Area run `master`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 255 | 52 | 492.6 | 0 | 0 |
| `scramble` | 109 | 25 | 209.3 | 0 | 0 |
| `bit_repeat_upsample` | 34 | 8 | 61.2 | 0 | 0 |
| `gauss_filter` | 2286 | 178 | 3366.0 | 0 | 0 |
| `vco` | 86 | 15 | 150.0 | 2 | 32768 |
| `gfsk_modulation` | 5195 | 372 | 7240.8 | 2 | 32768 |
| `btle_tx` | 5823 | 547 | 8559.1 | 3 | 36864 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4477 | 202 | 5709.7 | 0 | 0 |
| `btle_rx` | 36782 | 2068 | 48619.2 | 8 | 32768 |
| `btle_phy` | 42844 | 2615 | 57320.1 | 11 | 69632 |
| `clock_domain_conversion_iq` | 186 | 62 | 363.6 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9523 | 2036 | 16737.8 | 3 | 17862 |
| `btle_controller` | 52357 | 4722 | 74684.8 | 15 | 1136070 |
