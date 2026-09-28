# TX area of the Gaussian filter options, run `tx-area`

Yosys 0.68 + ABC, Nangate45 std cells; the SRAM banks of the tables are OpenRAM macros in FreePDK45 (2 560 bits, 18437.4 µm²), added to the std-cell area. The RAMs every option shares (TX COS/SIN tables, 32 768 bits, and TX packet buffer, 4 096 bits) are left out. RX is not measured.

## `gauss_filter`

| Option | Branch | Table | Taps after fabrication | Std cells | Flip-flops | Cell area (µm²) | Table macros (µm²) | **Total (µm²)** | vs upstream FIR |
|---|---|---|---|---:|---:|---:|---:|---:|---:|
| upstream FIR, 17 terms | `master` | - (9 tap registers) | rewritable | 2 286 | 178 | 3366.0 | 0.0 | **3366.0** | — |
| folded FIR, 8 pairs + centre | `ble-tx-fir2` | - (9 tap registers) | rewritable | 1 560 | 170 | 2311.5 | 0.0 | **2311.5** | -31.3 % |
| tables, constants | `ble-tx-table` | ROM: logic | fixed | 253 | 22 | 348.5 | 0.0 | **348.5** | -89.6 % |
| tables, rebuilt from the taps | `ble-tx-table-reg` | REG: 2 560 flip-flops | rewritable | 10 097 | 2 822 | 23221.5 | 0.0 | **23221.5** | +589.9 % |
| tables, rebuilt from the taps | `ble-tx-table-sram` | SRAM: 3 macros, 2 560 bits | rewritable | 1 362 | 267 | 2479.7 | 18437.4 | **20917.1** | +521.4 % |

## Whole transmitter, `btle_tx`

| Option | Branch | Std cells | Flip-flops | Cell area (µm²) | Table macros (µm²) | **Total (µm²)** | vs upstream |
|---|---|---:|---:|---:|---:|---:|---:|
| upstream FIR, 17 terms | `master` | 3 409 | 404 | 5322.9 | 0.0 | **5322.9** | — |
| folded FIR, 8 pairs + centre | `ble-tx-fir2` | 2 707 | 396 | 4295.9 | 0.0 | **4295.9** | -19.3 % |
| tables, constants | `ble-tx-table` | 1 392 | 248 | 2325.6 | 0.0 | **2325.6** | -56.3 % |
| tables, rebuilt from the taps | `ble-tx-table-reg` | 11 328 | 3 048 | 25201.6 | 0.0 | **25201.6** | +373.5 % |
| tables, rebuilt from the taps | `ble-tx-table-sram` | 2 477 | 493 | 4434.5 | 18437.4 | **22871.9** | +329.7 % |

## Inside the rewritable tables

| Branch | Part | Std cells | Flip-flops | Cell area (µm²) | Macros (µm²) |
|---|---|---:|---:|---:|---:|
| `ble-tx-table-reg` | `gauss_table_builder` | 493 | 53 | 778.0 | 0.0 |
| `ble-tx-table-reg` | `gauss_table_reg` | 8 899 | 2 560 | 20870.1 | 0.0 |
| `ble-tx-table-sram` | `gauss_table_builder` | 493 | 53 | 778.0 | 0.0 |
| `ble-tx-table-sram` | `gauss_table_sram` | 56 | 16 | 139.4 | 18437.4 |

OpenRAM macros (FreePDK45, one read/write port):

| Macro | Words x bits | Bits | Area (µm²) | µm² per bit |
|---|---|---:|---:|---:|
| `sram_1rw_32x32` | 32 x 32 | 1024 | 9046.2 | 8.83 |
| `sram_1rw_16x64` | 64 x 16 | 1024 | 5475.8 | 5.35 |
| `sram_1rw_16x32` | 32 x 16 | 512 | 3915.4 | 7.65 |

RESULT: PASS
