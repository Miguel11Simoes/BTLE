# SRAM accesses and energy of the transmitter

Window: 100000 clocks of bb_clk = s00_axi_aclk (16 MHz), 6.25 ms, setup subtracted. Energies from the SPICE characterization of each OpenRAM macro (`/tmp/sram-char-combined/char.json`): every clock costs the energy of a deselected clock (the macro's clock buffers and input flip-flops), every access its energy relative to a deselected clock; dynamic power = their sum / window time, the clock part and the access part shown apart. Leakage: char.json's, the same in every scenario.

Not characterized (counts only, no energy): `sram_1rw1r_8x2048`, `sram_1rw1r_8x512`.

## Scenario rx

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-rom | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-min | packet buffer | `sram_1rw_8x32` | 0 | 0 | 100000 | 2.92 | 0.00 | 2.92 | 16.41 |

## Scenario tx

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-rom | packet buffer | `sram_1rw_8x256` | 99405 | 595 | 0 | 5.17 | 14.22 | 19.39 | 15.02 |
| ble-tx-min | packet buffer | `sram_1rw_8x32` | 98668 | 451 | 881 | 2.92 | 7.59 | 10.51 | 16.41 |

## Scenario mixed

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-rom | packet buffer | `sram_1rw_8x256` | 99712 | 288 | 0 | 5.17 | 14.22 | 19.39 | 15.02 |
| ble-tx-min | packet buffer | `sram_1rw_8x32` | 93520 | 216 | 6264 | 2.92 | 7.18 | 10.10 | 16.41 |

## Scenario idle

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-rom | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-min | packet buffer | `sram_1rw_8x32` | 0 | 0 | 100000 | 2.92 | 0.00 | 2.92 | 16.41 |

## Scenario idle0

| Configuration | Memory | Macro | Writes | Reads | Deselected | Clocks (uW) | Accesses (uW) | Dynamic (uW) | Leakage (uW) |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| master | packet buffer | `sram_1rw1r_8x512` | 100000 | 100000 | - | — | — | — | — |
| master | VCO cos table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| master | VCO sin table | `sram_1rw1r_8x2048` | 100000 | 100000 | - | — | — | — | — |
| ble-tx-rom | packet buffer | `sram_1rw_8x256` | 100000 | 0 | 0 | 5.17 | 14.22 | 19.40 | 15.02 |
| ble-tx-min | packet buffer | `sram_1rw_8x32` | 0 | 0 | 100000 | 2.92 | 0.00 | 2.92 | 16.41 |

## Totals: the transmitter's SRAMs, dynamic power (uW)

| Configuration | rx | tx | mixed | idle | idle0 | of which clocks | Leakage (uW) |
|---|---:|---:|---:|---:|---:|---:|---:|
| master | — | — | — | — | — | — | — |
| ble-tx-rom | 19.40 | 19.39 | 19.39 | 19.40 | 19.40 | 5.17 | 15.02 |
| ble-tx-min | 2.92 | 10.51 | 10.10 | 2.92 | 2.92 | 2.92 | 16.41 |

— : a memory of that configuration is not characterized. The clock part is the same in every scenario: every memory takes every clock.

## Check failures

- incomplete energy characterization: sram_1rw1r_8x2048, sram_1rw1r_8x512

CHECKS: FAIL
RESULT: FAIL
