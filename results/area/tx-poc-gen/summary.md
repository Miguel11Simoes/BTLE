# Area run `tx-poc-gen`

Nangate45 standard cells after `synth -flatten`, `dfflibmap`, `abc -liberty`.
SRAMs are blackboxed macros, reported in bits, not as cells or area.

| Top | Std cells | Flip-flops | Cell area (um2) | SRAM macros | SRAM bits |
|---|---:|---:|---:|---:|---:|
| `btle_tx` | 1613 | 265 | 2760.8 | 0 | 0 |
| `tag_fsm` | 2104 | 318 | 3349.5 | 0 | 0 |
| `tag_chip` | 1920 | 308 | 3123.1 | 0 | 0 |
| `btle_phy` | 2060 | 318 | 3303.5 | 0 | 0 |
| `btle_ll` | 9525 | 2014 | 16693.4 | 4 | 18182 |
| `btle_controller` | 10633 | 2082 | 18124.7 | 5 | 1066758 |
