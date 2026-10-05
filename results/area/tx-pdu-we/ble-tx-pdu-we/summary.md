# Area run `ble-tx-pdu-we`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `crc24` | 210 | 38 | 359.1 | 0 | 0 |
| `scramble` | 90 | 17 | 154.3 | 0 | 0 |
| `bit_repeat_upsample` | 61 | 14 | 110.1 | 0 | 0 |
| `gauss_filter` | 166 | 22 | 256.7 | 0 | 0 |
| `vco` | 349 | 63 | 635.7 | 1 | 4096 |
| `gfsk_modulation` | 562 | 99 | 994.8 | 1 | 4096 |
| `btle_tx` | 1299 | 257 | 2415.0 | 2 | 6144 |
| `gfsk_demodulation` | 3899 | 100 | 4757.4 | 0 | 0 |
| `search_unique_bit_sequence` | 202 | 33 | 324.8 | 0 | 0 |
| `btle_rx_core` | 4435 | 202 | 5664.7 | 0 | 0 |
| `btle_rx` | 36910 | 2068 | 48826.4 | 8 | 32768 |
| `btle_phy` | 38136 | 2325 | 51174.1 | 10 | 38912 |
| `clock_domain_conversion_iq` | 183 | 61 | 357.5 | 0 | 0 |
| `auxiliary_daemon` | 299 | 48 | 486.2 | 1 | 1048576 |
| `btle_ll` | 9478 | 2036 | 16748.2 | 3 | 17862 |
| `btle_controller` | 48056 | 4432 | 68767.4 | 14 | 1105350 |
