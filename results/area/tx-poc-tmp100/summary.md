# Area run `tx-poc-tmp100`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `btle_tx` | 1613 | 265 | 2760.8 | 0 | 0 |
| `tag_fsm` | 1959 | 314 | 3164.1 | 0 | 0 |
| `tag_chip` | 1771 | 304 | 2966.2 | 0 | 0 |
| `tag_chip_rate` | 1829 | 307 | 3013.8 | 0 | 0 |
| `btle_phy` | 2001 | 317 | 3219.4 | 0 | 0 |
| `btle_ll` | 9525 | 2014 | 16693.4 | 4 | 18182 |
| `btle_controller` | 10436 | 2081 | 17975.5 | 5 | 1066758 |
