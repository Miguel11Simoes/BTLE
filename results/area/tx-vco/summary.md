# Run tx-vco: the VCO and the transmitter of every branch, on the audited RTL

Yosys + ABC, Nangate45 (`scripts/area/run_area.sh`), each branch at its head, in the configuration
`scripts/branch_config.sh` gives it (`PDU_WRITE_STROBE=1` also on `ble-tx-pdu-we`). The SRAMs are
blackboxed and counted in bits; their areas are those of the OpenRAM runs. Configurations, commits
and trees: `provenance.txt`; every top: `<branch>/<top>/stat.txt`.

| Branch | Commit | Parameters | `vco` cells | flip-flops | area (um2) | `btle_tx` cells | flip-flops | area (um2) | SRAM macros | SRAM bits |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `master` | `9d6c383` | <none: defaults> | 86 | 15 | 150.0 | 6166 | 547 | 8875.6 | 3 | 36864 |
| `ble-rx-dm` | `8a188e4` | <none: defaults> | 86 | 15 | 150.0 | 5835 | 547 | 8557.8 | 3 | 36864 |
| `ble-opt` | `6f287cb` | ENABLE_IQ_CAPTURE=0 LL_MINIMAL=1 GAUSS_TABLE=1 | 86 | 15 | 150.0 | 1414 | 238 | 2362.3 | 3 | 36864 |
| `ble-tx-table` | `23cb5a6` | GAUSS_TABLE=1 | 86 | 15 | 150.0 | 1420 | 238 | 2360.8 | 3 | 36864 |
| `ble-tx-table-reg` | `921c5d5` | GAUSS_TABLE=1 | 86 | 15 | 150.0 | 13894 | 3191 | 28672.7 | 3 | 36864 |
| `ble-tx-table-sram` | `3aa1663` | GAUSS_TABLE=1 | 86 | 15 | 150.0 | 5176 | 636 | 7883.2 | 6 | 39424 |
| `ble-tx-fir2` | `472cd7c` | <none: defaults> | 86 | 15 | 150.0 | 5326 | 539 | 7698.6 | 3 | 36864 |
| `ble-tx-opt` | `9e78573` | GAUSS_TABLE=1 | 438 | 93 | 870.6 | 1750 | 316 | 3078.2 | 3 | 12288 |
| `ble-tx-sin4` | `39093de` | <none: defaults> | 179 | 18 | 274.2 | 6274 | 550 | 9029.1 | 3 | 12288 |
| `ble-tx-sin8` | `3559cca` | <none: defaults> | 438 | 93 | 870.6 | 6512 | 625 | 9571.2 | 3 | 12288 |
| `ble-tx-sin8-1rw` | `474ccef` | <none: defaults> | 426 | 79 | 796.9 | 6633 | 611 | 9605.3 | 3 | 12288 |
| `ble-tx-sin2` | `ec7730b` | <none: defaults> | 408 | 76 | 740.0 | 6245 | 608 | 9208.4 | 2 | 8192 |
| `ble-tx-1--8` | `dff6880` | <none: defaults> | 645 | 91 | 1059.7 | 6766 | 623 | 9790.1 | 3 | 8192 |
| `ble-tx-pdu` | `4e6ffc2` | GAUSS_TABLE=1 | 349 | 63 | 635.7 | 1399 | 268 | 2553.9 | 2 | 6144 |
| `ble-tx-pdu-we` | `cfa24a4` | GAUSS_TABLE=1 PDU_WRITE_STROBE=1 | 349 | 63 | 635.7 | 1416 | 269 | 2564.8 | 2 | 6144 |
| `ble-tx-rom` | `144d51b` | GAUSS_TABLE=1 | 434 | 31 | 593.2 | 1446 | 236 | 2509.4 | 1 | 2048 |
| `ble-tx-cordic` | `3d9ad94` | GAUSS_TABLE=1 | 1942 | 31 | 2317.9 | 2868 | 236 | 4142.2 | 1 | 2048 |
